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
	Download Zoom recording and attach to corresponding lesson.
	Called as background job from webhook handler.

	Args:
		meeting_uuid: Zoom meeting UUID
		recording_files: List of recording file objects from webhook payload
	"""
	from frappe.utils.file_manager import save_file

	# 1. Find the LMS Live Class
	live_class = frappe.db.get_value(
		"LMS Live Class",
		{"uuid": meeting_uuid},
		["name", "batch_name", "auto_recording", "zoom_account"],
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

	# 3. Check if already processed
	if frappe.db.get_value("LMS Live Class", live_class.name, "recording_processed"):
		return  # Already processed, skip

	# 4. Get the main video file
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

	# 5. Get the lesson from the batch
	batch = frappe.get_doc("LMS Batch", live_class.batch_name)
	if not batch.courses:
		frappe.log_error(
			f"No courses found in batch {live_class.batch_name}",
			"Zoom Recording Processing"
		)
		return

	course_name = batch.courses[0].course
	lesson = frappe.db.get_value("Course Lesson", {"title": live_class.name}, "name")

	if not lesson:
		frappe.log_error(
			f"No lesson found with title matching {live_class.name}",
			"Zoom Recording Processing"
		)
		return

	# 6. Download recording from Zoom
	download_url = video_file.get("download_url")
	access_token = authenticate(live_class.zoom_account)

	try:
		response = requests.get(
			download_url,
			headers={"Authorization": f"Bearer {access_token}"},
			stream=True,
			timeout=300
		)
		response.raise_for_status()

		# 7. Generate filename
		lesson_doc = frappe.get_doc("Course Lesson", lesson)
		course_doc = frappe.get_doc("LMS Course", course_name)
		filename = f"{course_doc.name}_{lesson_doc.name}_recording.mp4"

		# 8. Upload to Frappe File system
		file_doc = save_file(
			fname=filename,
			content=response.content,
			dt="Course Lesson",
			dn=lesson,
			is_private=1,
			decode=False
		)

		# 9. Add video block to lesson content
		add_video_block_to_lesson(lesson, file_doc.file_url)

		# 10. Mark as processed
		frappe.db.set_value(
			"LMS Live Class",
			live_class.name,
			{
				"recording_processed": 1,
				"recording_file": file_doc.name,
				"recording_url": file_doc.file_url
			}
		)
		frappe.db.commit()

		# 11. Notify instructor
		notify_instructor_recording_uploaded(live_class, lesson_doc, course_doc)

	except Exception as e:
		frappe.log_error(
			f"Error downloading recording for {live_class.name}: {str(e)}",
			"Zoom Recording Processing"
		)


def add_video_block_to_lesson(lesson_name, file_url):
	"""
	Add an EditorJS upload block with the recording video to the lesson content.

	Args:
		lesson_name: Name of Course Lesson DocType
		file_url: File URL of the uploaded recording
	"""
	lesson = frappe.get_doc("Course Lesson", lesson_name)

	# Parse existing content
	if lesson.content:
		content_data = json.loads(lesson.content)
	else:
		content_data = {"blocks": []}

	# Create video block
	video_block = {
		"type": "upload",
		"data": {
			"file_url": file_url,
			"file_name": file_url.split("/")[-1],
			"youtube": "",
			"controls": True,
			"title": "Class Recording"
		}
	}

	# Add at the beginning of content
	content_data["blocks"].insert(0, video_block)

	# Update lesson
	lesson.content = json.dumps(content_data)
	lesson.save(ignore_permissions=True)
	frappe.db.commit()


def notify_instructor_recording_uploaded(live_class, lesson, course):
	"""Send notification to instructor that recording is uploaded"""
	from frappe.utils import get_fullname

	instructor_name = get_fullname(live_class.get("host", frappe.session.user))

	notification = frappe.new_doc("Notification Log")
	notification.subject = f"Recording uploaded for {lesson.title}"
	notification.for_user = live_class.get("host", frappe.session.user)
	notification.type = "Alert"
	notification.document_type = "Course Lesson"
	notification.document_name = lesson.name
	notification.email_content = f"""
		<p>The Zoom cloud recording for your live class has been automatically uploaded.</p>
		<p><strong>Course:</strong> {course.title}</p>
		<p><strong>Lesson:</strong> {lesson.title}</p>
		<p>The recording has been added to the lesson content.</p>
	"""
	notification.insert(ignore_permissions=True)
	frappe.db.commit()
