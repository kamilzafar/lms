# Copyright (c) 2023, Frappe and contributors
# For license information, please see license.txt

import json
from datetime import timedelta

import frappe
import requests
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint, format_date, format_time, get_datetime, nowdate

from lms.lms.doctype.lms_batch.lms_batch import authenticate


class LMSLiveClass(Document):
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


def process_zoom_recording(meeting_uuid, recording_files):
	"""
	Extract Zoom recording metadata and store in LMS Live Class.
	NO file downloads - metadata only (videos remain in Zoom Cloud).
	Called as background job from webhook handler.

	Args:
		meeting_uuid: Zoom meeting UUID
		recording_files: List of recording file objects from webhook payload
	"""
	# 1. Find the LMS Live Class
	live_class = frappe.db.get_value(
		"LMS Live Class",
		{"uuid": meeting_uuid},
		["name", "batch_name", "auto_recording", "zoom_account", "lesson", "meeting_id"],
		as_dict=True
	)

	if not live_class:
		frappe.log_error(
			f"No LMS Live Class found for Zoom meeting UUID: {meeting_uuid}",
			"Zoom Recording Processing"
		)
		return

	# 2. Check if auto_recording is enabled for cloud
	if live_class.auto_recording != "Cloud":
		frappe.log_error(
			f"Live Class {live_class.name} not configured for cloud recording",
			"Zoom Recording Processing"
		)
		return

	# 3. Check if already processed (idempotent)
	if frappe.db.get_value("LMS Live Class", live_class.name, "recording_processed"):
		return  # Already processed, skip

	# 4. Get the main video file from webhook payload
	video_file = None
	for file in recording_files:
		if file.get("file_type") == "MP4" and file.get("recording_type") in [
			"shared_screen_with_speaker_view",
			"shared_screen_with_gallery_view",
			"speaker_view",
			"gallery_view"
		]:
			video_file = file
			break

	if not video_file:
		frappe.log_error(
			f"No suitable video file found in recording for {live_class.name}",
			"Zoom Recording Processing"
		)
		return

	# 5. Fetch passcode from Zoom API (not in webhook payload)
	# Must make separate API call to get recording_play_passcode
	access_token = authenticate(live_class.zoom_account)
	meeting_id = live_class.meeting_id

	if not meeting_id:
		frappe.log_error(
			f"No meeting_id found for Live Class {live_class.name}",
			"Zoom Recording Processing"
		)
		return

	try:
		# Fetch full recording details from Zoom API
		zoom_api_url = f"https://api.zoom.us/v2/meetings/{meeting_id}/recordings"
		headers = {"Authorization": f"Bearer {access_token}"}
		response = requests.get(zoom_api_url, headers=headers, timeout=30)
		response.raise_for_status()

		recording_data = response.json()
		recording_passcode = recording_data.get("recording_play_passcode", "")

		# 6. Extract metadata from webhook payload (NO file download)
		recording_id = video_file.get("id")
		play_url = video_file.get("play_url")  # This URL expires (~24 hours)
		file_size = video_file.get("file_size", 0)

		# Calculate duration from recording_start/recording_end timestamps (milliseconds)
		recording_start = video_file.get("recording_start")
		recording_end = video_file.get("recording_end")
		duration_seconds = 0
		if recording_start and recording_end:
			# Parse ISO 8601 timestamps
			from datetime import datetime
			start_dt = datetime.fromisoformat(recording_start.replace("Z", "+00:00"))
			end_dt = datetime.fromisoformat(recording_end.replace("Z", "+00:00"))
			duration_seconds = int((end_dt - start_dt).total_seconds())

		# 7. Store metadata ONLY (no file download, no file storage)
		frappe.db.set_value(
			"LMS Live Class",
			live_class.name,
			{
				"recording_processed": 1,
				"zoom_recording_id": recording_id,
				"recording_url": play_url,  # Store for reference (will be refreshed on-demand)
				"recording_passcode": recording_passcode,
				"recording_duration": duration_seconds,
				"recording_file_size": file_size
			}
		)
		frappe.db.commit()

		# 8. Notify instructor (metadata ready, not uploaded)
		notify_instructor_recording_available(live_class)

		print(f"✅ Zoom recording metadata stored for {live_class.name}")
		print(f"   Recording ID: {recording_id}")
		print(f"   Duration: {duration_seconds} seconds")
		print(f"   File Size: {file_size} bytes")
		print(f"   Passcode: {'Yes' if recording_passcode else 'No'}")

	except requests.exceptions.HTTPError as e:
		frappe.log_error(
			f"Zoom API error fetching recording metadata for {live_class.name}: {str(e)}\nResponse: {e.response.text if e.response else 'N/A'}",
			"Zoom Recording Processing"
		)
	except Exception as e:
		frappe.log_error(
			f"Error processing Zoom recording metadata for {live_class.name}: {str(e)}\n{frappe.get_traceback()}",
			"Zoom Recording Processing"
		)


def notify_instructor_recording_available(live_class):
	"""Send notification to instructor that recording metadata is available"""
	from frappe.utils import get_fullname

	instructor_name = get_fullname(live_class.get("host", frappe.session.user))

	# Get lesson title if linked
	lesson_title = "this live class"
	if live_class.get("lesson"):
		lesson_title = frappe.db.get_value("Course Lesson", live_class.lesson, "title") or lesson_title

	notification = frappe.new_doc("Notification Log")
	notification.subject = f"Recording available for {lesson_title}"
	notification.for_user = live_class.get("host", frappe.session.user)
	notification.type = "Alert"
	notification.document_type = "LMS Live Class"
	notification.document_name = live_class.name
	notification.email_content = f"""
		<p>The Zoom cloud recording for your live class is ready.</p>
		<p><strong>Title:</strong> {live_class.name}</p>
		<p>Students with enrollment can now watch the recording through the LMS.</p>
	"""
	notification.insert(ignore_permissions=True)
	frappe.db.commit()
