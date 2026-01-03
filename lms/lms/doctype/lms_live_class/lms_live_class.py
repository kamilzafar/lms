# Copyright (c) 2023, Frappe and contributors
# For license information, please see license.txt

import json
from datetime import datetime, timedelta

import frappe
import requests
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint, format_date, format_time, get_datetime, getdate, nowdate

from lms.lms.doctype.lms_batch.lms_batch import authenticate


class LMSLiveClass(Document):
	def on_update(self):
		# Auto-fetch recording if class has ended and recording is enabled
		if self.auto_recording != "No Recording" and not self.recording_available:
			# Check if class has ended
			try:
				class_start = datetime.combine(
					getdate(self.date),
					datetime.strptime(str(self.time), "%H:%M:%S").time() if isinstance(self.time, str) else self.time
				)
				class_end = class_start + timedelta(minutes=cint(self.duration))
				
				if datetime.now() > class_end:
					# Fetch recording asynchronously
					frappe.enqueue(
						'lms.lms.doctype.lms_live_class.lms_live_class.fetch_recording',
						live_class_name=self.name,
						queue='long'
					)
			except (ValueError, TypeError):
				# Skip if date/time parsing fails
				pass
	
	def after_insert(self):
		calendar = frappe.db.get_value("Google Calendar", {"user": frappe.session.user, "enable": 1}, "name")

		if calendar:
			event = self.create_event()
			self.add_event_participants(event, calendar)
			frappe.db.set_value(self.doctype, self.name, "event", event.name)

	def create_event(self):
		start = f"{self.date} {self.time}"

		event = frappe.get_doc(
			{
				"doctype": "Event",
				"subject": f"Live Class on {self.title}",
				"event_type": "Public",
				"starts_on": start,
				"ends_on": get_datetime(start) + timedelta(minutes=cint(self.duration)),
			}
		)
		event.save()
		return event

	def add_event_participants(self, event, calendar):
		participants = frappe.get_all("LMS Batch Enrollment", {"batch": self.batch_name}, pluck="member")
		instructors = frappe.get_all(
			"Course Instructor", {"parenttype": "LMS Batch", "parent": self.batch_name}, pluck="instructor"
		)

		participants.append(frappe.session.user)
		participants.extend(instructors)
		participants = list(set(participants))

		for participant in participants:
			frappe.get_doc(
				{
					"doctype": "Event Participants",
					"reference_doctype": "User",
					"reference_docname": participant,
					"email": participant,
					"parent": event.name,
					"parenttype": "Event",
					"parentfield": "event_participants",
				}
			).save()

		event.reload()
		event.update(
			{
				"sync_with_google_calendar": 1,
				"google_calendar": calendar,
				"description": f"A Live Class has been scheduled on {format_date(self.date, 'medium')} at {format_time(self.time, 'hh:mm a')}. Click on this link to join. {self.join_url}. {self.description}",
			}
		)

		event.save()


def send_live_class_reminder():
	classes = frappe.get_all(
		"LMS Live Class",
		{
			"date": nowdate(),
		},
		["name", "batch_name", "title", "date", "time"],
	)

	for live_class in classes:
		students = frappe.get_all(
			"LMS Batch Enrollment",
			{"batch": live_class.batch_name},
			["member", "member_name"],
		)
		for student in students:
			send_mail(live_class, student)


def send_mail(live_class, student):
	subject = _("Your class on {0} is today").format(live_class.title)
	template = "live_class_reminder"

	args = {
		"student_name": student.member_name,
		"title": live_class.title,
		"date": live_class.date,
		"time": live_class.time,
		"batch_name": live_class.batch_name,
	}

	frappe.sendmail(
		recipients=student.member,
		subject=subject,
		template=template,
		args=args,
		header=[_(f"Class Reminder: {live_class.title}"), "orange"],
	)


def update_attendance():
	past_live_classes = frappe.get_all(
		"LMS Live Class",
		{
			"uuid": ["is", "set"],
			"attendees": ["is", "not set"],
		},
		["name", "uuid", "zoom_account"],
	)

	for live_class in past_live_classes:
		attendance_data = get_attendance(live_class)
		create_attendance(live_class, attendance_data)
		update_attendees_count(live_class, attendance_data)


def get_attendance(live_class):
	headers = {
		"Authorization": "Bearer " + authenticate(live_class.zoom_account),
		"content-type": "application/json",
	}

	encoded_uuid = requests.utils.quote(live_class.uuid, safe="")
	response = requests.get(
		f"https://api.zoom.us/v2/past_meetings/{encoded_uuid}/participants", headers=headers
	)

	if response.status_code != 200:
		frappe.throw(
			_("Failed to fetch attendance data from Zoom for class {0}: {1}").format(
				live_class, response.text
			)
		)

	data = response.json()
	return data.get("participants", [])


def create_attendance(live_class, data):
	for participant in data:
		doc = frappe.new_doc("LMS Live Class Participant")
		doc.live_class = live_class.name
		doc.member = participant.get("user_email")
		doc.joined_at = participant.get("join_time")
		doc.left_at = participant.get("leave_time")
		doc.duration = participant.get("duration")
		doc.insert()


def update_attendees_count(live_class, data):
	frappe.db.set_value("LMS Live Class", live_class.name, "attendees", len(data))


def fetch_pending_recordings():
	"""Scheduled job to fetch recordings for classes that have ended but recordings aren't available yet"""
	# Get all live classes that:
	# 1. Have recording enabled
	# 2. Have ended (at least 10 minutes ago to allow processing time)
	# 3. Don't have recording available yet
	# 4. Are not older than 1.5 hours (90 minutes) - max time window for checking

	frappe.logger().info("[Recording Scheduler] Starting fetch_pending_recordings job")

	cutoff_time = datetime.now() - timedelta(minutes=90)  # 1.5 hours = 90 minutes
	ten_minutes_ago = datetime.now() - timedelta(minutes=10)

	frappe.logger().info(f"[Recording Scheduler] Time window: {cutoff_time} to {ten_minutes_ago}")

	pending_classes = frappe.get_all(
		"LMS Live Class",
		filters={
			"auto_recording": ["!=", "No Recording"],
			"recording_available": 0,
			"meeting_id": ["is", "set"],
		},
		fields=["name", "date", "time", "duration", "auto_recording", "meeting_id"]
	)

	frappe.logger().info(f"[Recording Scheduler] Found {len(pending_classes)} live classes with auto_recording enabled and no recording yet")

	enqueued_count = 0

	for live_class in pending_classes:
		try:
			# Check if class has ended (at least 10 minutes ago)
			class_start = datetime.combine(
				getdate(live_class.date),
				datetime.strptime(str(live_class.time), "%H:%M:%S").time() if isinstance(live_class.time, str) else live_class.time
			)
			class_end = class_start + timedelta(minutes=cint(live_class.duration))

			time_since_end = datetime.now() - class_end

			frappe.logger().info(f"[Recording Scheduler] Class {live_class.name}: ended at {class_end}, {time_since_end.total_seconds() / 60:.1f} minutes ago, meeting_id={live_class.meeting_id}")

			# Only try to fetch if class ended at least 10 minutes ago
			# and not more than 1.5 hours ago (max 90 minutes)
			if ten_minutes_ago > class_end > cutoff_time:
				frappe.logger().info(f"[Recording Scheduler] Enqueueing recording fetch for {live_class.name}")
				# Try to fetch recording
				frappe.enqueue(
					'lms.lms.doctype.lms_live_class.lms_live_class.fetch_recording',
					live_class_name=live_class.name,
					queue='long',
					timeout=300  # 5 minute timeout
				)
				enqueued_count += 1
			else:
				frappe.logger().info(f"[Recording Scheduler] Class {live_class.name} outside time window - not enqueueing")
		except (ValueError, TypeError) as e:
			frappe.logger().error(f"[Recording Scheduler] Error processing class {live_class.name}: {str(e)}")
			continue

	frappe.logger().info(f"[Recording Scheduler] Job complete. Enqueued {enqueued_count} recording fetch tasks")


@frappe.whitelist()
def fetch_recording(live_class_name):
	"""Fetch recording URL from Zoom API for a completed live class"""
	live_class = frappe.get_doc("LMS Live Class", live_class_name)

	frappe.logger().info(f"[Recording Fetch] Starting fetch for {live_class_name}")

	if not live_class.meeting_id:
		frappe.logger().error(f"[Recording Fetch] Meeting ID not found for {live_class_name}")
		frappe.throw(_("Meeting ID not found"))

	if live_class.recording_available:
		frappe.logger().info(f"[Recording Fetch] Recording already available for {live_class_name}")
		return {
			"recording_url": live_class.recording_url,
			"recording_available": True
		}

	frappe.logger().info(f"[Recording Fetch] Meeting ID: {live_class.meeting_id}, Zoom Account: {live_class.zoom_account}")

	try:
		token = authenticate(live_class.zoom_account)
		headers = {
			"Authorization": "Bearer " + token,
			"content-type": "application/json",
		}

		api_url = f"https://api.zoom.us/v2/meetings/{live_class.meeting_id}/recordings"
		frappe.logger().info(f"[Recording Fetch] Calling Zoom API: {api_url}")

		# Get recordings from Zoom API
		response = requests.get(api_url, headers=headers, timeout=30)

		frappe.logger().info(f"[Recording Fetch] Zoom API response status: {response.status_code}")

		if response.status_code == 200:
			data = response.json()
			recordings = data.get("recording_files", [])
			total_size = data.get("total_size", 0)
			recording_count = data.get("recording_count", 0)

			frappe.logger().info(f"[Recording Fetch] Response: total_size={total_size}, recording_count={recording_count}, files={len(recordings)}")

			# If no recordings yet, return status indicating it's still processing
			if not recordings:
				frappe.logger().info(f"[Recording Fetch] No recording files yet - still processing")
				return {
					"recording_available": False,
					"status": "processing",
					"message": _("Recording is being processed. Please check back in a few minutes.")
				}

			# Log all recording files found
			for i, rec in enumerate(recordings):
				frappe.logger().info(f"[Recording Fetch] File {i}: type={rec.get('file_type')}, recording_type={rec.get('recording_type')}, status={rec.get('status')}, has_play_url={bool(rec.get('play_url'))}")

			# Find cloud recording (prefer MP4 or shared_screen_with_speaker_view)
			cloud_recording = None
			for recording in recordings:
				# Prefer MP4 format or shared screen with speaker view
				if recording.get("file_type") == "MP4" or \
				   recording.get("recording_type") == "shared_screen_with_speaker_view":
					cloud_recording = recording
					frappe.logger().info(f"[Recording Fetch] Selected recording: type={recording.get('file_type')}, recording_type={recording.get('recording_type')}")
					break

			# If no MP4 found, get the first available recording
			if not cloud_recording and recordings:
				cloud_recording = recordings[0]
				frappe.logger().info(f"[Recording Fetch] No MP4 found, using first recording: type={cloud_recording.get('file_type')}")

			if cloud_recording:
				# Get playback URL - prefer play_url over download_url for embedding
				playback_url = cloud_recording.get("play_url")
				if not playback_url:
					# Fallback to download_url if play_url not available
					playback_url = cloud_recording.get("download_url")
					frappe.logger().info(f"[Recording Fetch] Using download_url as fallback")

				password = cloud_recording.get("password", "")

				if playback_url:
					# Store the meeting UUID for potential future use
					meeting_uuid = cloud_recording.get("meeting_id", "")

					frappe.logger().info(f"[Recording Fetch] Got playback URL, updating live class {live_class_name}")

					# Update live class with recording info
					live_class.recording_url = playback_url
					live_class.recording_password = password
					live_class.recording_available = 1
					live_class.save(ignore_permissions=True)

					frappe.logger().info(f"[Recording Fetch] Successfully saved recording for {live_class_name}")
					
					# Automatically create lesson in course chapter
					try:
						from lms.lms.api import create_lesson_from_recording
						create_lesson_from_recording(live_class_name)
					except Exception as e:
						frappe.logger().error(f"[Recording Fetch] Error creating lesson from recording: {str(e)}")

					return {
						"recording_url": playback_url,
						"recording_available": True
					}
				else:
					frappe.logger().warning(f"[Recording Fetch] No playback URL found in recording file")
			else:
				frappe.logger().warning(f"[Recording Fetch] No suitable cloud recording found")

		elif response.status_code == 404:
			frappe.logger().warning(f"[Recording Fetch] Zoom API returned 404 - recording not found or still processing")
			try:
				error_data = response.json()
				frappe.logger().warning(f"[Recording Fetch] Error details: {error_data}")
			except:
				frappe.logger().warning(f"[Recording Fetch] Could not parse error response")

		else:
			frappe.logger().error(f"[Recording Fetch] Zoom API returned status {response.status_code}")
			try:
				error_data = response.json()
				frappe.logger().error(f"[Recording Fetch] Error response: {error_data}")
			except:
				frappe.logger().error(f"[Recording Fetch] Response text: {response.text}")

	except requests.exceptions.RequestException as e:
		frappe.logger().error(f"[Recording Fetch] Network error: {str(e)}")
		return {
			"recording_available": False,
			"status": "processing",
			"message": _("Recording is being processed. Please check back in a few minutes.")
		}
	except Exception as e:
		frappe.logger().error(f"[Recording Fetch] Unexpected error: {str(e)}")
		return {
			"recording_available": False,
			"status": "error",
			"message": _("Error fetching recording. Please try again later.")
		}

	# Default: recording is still processing
	frappe.logger().info(f"[Recording Fetch] Recording still processing for {live_class_name}")
	return {
		"recording_available": False,
		"status": "processing",
		"message": _("Recording is being processed. Please check back in a few minutes.")
	}
