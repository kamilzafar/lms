"""API methods for the LMS."""

import json
import os
import re
import shutil
import xml.etree.ElementTree as ET
import zipfile
from datetime import datetime, timedelta
from xml.dom.minidom import parseString

import frappe
from frappe import _
from frappe.integrations.frappe_providers.frappecloud_billing import (
	current_site_info,
	is_fc_site,
)
from frappe.query_builder import DocType
from frappe.translate import get_all_translations
from frappe.utils import (
	add_days,
	cint,
	date_diff,
	flt,
	format_date,
	get_datetime,
	getdate,
	now,
)
from frappe.utils.response import Response

from lms.lms.doctype.course_lesson.course_lesson import save_progress
from lms.lms.utils import get_average_rating, get_batch_details, get_course_details, get_lesson_count


@frappe.whitelist(allow_guest=True)
def get_user_info():
	if frappe.session.user == "Guest":
		return None

	user = frappe.db.get_value(
		"User",
		frappe.session.user,
		["name", "email", "enabled", "user_image", "full_name", "user_type", "username"],
		as_dict=1,
	)
	user["roles"] = frappe.get_roles(user.name)
	user.is_instructor = "Course Creator" in user.roles
	user.is_moderator = "Moderator" in user.roles
	user.is_evaluator = "Batch Evaluator" in user.roles
	user.is_student = "LMS Student" in user.roles
	user.is_teacher = "LMS Teacher" in user.roles
	user.is_fc_site = is_fc_site()
	user.is_system_manager = "System Manager" in user.roles
	user.sitename = frappe.local.site
	user.developer_mode = frappe.conf.developer_mode
	if user.is_fc_site and user.is_system_manager:
		user.site_info = current_site_info()
	return user


@frappe.whitelist(allow_guest=True)
def get_translations():
	if frappe.session.user != "Guest":
		language = frappe.db.get_value("User", frappe.session.user, "language")
	else:
		language = frappe.db.get_single_value("System Settings", "language")
	return get_all_translations(language)


@frappe.whitelist()
def validate_billing_access(billing_type, name):
	doctype = "LMS Batch" if billing_type == "batch" else "LMS Course"
	access, message = verify_billing_access(doctype, name, billing_type)

	address = frappe.db.get_value(
		"Address",
		{"email_id": frappe.session.user},
		[
			"name",
			"address_title as billing_name",
			"address_line1",
			"address_line2",
			"city",
			"state",
			"country",
			"pincode",
			"phone",
		],
		as_dict=1,
	)

	return {"access": access, "message": message, "address": address}


def verify_billing_access(doctype, name, billing_type):
	access = True
	message = ""

	if frappe.session.user == "Guest":
		access = False
		message = _("Please login to continue with payment.")

	if access and billing_type not in ["course", "batch", "certificate"]:
		access = False
		message = _("Module is incorrect.")

	if access and not frappe.db.exists(doctype, name):
		access = False
		message = _("Module Name is incorrect or does not exist.")

	if access and billing_type == "course":
		membership = frappe.db.exists("LMS Enrollment", {"member": frappe.session.user, "course": name})
		if membership:
			access = False
			message = _("You are already enrolled for this course.")

	elif access and billing_type == "batch":
		membership = frappe.db.exists("LMS Batch Enrollment", {"member": frappe.session.user, "batch": name})
		if membership:
			access = False
			message = _("You are already enrolled for this batch.")

		seat_count = frappe.get_cached_value("LMS Batch", name, "seat_count")
		number_of_students = frappe.db.count("LMS Batch Enrollment", {"batch": name})
		if seat_count <= number_of_students:
			access = False
			message = _("Batch is sold out.")

		start_date = frappe.get_cached_value("LMS Batch", name, "start_date")
		if start_date and date_diff(start_date, now()) < 0:
			access = False
			message = _("Batch has already started.")

	elif access and billing_type == "certificate":
		purchased_certificate = frappe.db.exists(
			"LMS Enrollment",
			{
				"course": name,
				"member": frappe.session.user,
				"purchased_certificate": 1,
			},
		)
		if purchased_certificate:
			access = False
			message = _("You have already purchased the certificate for this course.")

	return access, message


@frappe.whitelist(allow_guest=True)
def get_job_details(job):
	return frappe.db.get_value(
		"Job Opportunity",
		job,
		[
			"job_title",
			"location",
			"country",
			"type",
			"work_mode",
			"company_name",
			"company_logo",
			"company_website",
			"name",
			"creation",
			"description",
			"owner",
		],
		as_dict=1,
	)


@frappe.whitelist(allow_guest=True)
def get_job_opportunities(filters=None, orFilters=None):
	if not filters:
		filters = {}

	jobs = frappe.get_all(
		"Job Opportunity",
		filters=filters,
		or_filters=orFilters,
		fields=[
			"job_title",
			"location",
			"country",
			"type",
			"work_mode",
			"company_name",
			"company_logo",
			"name",
			"creation",
			"description",
		],
		order_by="creation desc",
	)

	for job in jobs:
		job.description = frappe.utils.strip_html_tags(job.description)
		job.applicants = frappe.db.count("LMS Job Application", {"job": job.name})
	return jobs


@frappe.whitelist(allow_guest=True)
def get_chart_details():
	details = frappe._dict()
	details.enrollments = frappe.db.count("LMS Enrollment")
	details.courses = frappe.db.count(
		"LMS Course",
		{
			"published": 1,
			"upcoming": 0,
		},
	)
	details.users = frappe.db.count("User", {"enabled": 1, "name": ["not in", ("Administrator", "Guest")]})
	details.completions = frappe.db.count("LMS Enrollment", {"progress": ["like", "%100%"]})
	details.certifications = frappe.db.count("LMS Certificate", {"published": 1})
	return details


@frappe.whitelist()
def get_file_info(file_url):
	"""Get file info for the given file URL."""
	file_info = frappe.db.get_value(
		"File", {"file_url": file_url}, ["file_name", "file_size", "file_url"], as_dict=1
	)
	return file_info


@frappe.whitelist(allow_guest=True)
def get_branding():
	"""Get branding details."""
	website_settings = frappe.get_single("Website Settings")
	image_fields = ["banner_image", "footer_logo", "favicon"]

	for field in image_fields:
		if website_settings.get(field):
			file_info = get_file_info(website_settings.get(field))
			website_settings.update({field: json.loads(json.dumps(file_info))})
		else:
			website_settings.update({field: None})

	return website_settings


@frappe.whitelist()
def get_unsplash_photos(keyword=None):
	from lms.unsplash import get_by_keyword, get_list

	if keyword:
		return get_by_keyword(keyword)

	return frappe.cache().get_value("unsplash_photos", generator=get_list)


@frappe.whitelist()
def get_evaluator_details(evaluator):
	frappe.only_for("Batch Evaluator")

	if not frappe.db.exists("Google Calendar", {"user": evaluator}):
		calendar = frappe.new_doc("Google Calendar")
		calendar.update({"user": evaluator, "calendar_name": evaluator})
		calendar.insert()
	else:
		calendar = frappe.db.get_value(
			"Google Calendar", {"user": evaluator}, ["name", "authorization_code"], as_dict=1
		)

	if frappe.db.exists("Course Evaluator", {"evaluator": evaluator}):
		doc = frappe.get_doc("Course Evaluator", evaluator)
	else:
		doc = frappe.new_doc("Course Evaluator")
		doc.evaluator = evaluator
		doc.insert()

	return {
		"slots": doc.as_dict(),
		"calendar": calendar.name,
		"is_authorised": calendar.authorization_code,
	}


@frappe.whitelist(allow_guest=True)
def get_certified_participants(filters=None, start=0, page_length=100):
	or_filters = {}
	if not filters:
		filters = {}

	filters.update({"published": 1})

	category = filters.get("category")
	if category:
		del filters["category"]
		or_filters["course_title"] = ["like", f"%{category}%"]
		or_filters["batch_title"] = ["like", f"%{category}%"]

	participants = frappe.db.get_all(
		"LMS Certificate",
		filters=filters,
		or_filters=or_filters,
		fields=["member", "issue_date"],
		group_by="member",
		order_by="issue_date desc",
		start=start,
		page_length=page_length,
	)

	for participant in participants:
		count = frappe.db.count("LMS Certificate", {"member": participant.member})
		details = frappe.db.get_value(
			"User",
			participant.member,
			["full_name", "user_image", "username", "country", "headline", "looking_for_job"],
			as_dict=1,
		)
		details["certificate_count"] = count
		participant.update(details)

	return participants


@frappe.whitelist(allow_guest=True)
def get_count_of_certified_members(filters=None):
	Certificate = DocType("LMS Certificate")

	query = (
		frappe.qb.from_(Certificate).select(Certificate.member).distinct().where(Certificate.published == 1)
	)

	if filters:
		for field, value in filters.items():
			if field == "category":
				query = query.where(
					Certificate.course_title.like(f"%{value}%") | Certificate.batch_title.like(f"%{value}%")
				)
			elif field == "member_name":
				query = query.where(Certificate.member_name.like(value[1]))

	result = query.run(as_dict=True)
	return len(result) or 0


@frappe.whitelist(allow_guest=True)
def get_certification_categories():
	categories = []
	seen = set()
	docs = frappe.get_all(
		"LMS Certificate",
		filters={
			"published": 1,
		},
		fields=["course_title", "batch_title"],
	)

	for doc in docs:
		category = doc.course_title if doc.course_title else doc.batch_title
		if not category or category in seen:
			continue

		seen.add(category)
		categories.append({"label": category, "value": category})
	return categories


@frappe.whitelist()
def get_assigned_badges(member):
	assigned_badges = frappe.get_all(
		"LMS Badge Assignment",
		{"member": member},
		["badge"],
		as_dict=1,
	)

	for badge in assigned_badges:
		badge.update(frappe.db.get_value("LMS Badge", badge.badge, ["name", "title", "image"]))
	return assigned_badges


@frappe.whitelist()
def get_all_users():
	frappe.only_for(["Moderator", "Course Creator", "Batch Evaluator"])
	users = frappe.get_all(
		"User",
		{
			"enabled": 1,
		},
		["name", "full_name", "user_image"],
	)

	return {user.name: user for user in users}


@frappe.whitelist()
def mark_as_read(name):
	doc = frappe.get_doc("Notification Log", name)
	doc.read = 1
	doc.save(ignore_permissions=True)


@frappe.whitelist()
def mark_all_as_read():
	notifications = frappe.get_all(
		"Notification Log", {"for_user": frappe.session.user, "read": 0}, pluck="name"
	)

	for notification in notifications:
		mark_as_read(notification)


@frappe.whitelist(allow_guest=True)
def get_sidebar_settings():
	lms_settings = frappe.get_single("LMS Settings")
	sidebar_items = frappe._dict()

	items = [
		"courses",
		"batches",
		"certifications",
		"jobs",
		"statistics",
		"notifications",
		"programming_exercises",
	]
	for item in items:
		sidebar_items[item] = lms_settings.get(item)

	if len(lms_settings.sidebar_items):
		web_pages = frappe.get_all(
			"LMS Sidebar Item",
			{"parenttype": "LMS Settings", "parentfield": "sidebar_items"},
			["web_page", "route", "title as label", "icon", "name"],
		)
		for page in web_pages:
			page.to = page.route

		sidebar_items.web_pages = web_pages

	return sidebar_items


@frappe.whitelist()
def update_sidebar_item(webpage, icon):
	filters = {
		"web_page": webpage,
		"parenttype": "LMS Settings",
		"parentfield": "sidebar_items",
		"parent": "LMS Settings",
	}

	if frappe.db.exists("LMS Sidebar Item", filters):
		frappe.db.set_value("LMS Sidebar Item", filters, "icon", icon)
	else:
		doc = frappe.new_doc("LMS Sidebar Item")
		doc.update(filters)
		doc.icon = icon
		doc.insert()


@frappe.whitelist()
def delete_sidebar_item(webpage):
	return frappe.db.delete(
		"LMS Sidebar Item",
		{
			"web_page": webpage,
			"parenttype": "LMS Settings",
			"parentfield": "sidebar_items",
			"parent": "LMS Settings",
		},
	)


@frappe.whitelist()
def delete_lesson(lesson, chapter):
	# Delete Reference
	chapter = frappe.get_doc("Course Chapter", chapter)
	chapter.lessons = [row for row in chapter.lessons if row.lesson != lesson]
	chapter.save()

	# Delete progress
	frappe.db.delete("LMS Course Progress", {"lesson": lesson})

	# Delete Lesson
	frappe.db.delete("Course Lesson", lesson)


@frappe.whitelist()
def update_lesson_index(lesson, sourceChapter, targetChapter, idx):
	hasMoved = sourceChapter == targetChapter

	update_source_chapter(lesson, sourceChapter, idx, hasMoved)
	if not hasMoved:
		update_target_chapter(lesson, targetChapter, idx)


def update_source_chapter(lesson, chapter, idx, hasMoved=False):
	lessons = frappe.get_all(
		"Lesson Reference",
		{
			"parent": chapter,
		},
		pluck="lesson",
		order_by="idx",
	)

	lessons.remove(lesson)
	if not hasMoved:
		frappe.db.delete("Lesson Reference", {"parent": chapter, "lesson": lesson})
	else:
		lessons.insert(idx, lesson)

	update_index(lessons, chapter)


def update_target_chapter(lesson, chapter, idx):
	lessons = frappe.get_all(
		"Lesson Reference",
		{
			"parent": chapter,
		},
		pluck="lesson",
		order_by="idx",
	)

	lessons.insert(idx, lesson)
	new_lesson_reference = frappe.new_doc("Lesson Reference")
	new_lesson_reference.update(
		{
			"lesson": lesson,
			"parent": chapter,
			"parenttype": "Course Chapter",
			"parentfield": "lessons",
		}
	)
	new_lesson_reference.insert()
	update_index(lessons, chapter)


def update_index(lessons, chapter):
	for row in lessons:
		frappe.db.set_value(
			"Lesson Reference", {"lesson": row, "parent": chapter}, "idx", lessons.index(row) + 1
		)


@frappe.whitelist()
def update_chapter_index(chapter, course, idx):
	"""Update the index of a chapter within a course"""
	chapters = frappe.get_all(
		"Chapter Reference",
		{"parent": course},
		pluck="chapter",
		order_by="idx",
	)

	if chapter in chapters:
		chapters.remove(chapter)

	chapters.insert(idx, chapter)

	for i, chapter_name in enumerate(chapters):
		frappe.db.set_value("Chapter Reference", {"chapter": chapter_name, "parent": course}, "idx", i + 1)


@frappe.whitelist(allow_guest=True)
def get_categories(doctype, filters):
	categoryOptions = []

	categories = frappe.get_all(
		doctype,
		filters,
		pluck="category",
	)
	categories = list(set(categories))

	for category in categories:
		if category:
			categoryOptions.append({"label": category, "value": category})

	return categoryOptions


@frappe.whitelist()
def get_members(start=0, search=""):
	filters = {"enabled": 1, "name": ["not in", ["Administrator", "Guest"]]}
	or_filters = {}

	if search:
		or_filters["full_name"] = ["like", f"%{search}%"]
		or_filters["email"] = ["like", f"%{search}%"]

	members = frappe.get_all(
		"User",
		filters=filters,
		fields=["name", "full_name", "user_image", "username", "last_active"],
		or_filters=or_filters,
		page_length=20,
		start=start,
	)

	for member in members:
		roles = frappe.get_all(
			"Has Role",
			{
				"parent": member.name,
				"parenttype": "User",
			},
			pluck="role",
		)
		if "Moderator" in roles:
			member.role = "Moderator"
		elif "Course Creator" in roles:
			member.role = "Course Creator"
		elif "Batch Evaluator" in roles:
			member.role = "Batch Evaluator"
		elif "LMS Student" in roles:
			member.role = "LMS Student"

	return members


def check_app_permission():
	"""Check if the user has permission to access the app."""
	if frappe.session.user == "Administrator":
		return True

	roles = frappe.get_roles()
	lms_roles = ["Moderator", "Course Creator", "Batch Evaluator", "LMS Student"]
	if any(role in roles for role in lms_roles):
		return True

	return False


@frappe.whitelist()
def save_evaluation_details(
	member,
	course,
	batch_name,
	evaluator,
	date,
	start_time,
	end_time,
	status,
	rating,
	summary,
):
	"""
	Save evaluation details for a member against a course.
	"""
	evaluation = frappe.db.exists("LMS Certificate Evaluation", {"member": member, "course": course})

	details = {
		"date": date,
		"start_time": start_time,
		"end_time": end_time,
		"status": status,
		"rating": rating / 5,
		"summary": summary,
		"batch_name": batch_name,
	}

	if evaluation:
		frappe.db.set_value("LMS Certificate Evaluation", evaluation, details)
		return evaluation
	else:
		doc = frappe.new_doc("LMS Certificate Evaluation")
		details.update(
			{
				"member": member,
				"course": course,
				"evaluator": evaluator,
			}
		)
		doc.update(details)
		doc.insert()
		return doc.name


@frappe.whitelist()
def save_certificate_details(
	member,
	course,
	batch_name,
	evaluator,
	issue_date,
	expiry_date,
	template,
	published=True,
):
	"""
	Save certificate details for a member against a course.
	"""
	certificate = frappe.db.exists("LMS Certificate", {"member": member, "course": course})

	details = {
		"published": published,
		"issue_date": issue_date,
		"expiry_date": expiry_date,
		"template": template,
		"batch_name": batch_name,
	}

	if certificate:
		frappe.db.set_value("LMS Certificate", certificate, details)
		return certificate
	else:
		doc = frappe.new_doc("LMS Certificate")
		details.update(
			{
				"member": member,
				"course": course,
				"evaluator": evaluator,
			}
		)
		doc.update(details)
		doc.insert()
		return doc.name


@frappe.whitelist()
def delete_documents(doctype, documents):
	frappe.only_for("Moderator")
	for doc in documents:
		frappe.delete_doc(doctype, doc)


@frappe.whitelist(allow_guest=True)
def get_count(doctype, filters):
	return frappe.db.count(
		doctype,
		filters=filters,
	)


@frappe.whitelist()
def get_payment_gateway_details(payment_gateway):
	gateway = frappe.get_doc("Payment Gateway", payment_gateway)

	if gateway.gateway_controller is None:
		try:
			data = frappe.get_doc(f"{payment_gateway} Settings").as_dict()
			meta = frappe.get_meta(f"{payment_gateway} Settings").fields
			doctype = f"{payment_gateway} Settings"
			docname = f"{payment_gateway} Settings"
		except Exception:
			frappe.throw(_("{0} Settings not found").format(payment_gateway))
	else:
		try:
			data = frappe.get_doc(gateway.gateway_settings, gateway.gateway_controller).as_dict()
			meta = frappe.get_meta(gateway.gateway_settings).fields
			doctype = gateway.gateway_settings
			docname = gateway.gateway_controller
		except Exception:
			frappe.throw(_("{0} Settings not found").format(payment_gateway))

	gateway_fields = get_transformed_fields(meta, data)

	return {
		"fields": gateway_fields,
		"data": data,
		"doctype": doctype,
		"docname": docname,
	}


def get_transformed_fields(meta, data=None):
	transformed_fields = []
	for row in meta:
		if row.fieldtype not in ["Column Break", "Section Break"]:
			if row.fieldtype in ["Attach", "Attach Image"]:
				fieldtype = "Upload"
				if data and data.get(row.fieldname):
					data[row.fieldname] = get_file_info(data.get(row.fieldname))
			elif row.fieldtype == "Check":
				fieldtype = "checkbox"
			else:
				fieldtype = row.fieldtype

			transformed_fields.append(
				{
					"label": row.label,
					"name": row.fieldname,
					"type": fieldtype,
				}
			)

	return transformed_fields


@frappe.whitelist()
def get_new_gateway_fields(doctype):
	try:
		meta = frappe.get_meta(doctype).fields
	except Exception:
		frappe.throw(_("{0} not found").format(doctype))

	transformed_fields = get_transformed_fields(meta)

	return transformed_fields


def update_course_statistics():
	courses = frappe.get_all("LMS Course", fields=["name"])

	for course in courses:
		lessons = get_lesson_count(course.name)

		enrollments = frappe.db.count("LMS Enrollment", {"course": course.name, "member_type": "Student"})

		avg_rating = get_average_rating(course.name) or 0
		avg_rating = flt(avg_rating, frappe.get_system_settings("float_precision") or 3)

		frappe.db.set_value(
			"LMS Course",
			course.name,
			{"lessons": lessons, "enrollments": enrollments, "rating": avg_rating},
		)


@frappe.whitelist()
def get_announcements(batch):
	communications = frappe.get_all(
		"Communication",
		filters={
			"reference_doctype": "LMS Batch",
			"reference_name": batch,
		},
		fields=[
			"subject",
			"content",
			"recipients",
			"cc",
			"communication_date",
			"sender",
			"sender_full_name",
		],
		order_by="communication_date desc",
	)

	for communication in communications:
		communication.image = frappe.get_cached_value("User", communication.sender, "user_image")

	return communications


@frappe.whitelist()
def delete_course(course):
	chapters = frappe.get_all("Course Chapter", {"course": course}, pluck="name")

	chapter_references = frappe.get_all("Chapter Reference", {"parent": course}, pluck="name")

	for chapter in chapters:
		lessons = frappe.get_all("Course Lesson", {"chapter": chapter}, pluck="name")

		lesson_references = frappe.get_all("Lesson Reference", {"parent": chapter}, pluck="name")

		for lesson in lesson_references:
			frappe.delete_doc("Lesson Reference", lesson)

		for lesson in lessons:
			topics = frappe.get_all(
				"Discussion Topic",
				{"reference_doctype": "Course Lesson", "reference_docname": lesson},
				pluck="name",
			)

			for topic in topics:
				frappe.db.delete("Discussion Reply", {"topic": topic})

				frappe.db.delete("Discussion Topic", topic)

			frappe.delete_doc("Course Lesson", lesson)

	for chapter in chapter_references:
		frappe.delete_doc("Chapter Reference", chapter)

	for chapter in chapters:
		frappe.delete_doc("Course Chapter", chapter)

	frappe.db.delete("LMS Course Progress", {"course": course})
	frappe.db.delete("LMS Quiz", {"course": course})
	frappe.db.delete("LMS Quiz Submission", {"course": course})
	frappe.db.delete("LMS Enrollment", {"course": course})
	frappe.delete_doc("LMS Course", course)


@frappe.whitelist()
def delete_batch(batch):
	frappe.db.delete("LMS Batch Enrollment", {"batch": batch})
	frappe.db.delete("Batch Course", {"parent": batch, "parenttype": "LMS Batch"})
	frappe.db.delete("LMS Assessment", {"parent": batch, "parenttype": "LMS Batch"})
	frappe.db.delete("LMS Batch Timetable", {"parent": batch, "parenttype": "LMS Batch"})
	frappe.db.delete("LMS Batch Feedback", {"batch": batch})
	delete_batch_discussions(batch)
	frappe.db.delete("LMS Batch", batch)


def delete_batch_discussions(batch):
	topics = frappe.get_all(
		"Discussion Topic",
		{"reference_doctype": "LMS Batch", "reference_docname": batch},
		pluck="name",
	)

	for topic in topics:
		frappe.db.delete("Discussion Reply", {"topic": topic})
		frappe.db.delete("Discussion Topic", topic)


def give_discussions_permission():
	doctypes = ["Discussion Topic", "Discussion Reply"]
	roles = ["LMS Student", "Course Creator", "Moderator", "Batch Evaluator"]
	for doctype in doctypes:
		for role in roles:
			if not frappe.db.exists("Custom DocPerm", {"parent": doctype, "role": role}):
				frappe.get_doc(
					{
						"doctype": "Custom DocPerm",
						"parent": doctype,
						"role": role,
						"read": 1,
						"write": 1,
						"create": 1,
						"delete": 1,
						"if_owner": 0 if role == "Moderator" else 1,
					}
				).save(ignore_permissions=True)


@frappe.whitelist()
def upsert_chapter(title, course, is_scorm_package, scorm_package, name=None):
	values = frappe._dict({"title": title, "course": course, "is_scorm_package": is_scorm_package})

	if is_scorm_package:
		scorm_package = frappe._dict(scorm_package)
		extract_path = extract_package(course, title, scorm_package)

		values.update(
			{
				"scorm_package": scorm_package.name,
				"scorm_package_path": extract_path.split("public")[1],
				"manifest_file": get_manifest_file(extract_path).split("public")[1],
				"launch_file": get_launch_file(extract_path).split("public")[1],
			}
		)

	if name:
		chapter = frappe.get_doc("Course Chapter", name)
	else:
		chapter = frappe.new_doc("Course Chapter")

	chapter.update(values)
	chapter.save()

	if is_scorm_package and not len(chapter.lessons):
		add_lesson(title, chapter.name, course, 1)

	return chapter


def extract_package(course, title, scorm_package):
	package = frappe.get_doc("File", scorm_package.name)
	zip_path = package.get_full_path()
	# check_for_malicious_code(zip_path)
	extract_path = frappe.get_site_path("public", "scorm", course, title)
	zipfile.ZipFile(zip_path).extractall(extract_path)
	return extract_path


def check_for_malicious_code(zip_path):
	suspicious_patterns = [
		# Unsafe inline JavaScript
		r'on(click|load|mouseover|error|submit|focus|blur|change|keyup|keydown|keypress|resize)=".*?"',  # Inline event handlers (e.g., onerror, onclick)
		r'<script.*?src=["\']http',  # External script tags
		r"eval\(",  # Usage of eval()
		r"Function\(",  # Usage of Function constructor
		r"(btoa|atob)\(",  # Base64 encoding/decoding
		# Dangerous XML patterns
		r"<!ENTITY",  # XXE-related
		r"<\?xml-stylesheet .*?>",  # External stylesheets in XML
	]

	with zipfile.ZipFile(zip_path, "r") as zf:
		for file_name in zf.namelist():
			if file_name.endswith((".html", ".js", ".xml")):
				with zf.open(file_name) as file:
					content = file.read().decode("utf-8", errors="ignore")
					for pattern in suspicious_patterns:
						if re.search(pattern, content):
							frappe.throw(_("Suspicious pattern found in {0}: {1}").format(file_name, pattern))


def get_manifest_file(extract_path):
	manifest_file = None
	for root, _dirs, files in os.walk(extract_path):
		for file in files:
			if file == "imsmanifest.xml":
				manifest_file = os.path.join(root, file)
				break
		if manifest_file:
			break
	return manifest_file


def get_launch_file(extract_path):
	launch_file = None
	manifest_file = get_manifest_file(extract_path)

	if manifest_file:
		with open(manifest_file) as file:
			data = file.read()
			dom = parseString(data)
			resource = dom.getElementsByTagName("resource")
			for res in resource:
				if (
					res.getAttribute("adlcp:scormtype") == "sco"
					or res.getAttribute("adlcp:scormType") == "sco"
				):
					launch_file = res.getAttribute("href")
					break

		if launch_file:
			launch_file = os.path.join(os.path.dirname(manifest_file), launch_file)

	return launch_file


def add_lesson(title, chapter, course, idx):
	lesson = frappe.new_doc("Course Lesson")
	lesson.update(
		{
			"title": title,
			"chapter": chapter,
			"course": course,
		}
	)
	lesson.insert(ignore_permissions=True)

	# Get the course chapter and add lesson reference as child table
	chapter_doc = frappe.get_doc("Course Chapter", chapter)
	lesson_reference = chapter_doc.append("lessons", {
		"lesson": lesson.name,
		"idx": idx,
	})
	chapter_doc.save(ignore_permissions=True)

	return lesson


def create_lesson_from_recording(live_class_name):
	"""
	Automatically create a lesson in course chapter when a Zoom recording becomes available.
	Creates lesson in all courses associated with the live class's batch.
	"""
	try:
		live_class = frappe.get_doc("LMS Live Class", live_class_name)
		
		if not live_class.recording_available or not live_class.recording_url:
			frappe.logger().info(f"[Recording Lesson] Recording not available yet for {live_class_name}")
			return
		
		if not live_class.batch_name:
			frappe.logger().info(f"[Recording Lesson] No batch associated with live class {live_class_name}")
			return
		
		# Get all courses from the batch
		batch_courses = frappe.get_all(
			"Batch Course",
			{"parent": live_class.batch_name},
			pluck="course",
			distinct=True
		)
		
		if not batch_courses:
			frappe.logger().info(f"[Recording Lesson] No courses found for batch {live_class.batch_name}")
			return
		
		# Check if lesson already exists for this live class
		existing_lesson = frappe.db.exists(
			"Course Lesson",
			{"content": f"live_class:{live_class_name}"}
		)
		
		if existing_lesson:
			frappe.logger().info(f"[Recording Lesson] Lesson already exists for live class {live_class_name}")
			return
		
		# Process each course
		for course_name in batch_courses:
			try:
				# Find or create "Recordings" chapter (ONE chapter per course for ALL recordings)
				# All recording lessons will be added to this same chapter
				chapter_name = frappe.db.exists(
					"Course Chapter",
					{"course": course_name, "title": "Recordings"}
				)
				
				if not chapter_name:
					# Create new "Recordings" chapter (only once per course)
					chapter = frappe.new_doc("Course Chapter")
					chapter.title = "Recordings"
					chapter.course = course_name
					chapter.insert(ignore_permissions=True)
					chapter_name = chapter.name

					# Add chapter to course via LMS Course
					course_doc = frappe.get_doc("LMS Course", course_name)
					course_doc.append("chapters", {
						"chapter": chapter_name,
					})
					course_doc.save(ignore_permissions=True)

					frappe.logger().info(f"[Recording Lesson] Created Recordings chapter for course {course_name}")
				else:
					frappe.logger().info(f"[Recording Lesson] Reusing existing Recordings chapter {chapter_name} for course {course_name}")
				
				# Get the chapter (existing or newly created) to find next lesson index
				# All recording lessons will be added to this same chapter
				chapter = frappe.get_doc("Course Chapter", chapter_name)
				max_lesson_idx = frappe.db.get_value(
					"Lesson Reference",
					{"parent": chapter_name},
					"max(idx)",
					as_dict=False
				) or 0
				
				# Create lesson with live class title
				lesson_title = live_class.title or f"Recording - {live_class.date}"
				lesson = add_lesson(lesson_title, chapter_name, course_name, max_lesson_idx + 1)
				
				# Store live class reference in lesson content for frontend to render recording
				lesson.content = f"live_class:{live_class_name}"
				if live_class.description:
					lesson.body = live_class.description
				lesson.save(ignore_permissions=True)
				
				frappe.logger().info(f"[Recording Lesson] Created lesson {lesson.name} for live class {live_class_name} in course {course_name}")
				
			except Exception as e:
				frappe.logger().error(f"[Recording Lesson] Error creating lesson for course {course_name}: {str(e)}")
				continue
				
	except Exception as e:
		frappe.logger().error(f"[Recording Lesson] Error in create_lesson_from_recording: {str(e)}")


@frappe.whitelist()
def delete_chapter(chapter):
	chapterInfo = frappe.db.get_value(
		"Course Chapter", chapter, ["is_scorm_package", "scorm_package_path"], as_dict=True
	)

	if chapterInfo.is_scorm_package:
		delete_scorm_package(chapterInfo.scorm_package_path)

	frappe.db.delete("Chapter Reference", {"chapter": chapter})
	frappe.db.delete("Lesson Reference", {"parent": chapter})
	frappe.db.delete("Course Lesson", {"chapter": chapter})
	frappe.db.delete("Course Chapter", chapter)


def delete_scorm_package(scorm_package_path):
	scorm_package_path = frappe.get_site_path("public", scorm_package_path[1:])
	if os.path.exists(scorm_package_path):
		shutil.rmtree(scorm_package_path)


@frappe.whitelist()
def mark_lesson_progress(course, chapter_number, lesson_number):
	chapter_name = frappe.get_value("Chapter Reference", {"parent": course, "idx": chapter_number}, "chapter")
	lesson_name = frappe.get_value(
		"Lesson Reference", {"parent": chapter_name, "idx": lesson_number}, "lesson"
	)
	save_progress(lesson_name, course)


@frappe.whitelist()
def get_heatmap_data(member=None, base_days=200):
	if not member:
		member = frappe.session.user

	base_date, start_date, number_of_days, days = calculate_date_ranges(base_days)
	date_count = initialize_date_count(days)

	lesson_completions, quiz_submissions, assignment_submissions = fetch_activity_data(member, start_date)
	count_dates(lesson_completions, date_count)
	count_dates(quiz_submissions, date_count)
	count_dates(assignment_submissions, date_count)

	heatmap_data, labels, total_activities, weeks = prepare_heatmap_data(
		start_date, number_of_days, date_count
	)

	return {
		"heatmap_data": heatmap_data,
		"labels": labels,
		"total_activities": total_activities,
		"weeks": weeks,
	}


def calculate_date_ranges(base_days):
	today = format_date(now(), "YYYY-MM-dd")
	day_today = get_datetime(today).strftime("%w")
	padding_end = 6 - cint(day_today)

	base_date = add_days(today, -base_days)
	day_of_base_date = cint(get_datetime(base_date).strftime("%w"))
	start_date = add_days(base_date, -day_of_base_date)
	number_of_days = base_days + day_of_base_date + padding_end
	days = [add_days(start_date, i) for i in range(number_of_days + 1)]

	return base_date, start_date, number_of_days, days


def initialize_date_count(days):
	return {format_date(day, "YYYY-MM-dd"): 0 for day in days}


def fetch_activity_data(member, start_date):
	lesson_completions = frappe.get_all(
		"LMS Course Progress",
		fields=["creation"],
		filters={"member": member, "creation": [">=", start_date], "status": "Complete"},
	)

	quiz_submissions = frappe.get_all(
		"LMS Quiz Submission",
		fields=["creation"],
		filters={"member": member, "creation": [">=", start_date]},
	)

	assignment_submissions = frappe.get_all(
		"LMS Assignment Submission",
		fields=["creation"],
		filters={"member": member, "creation": [">=", start_date]},
	)

	return lesson_completions, quiz_submissions, assignment_submissions


def count_dates(data, date_count):
	for entry in data:
		date = format_date(entry.creation, "YYYY-MM-dd")
		if date in date_count:
			date_count[date] += 1


def prepare_heatmap_data(start_date, number_of_days, date_count):
	days_of_week = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]
	heatmap_data = {day: [] for day in days_of_week}
	week_count = -(number_of_days // -7)
	labels = [None] * week_count
	last_seen_month = None
	sorted_dates = sorted(date_count.keys())

	for date in sorted_dates:
		activity_count = date_count[date]
		day_of_week = get_datetime(date).strftime("%a")
		current_month = get_datetime(date).strftime("%b")
		column_index = get_week_difference(start_date, date)

		if 0 <= column_index < week_count:
			heatmap_data[day_of_week].append(
				{
					"date": date,
					"count": activity_count,
					"label": f"{activity_count} activities on {format_date(date, 'dd MMM')}",
				}
			)

			if last_seen_month != current_month:
				labels[column_index] = current_month
				last_seen_month = current_month

	for index, label in enumerate(labels):
		if not label:
			labels[index] = ""

	formatted_heatmap_data = [{"name": day, "data": heatmap_data[day]} for day in days_of_week]

	total_activities = sum(date_count.values())
	return formatted_heatmap_data, labels, total_activities, week_count


def get_week_difference(start_date, current_date):
	diff_in_days = date_diff(current_date, start_date)
	return diff_in_days // 7


@frappe.whitelist()
def get_notifications(filters):
	notifications = frappe.get_all(
		"Notification Log",
		filters,
		["subject", "from_user", "link", "read", "name"],
		order_by="creation desc",
	)

	for notification in notifications:
		from_user_details = frappe.db.get_value(
			"User", notification.from_user, ["full_name", "user_image"], as_dict=1
		)
		notification.update(from_user_details)

	return notifications


@frappe.whitelist(allow_guest=True)
def get_lms_settings():
	allowed_fields = [
		"allow_guest_access",
		"prevent_skipping_videos",
		"contact_us_email",
		"contact_us_url",
		"livecode_url",
		"disable_pwa",
	]

	settings = frappe._dict()
	for field in allowed_fields:
		settings[field] = frappe.get_cached_value("LMS Settings", None, field)

	return settings


@frappe.whitelist()
def cancel_evaluation(evaluation):
	evaluation = frappe._dict(evaluation)

	if evaluation.member != frappe.session.user:
		return

	frappe.db.set_value("LMS Certificate Request", evaluation.name, "status", "Cancelled")
	events = frappe.get_all(
		"Event Participants",
		{
			"email": evaluation.member,
		},
		["parent", "name"],
	)

	for event in events:
		info = frappe.db.get_value("Event", event.parent, ["starts_on", "subject"], as_dict=1)
		date = str(info.starts_on).split(" ")[0]

		if date == str(evaluation.date.format("YYYY-MM-DD")) and evaluation.member_name in info.subject:
			communication = frappe.db.get_value(
				"Communication",
				{"reference_doctype": "Event", "reference_name": event.parent},
				"name",
			)
			if communication:
				frappe.delete_doc("Communication", communication, ignore_permissions=True)

			frappe.delete_doc("Event Participants", event.name, ignore_permissions=True)
			frappe.delete_doc("Event", event.parent, ignore_permissions=True)


@frappe.whitelist()
def get_certification_details(course):
	membership = None
	filters = {"course": course, "member": frappe.session.user}

	if frappe.db.exists("LMS Enrollment", filters):
		membership = frappe.db.get_value(
			"LMS Enrollment",
			filters,
			["name", "purchased_certificate"],
			as_dict=1,
		)

	paid_certificate = frappe.db.get_value("LMS Course", course, "paid_certificate")
	certificate = frappe.db.get_value(
		"LMS Certificate",
		{"member": frappe.session.user, "course": course},
		["name", "template"],
		as_dict=1,
	)

	return {
		"membership": membership,
		"paid_certificate": paid_certificate,
		"certificate": certificate,
	}


@frappe.whitelist()
def save_role(user, role, value):
	frappe.only_for("Moderator")
	if cint(value):
		doc = frappe.get_doc(
			{
				"doctype": "Has Role",
				"parent": user,
				"role": role,
				"parenttype": "User",
				"parentfield": "roles",
			}
		)
		doc.save(ignore_permissions=True)
	else:
		frappe.db.delete("Has Role", {"parent": user, "role": role})
	frappe.clear_cache(user=user)
	return True


@frappe.whitelist()
def add_an_evaluator(email):
	frappe.only_for("Moderator")
	if not frappe.db.exists("User", email):
		user = frappe.new_doc("User")
		user.update(
			{
				"email": email,
				"first_name": email.split("@")[0].capitalize(),
				"enabled": 1,
			}
		)
		user.insert()
		user.add_roles("Batch Evaluator")

	evaluator = frappe.new_doc("Course Evaluator")
	evaluator.evaluator = email
	evaluator.insert()

	return evaluator


@frappe.whitelist()
def delete_evaluator(evaluator):
	frappe.only_for("Moderator")
	if not frappe.db.exists("Course Evaluator", evaluator):
		frappe.throw(_("Evaluator does not exist."))

	frappe.db.delete("Has Role", {"parent": evaluator, "role": "Batch Evaluator"})
	frappe.db.delete("Course Evaluator", evaluator)


@frappe.whitelist()
def capture_user_persona(responses):
	frappe.only_for("System Manager")
	data = frappe.parse_json(responses)
	data = json.dumps(data)
	response = frappe.integrations.utils.make_post_request(
		"https://school.frappe.io/api/method/capture-persona",
		data={"response": data},
	)
	if response.get("message").get("name"):
		frappe.db.set_single_value("LMS Settings", "persona_captured", True)
	return response


@frappe.whitelist()
def get_meta_info(type, route):
	if frappe.db.exists("Website Meta Tag", {"parent": f"{type}/{route}"}):
		meta_tags = frappe.get_all(
			"Website Meta Tag",
			{
				"parent": f"{type}/{route}",
			},
			["name", "key", "value"],
		)

		return meta_tags

	return []


@frappe.whitelist()
def update_meta_info(meta_type, route, meta_tags):
	validate_meta_data_permissions(meta_type)
	validate_meta_tags(meta_tags)

	parent_name = f"{meta_type}/{route}"
	for tag in meta_tags:
		existing_tag = frappe.db.exists(
			"Website Meta Tag",
			{
				"parent": parent_name,
				"parenttype": "Website Route Meta",
				"parentfield": "meta_tags",
				"key": tag["key"],
			},
		)
		if existing_tag:
			if not tag.get("value"):
				frappe.db.delete("Website Meta Tag", existing_tag)
				continue
			frappe.db.set_value("Website Meta Tag", existing_tag, "value", tag["value"])
		elif tag.get("value"):
			tag_properties = {
				"parent": parent_name,
				"parenttype": "Website Route Meta",
				"parentfield": "meta_tags",
				"key": tag["key"],
				"value": tag["value"],
			}

			parent_exists = frappe.db.exists("Website Route Meta", parent_name)
			if not parent_exists:
				create_meta(parent_name, tag_properties)
			else:
				create_meta_tag(tag_properties)


def validate_meta_tags(meta_tags):
	if not isinstance(meta_tags, list):
		frappe.throw(_("Meta tags should be a list."))


def create_meta(parent_name, tag_properties):
	route_meta = frappe.new_doc("Website Route Meta")
	route_meta.update(
		{
			"__newname": parent_name,
		}
	)
	route_meta.append("meta_tags", tag_properties)
	route_meta.insert()


def create_meta_tag(tag_properties):
	new_tag = frappe.new_doc("Website Meta Tag")
	new_tag.update(tag_properties)
	new_tag.insert()


def validate_meta_data_permissions(meta_type):
	roles = frappe.get_roles()

	if meta_type == "courses":
		if not ("Course Creator" in roles or "Moderator" in roles):
			frappe.throw(_("You do not have permission to update meta tags."))

	elif meta_type == "batches":
		if not ("Batch Evaluator" in roles or "Moderator" in roles):
			frappe.throw(_("You do not have permission to update meta tags."))


@frappe.whitelist()
def create_programming_exercise_submission(exercise, submission, code, test_cases):
	if submission == "new":
		return make_new_exercise_submission(exercise, code, test_cases)
	else:
		update_exercise_submission(submission, code, test_cases)


def make_new_exercise_submission(exercise, code, test_cases):
	submission = frappe.new_doc("LMS Programming Exercise Submission")
	submission.exercise = exercise
	submission.member = frappe.session.user
	submission.code = code

	for test_case in test_cases:
		submission.append(
			"test_cases",
			{
				"input": test_case.get("input"),
				"output": test_case.get("output"),
				"expected_output": test_case.get("expected_output"),
				"status": test_case.get("status", test_case.get("status", "Failed")),
			},
		)

	submission.status = get_exercise_status(test_cases)
	submission.insert()
	return submission.name


def update_exercise_submission(submission, code, test_cases):
	update_test_cases(test_cases, submission)
	status = get_exercise_status(test_cases)
	frappe.db.set_value("LMS Programming Exercise Submission", submission, {"status": status, "code": code})


def get_exercise_status(test_cases):
	if not test_cases:
		return "Failed"

	if all(row.get("status", "Failed") == "Passed" for row in test_cases):
		return "Passed"
	else:
		return "Failed"


def update_test_cases(test_cases, submission):
	frappe.db.delete("LMS Test Case Submission", {"parent": submission})
	for row in test_cases:
		test_case = frappe.new_doc("LMS Test Case Submission")
		test_case.update(
			{
				"parent": submission,
				"parenttype": "LMS Programming Exercise Submission",
				"parentfield": "test_cases",
				"input": row.get("input"),
				"output": row.get("output"),
				"expected_output": row.get("expected_output"),
				"status": row.get("status", "Failed"),
			}
		)
		test_case.insert()


@frappe.whitelist()
def track_video_watch_duration(lesson, videos):
	"""
	Track the watch duration of videos in a lesson.
	"""
	if not isinstance(videos, list):
		videos = json.loads(videos)

	for video in videos:
		filters = {
			"lesson": lesson,
			"source": video.get("source"),
			"member": frappe.session.user,
		}
		existing_record = frappe.db.get_value(
			"LMS Video Watch Duration", filters, ["name", "watch_time"], as_dict=True
		)
		if existing_record and flt(existing_record.watch_time) < flt(video.get("watch_time")):
			frappe.db.set_value(
				"LMS Video Watch Duration",
				filters,
				"watch_time",
				video.get("watch_time"),
			)
		elif not existing_record:
			track_new_watch_time(lesson, video)


def track_new_watch_time(lesson, video):
	doc = frappe.new_doc("LMS Video Watch Duration")
	doc.lesson = lesson
	doc.source = video.get("source")
	doc.watch_time = video.get("watch_time")
	doc.member = frappe.session.user
	doc.save()


@frappe.whitelist()
def get_course_progress_distribution(course):
	all_progress = frappe.get_all(
		"LMS Enrollment",
		{
			"course": course,
		},
		pluck="progress",
	)

	average_progress = get_average_course_progress(all_progress)
	progress_distribution = get_progress_distribution(all_progress)

	return {
		"average_progress": average_progress,
		"progress_distribution": progress_distribution,
	}


def get_average_course_progress(progress_list):
	if not progress_list:
		return 0
	average_progress = sum(progress_list) / len(progress_list)
	return flt(average_progress, frappe.get_system_settings("float_precision") or 3)


def get_progress_distribution(progressList):
	distribution = [
		{
			"category": "0-20%",
			"count": len([p for p in progressList if 0 <= p < 20]),
		},
		{
			"category": "20-40%",
			"count": len([p for p in progressList if 20 <= p < 40]),
		},
		{
			"category": "40-60%",
			"count": len([p for p in progressList if 40 <= p < 60]),
		},
		{
			"category": "60-80%",
			"count": len([p for p in progressList if 60 <= p < 80]),
		},
		{
			"category": "80-100%",
			"count": len([p for p in progressList if 80 <= p <= 100]),
		},
	]

	return distribution


@frappe.whitelist(allow_guest=True)
def get_pwa_manifest():
	title = frappe.db.get_single_value("Website Settings", "app_name") or "Frappe Learning"
	banner_image = frappe.db.get_single_value("Website Settings", "banner_image")

	manifest = {
		"name": title,
		"short_name": title,
		"description": "Easy to use, 100% open source Learning Management System",
		"start_url": "/lms",
		"icons": [
			{
				"src": banner_image or "/assets/lms/frontend/manifest/manifest-icon-192.maskable.png",
				"sizes": "192x192",
				"type": "image/png",
				"purpose": "maskable any",
			}
		],
	}

	return Response(json.dumps(manifest), status=200, content_type="application/manifest+json")


@frappe.whitelist()
def get_profile_details(username):
	details = frappe.db.get_value(
		"User",
		{"username": username},
		[
			"first_name",
			"last_name",
			"full_name",
			"name",
			"username",
			"user_image",
			"bio",
			"headline",
			"language",
			"cover_image",
			"looking_for_job",
			"linkedin",
			"github",
			"twitter",
		],
		as_dict=True,
	)

	details.roles = frappe.get_roles(details.name)
	return details


@frappe.whitelist()
def get_streak_info():
	if frappe.session.user == "Guest":
		return {}

	all_dates = fetch_activity_dates(frappe.session.user)
	streak, longest_streak = calculate_streaks(all_dates)
	current_streak = calculate_current_streak(all_dates, streak)

	return {
		"current_streak": current_streak,
		"longest_streak": longest_streak,
	}


def fetch_activity_dates(user):
	doctypes = [
		"LMS Course Progress",
		"LMS Quiz Submission",
		"LMS Assignment Submission",
		"LMS Programming Exercise Submission",
	]

	all_dates = []
	for dt in doctypes:
		all_dates.extend(frappe.get_all(dt, {"member": user}, pluck="creation"))

	return sorted({d.date() if hasattr(d, "date") else d for d in all_dates})


def calculate_streaks(all_dates):
	streak = 0
	longest_streak = 0
	prev_day = None

	for d in all_dates:
		if d.weekday() in (5, 6):
			continue

		if prev_day:
			expected = prev_day + timedelta(days=1)
			while expected.weekday() in (5, 6):
				expected += timedelta(days=1)

			streak = streak + 1 if d == expected else 1
		else:
			streak = 1

		longest_streak = max(longest_streak, streak)
		prev_day = d

	return streak, longest_streak


def calculate_current_streak(all_dates, streak):
	if not all_dates:
		return 0

	last_date = all_dates[-1]
	today = getdate()

	ref_day = today
	while ref_day.weekday() in (5, 6):
		ref_day -= timedelta(days=1)

	if last_date == ref_day or last_date == ref_day - timedelta(days=1):
		return streak
	return 0


@frappe.whitelist()
def get_my_live_classes():
	my_live_classes = []
	if frappe.session.user == "Guest":
		return my_live_classes

	# Get batches where user is enrolled as a student
	enrolled_batches = frappe.get_all(
		"LMS Batch Enrollment",
		{
			"member": frappe.session.user,
		},
		order_by="creation desc",
		pluck="batch",
	)

	# Get batches where user is a course instructor (for teachers)
	instructor_batches = frappe.get_all(
		"Course Instructor",
		{
			"instructor": frappe.session.user,
		},
		pluck="parent",
	)

	# Combine both lists and remove duplicates
	all_batches = list(set(enrolled_batches + instructor_batches))

	if not all_batches:
		return my_live_classes

	live_class_details = frappe.get_all(
		"LMS Live Class",
		filters={
			"date": [">=", getdate()],
			"batch_name": ["in", all_batches],
		},
		fields=[
			"name",
			"title",
			"description",
			"time",
			"date",
			"duration",
			"attendees",
			"start_url",
			"join_url",
			"owner",
			"batch_name",
		],
		limit=2,
		order_by="date",
	)

	if len(live_class_details):
		for live_class in live_class_details:
			my_live_classes.append(live_class)

	return my_live_classes


@frappe.whitelist()
def get_all_my_live_classes():
	"""Get all live classes for enrolled students (for Live tab in Courses page)"""
	all_live_classes = []
	if frappe.session.user == "Guest":
		return all_live_classes

	# Get enrolled batches
	enrolled_batches = frappe.get_all(
		"LMS Batch Enrollment",
		{"member": frappe.session.user},
		pluck="batch"
	)

	if not enrolled_batches:
		return all_live_classes

	# Get all live classes from enrolled batches (current or upcoming)
	live_class_details = frappe.get_all(
		"LMS Live Class",
		filters={
			"date": [">=", getdate()],
			"batch_name": ["in", enrolled_batches],
		},
		fields=[
			"name",
			"title",
			"description",
			"time",
			"date",
			"duration",
			"attendees",
			"start_url",
			"join_url",
			"owner",
			"batch_name",
		],
		order_by="date asc",
	)

	# Get batch and course information for each live class
	for live_class in live_class_details:
		# Get batch details
		batch = frappe.get_doc("LMS Batch", live_class.batch_name)
		live_class.batch_title = batch.title
		
		# Get course from batch
		batch_courses = frappe.get_all(
			"Batch Course",
			{"parent": live_class.batch_name},
			pluck="course",
			limit=1
		)
		
		if batch_courses:
			course = frappe.get_doc("LMS Course", batch_courses[0])
			live_class.course_name = course.name
			live_class.course_title = course.title
			live_class.course_image = course.image
		
		all_live_classes.append(live_class)

	return all_live_classes


@frappe.whitelist()
def get_recorded_courses():
	"""Get courses with recorded lectures for enrolled students"""
	recorded_courses = []
	if frappe.session.user == "Guest":
		return recorded_courses

	# Get all batches the student is enrolled in
	enrolled_batches = frappe.get_all(
		"LMS Batch Enrollment",
		{"member": frappe.session.user},
		pluck="batch"
	)

	if not enrolled_batches:
		return recorded_courses

	# Get all live classes from enrolled batches that have recordings
	live_classes_with_recordings = frappe.get_all(
		"LMS Live Class",
		filters={
			"batch_name": ["in", enrolled_batches],
			"auto_recording": ["!=", "No Recording"],
		},
		fields=["batch_name", "name"],
	)

	if not live_classes_with_recordings:
		return recorded_courses

	# Get unique batches that have recorded lectures
	batches_with_recordings = list(set([lc.batch_name for lc in live_classes_with_recordings]))

	# Get courses from those batches
	BatchCourse = frappe.qb.DocType("Batch Course")
	Course = frappe.qb.DocType("LMS Course")

	query = (
		frappe.qb.from_(BatchCourse)
		.join(Course)
		.on(BatchCourse.course == Course.name)
		.select(Course.name)
		.where(BatchCourse.parent.isin(batches_with_recordings))
		.where(Course.published == 1)
		.distinct()
	)

	results = query.run(as_dict=True)
	course_names = [row["name"] for row in results]

	# Also check direct course enrollments
	enrolled_courses = frappe.get_all(
		"LMS Enrollment",
		{"member": frappe.session.user},
		pluck="course"
	)

	# Combine batch courses and directly enrolled courses
	all_course_names = list(set(course_names + enrolled_courses))

	# Get course details
	for course_name in all_course_names:
		course_details = get_course_details(course_name)
		# Verify the course has recorded lectures
		batch_courses = frappe.get_all(
			"Batch Course",
			{"course": course_name},
			pluck="parent"
		)
		if batch_courses:
			# Check if any batch has recorded lectures
			has_recordings = frappe.db.exists(
				"LMS Live Class",
				{
					"batch_name": ["in", batch_courses],
					"auto_recording": ["!=", "No Recording"],
				}
			)
			if has_recordings:
				recorded_courses.append(course_details)
		else:
			# Direct enrollment - check if course has any batches with recordings
			# For now, include all enrolled courses (can be refined later)
			recorded_courses.append(course_details)

	return recorded_courses


@frappe.whitelist()
def get_recorded_lectures(course_name=None):
	"""Get recorded lectures for enrolled students"""
	if frappe.session.user == "Guest":
		return []
	
	# Get enrolled batches
	enrolled_batches = frappe.get_all(
		"LMS Batch Enrollment",
		{"member": frappe.session.user},
		pluck="batch"
	)
	
	# Get enrolled courses
	enrolled_courses = frappe.get_all(
		"LMS Enrollment",
		{"member": frappe.session.user},
		pluck="course"
	)
	
	frappe.logger().info(f"[Recorded Lectures] User {frappe.session.user}: enrolled_batches={len(enrolled_batches)}, enrolled_courses={len(enrolled_courses)}")
	
	# Get courses from batches
	if enrolled_batches:
		batch_courses = frappe.get_all(
			"Batch Course",
			{"parent": ["in", enrolled_batches]},
			pluck="course",
			distinct=True
		)
		enrolled_courses = list(set(enrolled_courses + batch_courses))
	
	# Filter by course if provided
	if course_name:
		if course_name not in enrolled_courses:
			frappe.throw(_("You are not enrolled in this course"))
		enrolled_courses = [course_name]
	
	# If no enrolled batches but student has enrolled courses, find batches containing those courses
	if not enrolled_batches and enrolled_courses:
		# Find batches that contain enrolled courses
		batches_with_courses = frappe.get_all(
			"Batch Course",
			{"course": ["in", enrolled_courses]},
			pluck="parent",
			distinct=True
		)
		enrolled_batches = batches_with_courses
		frappe.logger().info(f"[Recorded Lectures] Found {len(enrolled_batches)} batches from enrolled courses")
	
	# If still no batches, return empty
	if not enrolled_batches:
		frappe.logger().info(f"[Recorded Lectures] No enrolled batches found for user {frappe.session.user}")
		return []
	
	# Get live classes with recordings from enrolled batches
	# Include both available recordings and those that might still be processing
	# (auto_recording enabled but recording_available might be 0 if still processing)
	live_classes = frappe.get_all(
		"LMS Live Class",
		filters={
			"batch_name": ["in", enrolled_batches],
			"auto_recording": ["!=", "No Recording"]
		},
		fields=[
			"name",
			"title",
			"description",
			"date",
			"time",
			"duration",
			"batch_name",
			"recording_available",
			"meeting_id"
		],
		order_by="date desc"
	)
	
	frappe.logger().info(f"[Recorded Lectures] Found {len(live_classes)} live classes with auto_recording enabled")
	
	# Get course info for each batch and filter by enrollment
	result = []
	for live_class in live_classes:
		batch_courses = frappe.get_all(
			"Batch Course",
			{"parent": live_class.batch_name},
			pluck="course"
		)
		# Only include if student is enrolled in at least one course from this batch
		if not any(course in enrolled_courses for course in batch_courses):
			continue
		
		# Get course details
		if batch_courses:
			course = frappe.get_doc("LMS Course", batch_courses[0])
			live_class.course_name = course.name
			live_class.course_title = course.title
			live_class.course_image = course.image
			
			# Add status field to indicate if recording is processing
			if not live_class.recording_available:
				# Check if class has ended (recording might still be processing)
				from datetime import datetime
				try:
					class_start = datetime.combine(
						getdate(live_class.date),
						datetime.strptime(str(live_class.time), "%H:%M:%S").time() if isinstance(live_class.time, str) else live_class.time
					)
					class_end = class_start + timedelta(minutes=cint(live_class.duration))
					
					if datetime.now() > class_end:
						# Class has ended, recording might be processing
						live_class.recording_status = "processing"
					else:
						# Class hasn't ended yet
						live_class.recording_status = "not_started"
				except (ValueError, TypeError):
					# If date/time parsing fails, assume processing
					live_class.recording_status = "processing"
			else:
				live_class.recording_status = "available"
			
			result.append(live_class)
	
	frappe.logger().info(f"[Recorded Lectures] Returning {len(result)} recorded lectures for user {frappe.session.user}")
	return result


@frappe.whitelist()
def get_recording_embed_url(live_class):
	"""
	Get secure token for recording access (doesn't expose actual Zoom URL to frontend).
	Token is valid for the duration of the recording.
	Returns a token that frontend uses to request the secure embed endpoint.
	"""
	if frappe.session.user == "Guest":
		frappe.throw(_("Please login to view recordings"))

	try:
		live_class_doc = frappe.get_doc("LMS Live Class", live_class)
	except frappe.DoesNotExistError:
		frappe.logger().error(f"[Recording Embed] Live class not found: {live_class}")
		frappe.throw(_("Live class not found"))

	# Check if user is admin/moderator (skip enrollment check)
	user_roles = frappe.get_roles(frappe.session.user)
	is_privileged = any(role in user_roles for role in ["System Manager", "LMS Admin", "Moderator", "Course Creator"])

	if not is_privileged:
		# Verify user has access (enrolled in batch)
		enrolled_batches = frappe.get_all(
			"LMS Batch Enrollment",
			{"member": frappe.session.user},
			pluck="batch"
		)

		has_batch_access = live_class_doc.batch_name and live_class_doc.batch_name in enrolled_batches

		if not has_batch_access:
			# Also check if user is enrolled in course directly
			batch_courses = []
			if live_class_doc.batch_name:
				batch_courses = frappe.get_all(
					"Batch Course",
					{"parent": live_class_doc.batch_name},
					pluck="course"
				)
			enrolled_courses = frappe.get_all(
				"LMS Enrollment",
				{"member": frappe.session.user},
				pluck="course"
			)

			if not batch_courses or not any(course in enrolled_courses for course in batch_courses):
				frappe.logger().warning(f"[Recording Embed] Access denied for user {frappe.session.user} to live class {live_class}")
				frappe.throw(_("You don't have access to this recording"))

	# Log current recording status
	frappe.logger().info(f"[Recording Embed] Live class {live_class}: recording_available={live_class_doc.recording_available}, recording_url={bool(live_class_doc.recording_url)}, meeting_id={live_class_doc.meeting_id}")

	if not live_class_doc.recording_available or not live_class_doc.recording_url:
		frappe.logger().info(f"[Recording Embed] Recording not available, attempting to fetch for {live_class}")
		# Try to fetch recording
		from lms.lms.doctype.lms_live_class.lms_live_class import fetch_recording
		try:
			recording_data = fetch_recording(live_class)
			if recording_data:
				frappe.logger().info(f"[Recording Embed] Fetch result: recording_available={recording_data.get('recording_available')}, status={recording_data.get('status')}")
			else:
				frappe.logger().warning(f"[Recording Embed] fetch_recording returned None for {live_class}")
				recording_data = {}
		except Exception as e:
			frappe.logger().error(f"[Recording Embed] Error fetching recording: {str(e)}")
			frappe.log_error(title="Recording Embed Fetch Error", message=frappe.get_traceback())
			recording_data = {
				"recording_available": False,
				"status": "error",
				"message": _("Error fetching recording. Please try again later.")
			}

		if not recording_data or not recording_data.get("recording_available"):
			# Return processing status instead of throwing error
			frappe.logger().info(f"[Recording Embed] Returning processing status for {live_class}")
			return {
				"embed_url": None,
				"recording_available": False,
				"status": recording_data.get("status", "processing") if recording_data else "processing",
				"message": recording_data.get("message", _("Recording is being processed. Please check back in a few minutes.")) if recording_data else _("Recording is being processed. Please check back in a few minutes."),
				"title": live_class_doc.title,
				"description": live_class_doc.description
			}

		live_class_doc.reload()

	# Log access
	_log_recording_access(live_class_doc.name, "request", frappe.session.user)

	# Generate secure token with expiration based on recording duration
	token = frappe.generate_hash(length=32)

	# Calculate token TTL: recording duration + 30 minute buffer for user convenience
	# Get duration from live class (in minutes), fallback to 120 minutes (2 hours)
	recording_duration_minutes = live_class_doc.duration or 120
	ttl_seconds = (recording_duration_minutes * 60) + 1800  # Add 30 min buffer

	current_time = now()
	expires_at = current_time + timedelta(seconds=ttl_seconds)

	# Store token in cache with expiration
	cache_key = f"recording_token_{live_class_doc.name}_{frappe.session.user}_{token}"
	frappe.cache().set_value(
		cache_key,
		{
			"live_class": live_class_doc.name,
			"user": frappe.session.user,
			"created_at": current_time,
			"expires_at": expires_at,
			"recording_duration": recording_duration_minutes,
			"ip_address": frappe.request.remote_addr if frappe.request else "unknown"
		},
		expires_in_sec=ttl_seconds
	)

	return {
		"token": token,
		"title": live_class_doc.title,
		"description": live_class_doc.description,
		"recording_available": True
	}


@frappe.whitelist()
def get_recording_secure(token, live_class):
	"""
	Secure backend proxy for recording embed.
	Validates token and access, then returns HTML with embedded recording.
	Actual Zoom URL never exposed to frontend.
	"""
	if frappe.session.user == "Guest":
		frappe.throw(_("Please login to view recordings"))

	# Validate request origin (prevent external embedding)
	referer = frappe.request.headers.get('Referer', '') if frappe.request else ''
	site_url = frappe.utils.get_url()

	if referer:
		# Normalize URLs to handle protocol/port mismatches
		# Extract domain from both URLs for comparison
		from urllib.parse import urlparse
		referer_parsed = urlparse(referer)
		site_parsed = urlparse(site_url)

		referer_domain = f"{referer_parsed.scheme}://{referer_parsed.netloc}"
		site_domain = f"{site_parsed.scheme}://{site_parsed.netloc}"

		# Also check if referer matches without protocol (handles mixed HTTP/HTTPS)
		referer_netloc = referer_parsed.netloc
		site_netloc = site_parsed.netloc

		if referer_domain != site_domain and referer_netloc != site_netloc:
			frappe.logger().warning(
				f"[Recording Security] Invalid referer: {referer} (expected: {site_url}) for user {frappe.session.user}"
			)
			frappe.throw(_("Access denied: Invalid request origin"))

	# Get live class document first to normalize the name
	live_class_doc = frappe.get_doc("LMS Live Class", live_class)

	# Validate token using normalized live_class_doc.name (same as how it was stored)
	cache_key = f"recording_token_{live_class_doc.name}_{frappe.session.user}_{token}"
	token_data = frappe.cache().get_value(cache_key)

	if not token_data:
		frappe.throw(_("Recording access token expired or invalid. Please reload and try again."))

	# Check if user is admin/moderator (skip enrollment check)
	user_roles = frappe.get_roles(frappe.session.user)
	is_privileged = any(role in user_roles for role in ["System Manager", "LMS Admin", "Moderator", "Course Creator"])

	if not is_privileged:
		# Re-verify access (enrollment could have changed)
		has_access = False

		# Check batch enrollment
		if live_class_doc.batch_name:
			enrolled_batches = frappe.get_all(
				"LMS Batch Enrollment",
				{"member": frappe.session.user},
				pluck="batch"
			)
			if live_class_doc.batch_name in enrolled_batches:
				has_access = True

			# If not directly in batch, check course enrollment via batch
			if not has_access:
				batch_courses = frappe.get_all(
					"Batch Course",
					{"parent": live_class_doc.batch_name},
					pluck="course"
				)
				if batch_courses:
					enrolled_courses = frappe.get_all(
						"LMS Enrollment",
						{"member": frappe.session.user},
						pluck="course"
					)
					if any(course in enrolled_courses for course in batch_courses):
						has_access = True

		# If no batch or batch check failed, check direct course enrollment
		if not has_access:
			# Try to find course from batch (if batch exists)
			course_to_check = None
			if live_class_doc.batch_name:
				batch_courses = frappe.get_all(
					"Batch Course",
					{"parent": live_class_doc.batch_name},
					pluck="course"
				)
				course_to_check = batch_courses[0] if batch_courses else None

			# If we found a course, check enrollment
			if course_to_check:
				user_courses = frappe.get_all(
					"LMS Enrollment",
					{"member": frappe.session.user},
					pluck="course"
				)
				if course_to_check in user_courses:
					has_access = True

		if not has_access:
			frappe.throw(_("You don't have access to this recording"))

	# Log access
	_log_recording_access(live_class_doc.name, "view", frappe.session.user)

	recording_url = live_class_doc.recording_url
	password = live_class_doc.recording_password or ""

	if not recording_url:
		frappe.throw(_("Recording URL not found"))

	# Handle password in URL if needed
	# Note: Password should already be embedded at webhook stage, but add as fallback
	embed_url = recording_url
	frappe.logger().info(f"[Recording Secure] Processing URL - has_password={bool(password)}, pwd_in_url={'pwd=' in recording_url}, access_token_in_url={'access_token=' in recording_url}")

	# Only add password if:
	# 1. We have a password
	# 2. It's not already in the URL (from webhook)
	# 3. There's no access_token (which bypasses password)
	if password and "pwd=" not in recording_url and "password=" not in recording_url and "access_token=" not in recording_url:
		try:
			from urllib.parse import quote
			# Add password to URL as fallback (should already be embedded from webhook)
			separator = "&" if "?" in recording_url else "?"
			embed_url = f"{recording_url}{separator}pwd={quote(password, safe='')}"
			frappe.logger().info(f"[Recording Secure] Added password to URL (fallback from webhook)")
		except Exception as e:
			frappe.logger().error(f"[Recording Secure] Error adding password to URL: {str(e)}")
			embed_url = recording_url
	elif "pwd=" in recording_url or "access_token=" in recording_url:
		frappe.logger().info(f"[Recording Secure] Password/token already embedded in URL from webhook")
	else:
		frappe.logger().warning(f"[Recording Secure] No password found in recording_password field for {live_class}")

	# Return HTML with embedded iframe (URL stays on backend)
	# HTML-escape title to prevent XSS attacks
	import html
	safe_title = html.escape(live_class_doc.title or "Recording")

	html_content = f'''
	<div class="recording-container" style="position: relative; width: 100%; padding-bottom: 56.25%; height: 0; overflow: hidden; border-radius: 0.375rem;">
		<iframe
			src="{embed_url}"
			style="position: absolute; top: 0; left: 0; width: 100%; height: 100%; border: 0;"
			frameborder="0"
			sandbox="allow-scripts allow-same-origin allow-presentation"
			allowfullscreen="true"
			allow="autoplay; encrypted-media; fullscreen; picture-in-picture"
			title="{safe_title}"
			referrerpolicy="no-referrer"
			controlsList="nodownload">
		</iframe>
	</div>
	'''

	# Add security headers to prevent external embedding and protect against attacks
	response = Response(html_content, status=200, content_type="text/html")
	response.headers['X-Frame-Options'] = 'SAMEORIGIN'  # Allow embedding on same domain, CSP provides additional restrictions
	response.headers['X-Content-Type-Options'] = 'nosniff'
	response.headers['Referrer-Policy'] = 'no-referrer'
	response.headers['Content-Security-Policy'] = "frame-ancestors 'self'; script-src 'unsafe-inline' https://zoom.us https://*.zoom.us; frame-src https://zoom.us https://*.zoom.us; style-src 'unsafe-inline' https://zoom.us https://*.zoom.us"
	response.headers['Permissions-Policy'] = "autoplay=(self), encrypted-media=(self), fullscreen=(self), picture-in-picture=(self)"
	return response


def _log_recording_access(live_class_name, access_type, user):
	"""Log recording access for audit trail"""
	try:
		log_doc = frappe.new_doc("LMS Recording Access Log")
		log_doc.live_class = live_class_name
		log_doc.user = user
		log_doc.access_type = access_type  # "request" or "view"
		log_doc.timestamp = now()
		log_doc.ip_address = frappe.request.remote_addr if frappe.request else "unknown"
		log_doc.insert(ignore_permissions=True)
	except Exception as e:
		# Don't fail recording access if logging fails
		frappe.logger().warning(f"Failed to log recording access: {e}")


@frappe.whitelist()
def get_created_courses():
	created_courses = []
	if frappe.session.user == "Guest":
		return created_courses

	CourseInstructor = frappe.qb.DocType("Course Instructor")
	Course = frappe.qb.DocType("LMS Course")

	query = (
		frappe.qb.from_(CourseInstructor)
		.join(Course)
		.on(CourseInstructor.parent == Course.name)
		.select(Course.name)
		.where(CourseInstructor.instructor == frappe.session.user)
		.orderby(Course.published_on, order=frappe.qb.desc)
		.limit(3)
	)

	results = query.run(as_dict=True)
	courses = [row["name"] for row in results]

	for course in courses:
		course_details = get_course_details(course)
		created_courses.append(course_details)

	return created_courses


@frappe.whitelist()
def get_created_batches():
	created_batches = []
	if frappe.session.user == "Guest":
		return created_batches

	CourseInstructor = frappe.qb.DocType("Course Instructor")
	Batch = frappe.qb.DocType("LMS Batch")

	query = (
		frappe.qb.from_(CourseInstructor)
		.join(Batch)
		.on(CourseInstructor.parent == Batch.name)
		.select(Batch.name)
		.where(CourseInstructor.instructor == frappe.session.user)
		.where(Batch.start_date >= getdate())
		.orderby(Batch.start_date, order=frappe.qb.asc)
		.limit(4)
	)

	results = query.run(as_dict=True)
	batches = [row["name"] for row in results]

	for batch in batches:
		batch_details = get_batch_details(batch)
		created_batches.append(batch_details)

	return created_batches


@frappe.whitelist()
def get_admin_live_classes():
	if frappe.session.user == "Guest":
		return []

	CourseInstructor = frappe.qb.DocType("Course Instructor")
	LMSLiveClass = frappe.qb.DocType("LMS Live Class")

	query = (
		frappe.qb.from_(CourseInstructor)
		.join(LMSLiveClass)
		.on(CourseInstructor.parent == LMSLiveClass.batch_name)
		.select(
			LMSLiveClass.name,
			LMSLiveClass.title,
			LMSLiveClass.description,
			LMSLiveClass.time,
			LMSLiveClass.date,
			LMSLiveClass.duration,
			LMSLiveClass.attendees,
			LMSLiveClass.start_url,
			LMSLiveClass.join_url,
			LMSLiveClass.owner,
		)
		.where(CourseInstructor.instructor == frappe.session.user)
		.where(LMSLiveClass.date >= getdate())
		.orderby(LMSLiveClass.date, order=frappe.qb.asc)
		.limit(4)
	)
	results = query.run(as_dict=True)
	return results


@frappe.whitelist()
def get_admin_evals():
	if frappe.session.user == "Guest":
		return []

	evals = frappe.get_all(
		"LMS Certificate Request",
		{
			"evaluator": frappe.session.user,
			"date": [">=", getdate()],
		},
		[
			"name",
			"date",
			"start_time",
			"course",
			"evaluator",
			"google_meet_link",
			"member",
			"member_name",
		],
		limit=4,
		order_by="date asc",
	)

	for evaluation in evals:
		evaluation.course_title = frappe.db.get_value("LMS Course", evaluation.course, "title")

	return evals


@frappe.whitelist()
def get_my_courses():
	my_courses = []
	if frappe.session.user == "Guest":
		return my_courses

	courses = get_my_latest_courses()

	if not len(courses):
		courses = get_featured_home_courses()

	if not len(courses):
		courses = get_popular_courses()

	for course in courses:
		my_courses.append(get_course_details(course))

	return my_courses


def get_my_latest_courses():
	return frappe.get_all(
		"LMS Enrollment",
		{
			"member": frappe.session.user,
		},
		order_by="modified desc",
		limit=3,
		pluck="course",
	)


def get_featured_home_courses():
	return frappe.get_all(
		"LMS Course",
		{"published": 1, "featured": 1},
		order_by="published_on desc",
		limit=3,
		pluck="name",
	)


def get_popular_courses():
	return frappe.get_all(
		"LMS Course",
		{
			"published": 1,
		},
		order_by="enrollments desc",
		limit=3,
		pluck="name",
	)


@frappe.whitelist()
def get_my_batches():
	my_batches = []
	if frappe.session.user == "Guest":
		return my_batches

	batches = get_my_latest_batches()

	if not len(batches):
		batches = get_upcoming_batches()

	for batch in batches:
		batch_details = get_batch_details(batch)
		if batch_details:
			my_batches.append(batch_details)

	return my_batches


def get_my_latest_batches():
	return frappe.get_all(
		"LMS Batch Enrollment",
		{
			"member": frappe.session.user,
		},
		order_by="creation desc",
		limit=4,
		pluck="batch",
	)


def get_upcoming_batches():
	return frappe.get_all(
		"LMS Batch",
		{
			"published": 1,
			"start_date": [">=", getdate()],
		},
		order_by="start_date asc",
		limit=4,
		pluck="name",
	)


# ============================================================================
# ZOOM WEBHOOK HANDLER
# ============================================================================

@frappe.whitelist(allow_guest=True, methods=["POST", "GET"])
def zoom_webhook():
	"""
	Handle Zoom webhook events for recording notifications.
	Can be called directly by Zoom or via n8n proxy.

	Supported events:
	- recording.completed: When a cloud recording is ready
	- recording.transcript_completed: When transcript is ready
	- endpoint.url_validation: Zoom URL validation challenge

	Webhook URL: /api/method/lms.lms.api.zoom_webhook
	"""
	import hashlib
	import hmac

	# Bypass CSRF for webhook endpoints
	frappe.flags.ignore_csrf = True

	try:
		# Get request data
		if frappe.request.data:
			payload = json.loads(frappe.request.data)
		else:
			frappe.logger().error("[Zoom Webhook] No request data received")
			return {"status": "error", "message": "No data received"}

		# Handle n8n wrapped payload - n8n might send {body: {...actual zoom payload...}}
		if "body" in payload and "event" not in payload:
			frappe.logger().info("[Zoom Webhook] Detected n8n wrapped payload, extracting body")
			payload = payload.get("body", payload)

		event_type = payload.get("event", "")

		frappe.logger().info(f"[Zoom Webhook] Received event: {event_type}")
		frappe.logger().info(f"[Zoom Webhook] Payload: {json.dumps(payload, indent=2)}")

		# Handle Zoom URL validation challenge (required for webhook setup)
		if event_type == "endpoint.url_validation":
			return _handle_zoom_url_validation(payload)

		# Get webhook signature from headers for verification (only if direct from Zoom)
		signature = frappe.request.headers.get("x-zm-signature", "")
		timestamp = frappe.request.headers.get("x-zm-request-timestamp", "")

		# Verify webhook signature if secret is configured (skip if from n8n)
		if signature and timestamp:
			is_valid = _verify_zoom_webhook_signature(
				frappe.request.data.decode("utf-8"),
				signature,
				timestamp
			)
			if not is_valid:
				frappe.logger().warning("[Zoom Webhook] Invalid signature - request may not be from Zoom")
				# Continue processing anyway for now, but log the warning

		# Handle recording events
		if event_type in ["recording.completed", "recording.transcript_completed"]:
			return _handle_recording_event(payload)

		# Handle other events (just acknowledge)
		frappe.logger().info(f"[Zoom Webhook] Unhandled event type: {event_type}")
		return {"status": "success", "message": f"Event {event_type} acknowledged"}

	except Exception as e:
		frappe.logger().error(f"[Zoom Webhook] Error processing webhook: {str(e)}")
		frappe.log_error(title="Zoom Webhook Error", message=frappe.get_traceback())
		return {"status": "error", "message": str(e)}


@frappe.whitelist(allow_guest=True, methods=["POST", "GET"])
def zoom_webhook_n8n():
	"""
	Dedicated endpoint for n8n to forward Zoom webhooks.
	This endpoint is simpler and doesn't require signature verification.

	n8n should forward the complete Zoom payload to this endpoint.

	Webhook URL: /api/method/lms.lms.api.zoom_webhook_n8n
	"""
	# Bypass CSRF for webhook endpoints
	frappe.flags.ignore_csrf = True
	try:
		# Get request data
		payload = None

		if frappe.request.data:
			payload = json.loads(frappe.request.data)

		# Also check form data (in case n8n sends differently)
		if not payload and frappe.form_dict:
			payload = dict(frappe.form_dict)

		if not payload:
			frappe.logger().error("[Zoom Webhook n8n] No request data received")
			return {"status": "error", "message": "No data received"}

		frappe.logger().info(f"[Zoom Webhook n8n] Received payload keys: {list(payload.keys())}")

		# Handle various n8n payload formats
		# n8n might wrap in: {body: {...}}, {data: {...}}, or send directly
		actual_payload = payload
		if "body" in payload and isinstance(payload.get("body"), dict):
			actual_payload = payload["body"]
			frappe.logger().info("[Zoom Webhook n8n] Extracted from 'body' wrapper")
		elif "data" in payload and isinstance(payload.get("data"), dict):
			actual_payload = payload["data"]
			frappe.logger().info("[Zoom Webhook n8n] Extracted from 'data' wrapper")

		event_type = actual_payload.get("event", "")

		frappe.logger().info(f"[Zoom Webhook n8n] Event type: {event_type}")
		frappe.logger().info(f"[Zoom Webhook n8n] Payload: {json.dumps(actual_payload, indent=2)}")

		# Handle URL validation
		if event_type == "endpoint.url_validation":
			return _handle_zoom_url_validation(actual_payload)

		# Handle recording events
		if event_type in ["recording.completed", "recording.transcript_completed"]:
			result = _handle_recording_event(actual_payload)
			frappe.logger().info(f"[Zoom Webhook n8n] Recording event result: {result}")
			return result

		# Handle other events
		frappe.logger().info(f"[Zoom Webhook n8n] Unhandled event type: {event_type}")
		return {"status": "success", "message": f"Event {event_type} acknowledged"}

	except json.JSONDecodeError as e:
		frappe.logger().error(f"[Zoom Webhook n8n] JSON decode error: {str(e)}")
		frappe.logger().error(f"[Zoom Webhook n8n] Raw data: {frappe.request.data}")
		return {"status": "error", "message": f"Invalid JSON: {str(e)}"}
	except Exception as e:
		frappe.logger().error(f"[Zoom Webhook n8n] Error: {str(e)}")
		frappe.log_error(title="Zoom Webhook n8n Error", message=frappe.get_traceback())
		return {"status": "error", "message": str(e)}


def _handle_zoom_url_validation(payload):
	"""
	Handle Zoom URL validation challenge.
	Required when setting up webhook endpoint in Zoom App.

	Zoom sends: {"event": "endpoint.url_validation", "payload": {"plainToken": "xxx"}}
	We respond: {"plainToken": "xxx", "encryptedToken": hmac_sha256(plainToken, secret)}
	"""
	import hashlib
	import hmac

	plain_token = payload.get("payload", {}).get("plainToken", "")

	if not plain_token:
		frappe.logger().error("[Zoom Webhook] No plainToken in validation request")
		return {"status": "error", "message": "No plainToken provided"}

	# Get any webhook secret from configured Zoom accounts
	zoom_accounts = frappe.get_all(
		"LMS Zoom Settings",
		filters={"enabled": 1, "webhook_secret": ["is", "set"]},
		fields=["name", "webhook_secret"]
	)

	if not zoom_accounts:
		frappe.logger().warning("[Zoom Webhook] No webhook secret configured - returning plain token only")
		# Return plain token without encryption (will work but not verified)
		return {
			"plainToken": plain_token,
			"encryptedToken": ""
		}

	# Use first configured secret
	secret = frappe.get_doc("LMS Zoom Settings", zoom_accounts[0].name).get_password("webhook_secret")

	if not secret:
		frappe.logger().warning("[Zoom Webhook] Webhook secret is empty")
		return {
			"plainToken": plain_token,
			"encryptedToken": ""
		}

	# Generate HMAC SHA256 hash
	encrypted_token = hmac.new(
		secret.encode("utf-8"),
		plain_token.encode("utf-8"),
		hashlib.sha256
	).hexdigest()

	frappe.logger().info(f"[Zoom Webhook] URL validation successful")

	return {
		"plainToken": plain_token,
		"encryptedToken": encrypted_token
	}


def _verify_zoom_webhook_signature(payload_body, signature, timestamp):
	"""
	Verify Zoom webhook signature using HMAC SHA256.

	Signature format: v0=hash
	Message format: v0:{timestamp}:{payload_body}
	"""
	import hashlib
	import hmac

	# Get webhook secrets from all enabled Zoom accounts
	zoom_accounts = frappe.get_all(
		"LMS Zoom Settings",
		filters={"enabled": 1, "webhook_secret": ["is", "set"]},
		fields=["name"]
	)

	if not zoom_accounts:
		frappe.logger().warning("[Zoom Webhook] No webhook secret configured for signature verification")
		return True  # Allow if no secret configured

	# Try each configured secret
	for account in zoom_accounts:
		try:
			secret = frappe.get_doc("LMS Zoom Settings", account.name).get_password("webhook_secret")
			if not secret:
				continue

			# Create message to sign
			message = f"v0:{timestamp}:{payload_body}"

			# Generate expected signature
			expected_signature = "v0=" + hmac.new(
				secret.encode("utf-8"),
				message.encode("utf-8"),
				hashlib.sha256
			).hexdigest()

			# Compare signatures
			if hmac.compare_digest(expected_signature, signature):
				frappe.logger().info(f"[Zoom Webhook] Signature verified with account {account.name}")
				return True
		except Exception as e:
			frappe.logger().error(f"[Zoom Webhook] Error verifying signature with {account.name}: {e}")
			continue

	return False


def _handle_recording_event(payload):
	"""
	Handle recording.completed and recording.transcript_completed events.

	Updates the LMS Live Class with recording information.
	"""
	try:
		event_type = payload.get("event", "")
		event_data = payload.get("payload", {}).get("object", {})

		meeting_id = event_data.get("id")  # Numeric meeting ID
		meeting_uuid = event_data.get("uuid")  # Meeting UUID
		topic = event_data.get("topic", "")
		share_url = event_data.get("share_url", "")
		password = event_data.get("password", "")
		recording_files = event_data.get("recording_files", [])

		frappe.logger().info(f"[Zoom Webhook] Processing {event_type} for meeting {meeting_id} (UUID: {meeting_uuid})")
		frappe.logger().info(f"[Zoom Webhook] Topic: {topic}, Share URL: {share_url}")
		frappe.logger().info(f"[Zoom Webhook] Recording files: {len(recording_files)}")

		# Find matching LMS Live Class
		live_class = _find_live_class_by_meeting(meeting_id, meeting_uuid, topic)

		if not live_class:
			frappe.logger().warning(f"[Zoom Webhook] No matching LMS Live Class found for meeting {meeting_id}")
			return {"status": "success", "message": "No matching live class found"}

		frappe.logger().info(f"[Zoom Webhook] Found matching live class: {live_class.name}")

		# Check if recording already available
		if live_class.recording_available:
			frappe.logger().info(f"[Zoom Webhook] Recording already available for {live_class.name}")
			return {"status": "success", "message": "Recording already processed"}

		# Find the best recording URL
		recording_url = _extract_best_recording_url(recording_files, share_url)

		if not recording_url:
			frappe.logger().warning(f"[Zoom Webhook] No suitable recording URL found")
			return {"status": "success", "message": "No recording URL in payload"}

		# Embed password into URL if available to prevent Zoom from asking for passcode
		if password and "pwd=" not in recording_url and "access_token=" not in recording_url:
			try:
				from urllib.parse import quote
				# Add password to URL
				separator = "&" if "?" in recording_url else "?"
				recording_url_with_pwd = f"{recording_url}{separator}pwd={quote(password, safe='')}"
				frappe.logger().info(f"[Zoom Webhook] Embedded password into recording URL")
				recording_url = recording_url_with_pwd
			except Exception as e:
				frappe.logger().error(f"[Zoom Webhook] Error embedding password: {str(e)}")
				# Continue with original URL if embedding fails

		# Update live class with recording info
		live_class.recording_url = recording_url
		live_class.recording_password = password
		live_class.recording_available = 1

		# Also update UUID if not set
		if not live_class.uuid and meeting_uuid:
			live_class.uuid = meeting_uuid

		live_class.save(ignore_permissions=True)
		frappe.db.commit()

		frappe.logger().info(f"[Zoom Webhook] Successfully updated recording for {live_class.name}")

		# Create lesson from recording
		try:
			create_lesson_from_recording(live_class.name)
			frappe.logger().info(f"[Zoom Webhook] Created lesson from recording for {live_class.name}")
		except Exception as e:
			frappe.logger().error(f"[Zoom Webhook] Error creating lesson: {str(e)}")

		return {
			"status": "success",
			"message": f"Recording updated for {live_class.name}",
			"live_class": live_class.name
		}

	except Exception as e:
		frappe.logger().error(f"[Zoom Webhook] Error handling recording event: {str(e)}")
		frappe.log_error(title="Zoom Webhook Recording Error", message=frappe.get_traceback())
		return {"status": "error", "message": str(e)}


def _find_live_class_by_meeting(meeting_id, meeting_uuid, topic):
	"""
	Find LMS Live Class matching the Zoom meeting.

	Tries multiple matching strategies:
	1. By meeting_id (numeric ID)
	2. By UUID (if meeting_id not found)
	3. By title/topic (fuzzy match as fallback)
	"""
	# Strategy 1: Match by meeting_id
	if meeting_id:
		live_class = frappe.db.get_value(
			"LMS Live Class",
			{"meeting_id": str(meeting_id)},
			"name"
		)
		if live_class:
			return frappe.get_doc("LMS Live Class", live_class)

	# Strategy 2: Match by UUID
	if meeting_uuid:
		live_class = frappe.db.get_value(
			"LMS Live Class",
			{"uuid": meeting_uuid},
			"name"
		)
		if live_class:
			return frappe.get_doc("LMS Live Class", live_class)

	# Strategy 3: Match by title (exact match)
	if topic:
		live_class = frappe.db.get_value(
			"LMS Live Class",
			{"title": topic},
			"name"
		)
		if live_class:
			return frappe.get_doc("LMS Live Class", live_class)

	# Strategy 4: Match by title (fuzzy - topic contains title or vice versa)
	if topic:
		# Get recent live classes without recordings
		recent_classes = frappe.get_all(
			"LMS Live Class",
			filters={
				"recording_available": 0,
				"auto_recording": ["!=", "No Recording"],
				"date": [">=", frappe.utils.add_days(frappe.utils.nowdate(), -7)]  # Last 7 days
			},
			fields=["name", "title", "meeting_id", "uuid"]
		)

		for lc in recent_classes:
			if lc.title and (lc.title in topic or topic in lc.title):
				frappe.logger().info(f"[Zoom Webhook] Fuzzy matched '{topic}' to '{lc.title}'")
				return frappe.get_doc("LMS Live Class", lc.name)

	return None


def _extract_best_recording_url(recording_files, share_url):
	"""
	Extract the best recording URL from Zoom recording files.

	Priority:
	1. MP4 video file with play_url
	2. shared_screen_with_speaker_view type
	3. Any video file (not transcript/audio only)
	4. Share URL as fallback
	"""
	if not recording_files and share_url:
		return share_url

	# Filter for completed recordings
	completed_files = [
		f for f in recording_files
		if f.get("status") == "completed"
	]

	if not completed_files:
		completed_files = recording_files

	# Priority 1: MP4 files
	for file in completed_files:
		if file.get("file_type") == "MP4":
			url = file.get("play_url") or file.get("share_url") or file.get("download_url")
			if url:
				frappe.logger().info(f"[Zoom Webhook] Selected MP4 recording: {file.get('recording_type')}")
				return url

	# Priority 2: shared_screen_with_speaker_view
	for file in completed_files:
		if file.get("recording_type") == "shared_screen_with_speaker_view":
			url = file.get("play_url") or file.get("share_url") or file.get("download_url")
			if url:
				frappe.logger().info("[Zoom Webhook] Selected shared_screen_with_speaker_view recording")
				return url

	# Priority 3: Any video recording (not transcript/audio)
	video_types = ["MP4", "M4A"]
	non_video_types = ["TRANSCRIPT", "VTT", "TXT", "CHAT"]

	for file in completed_files:
		file_type = file.get("file_type", "").upper()
		if file_type not in non_video_types:
			url = file.get("play_url") or file.get("share_url") or file.get("download_url")
			if url:
				frappe.logger().info(f"[Zoom Webhook] Selected {file_type} recording")
				return url

	# Priority 4: Share URL fallback
	if share_url:
		frappe.logger().info("[Zoom Webhook] Using share_url as fallback")
		return share_url

	return None


@frappe.whitelist(allow_guest=True, methods=["GET"])
def zoom_webhook_status():
	"""
	Health check endpoint for Zoom webhook.
	Can be used to verify the webhook is accessible.
	"""
	return {
		"status": "ok",
		"message": "Zoom webhook endpoint is active",
		"timestamp": frappe.utils.now()
	}


# ============================================================================
# ZOOM RECORDING DIAGNOSTICS
# ============================================================================

@frappe.whitelist()
def zoom_recording_diagnostics():
	"""
	Comprehensive diagnostics for Zoom recording integration.
	Returns status of all components and recent activity.
	"""
	if not frappe.has_permission("LMS Live Class", "read"):
		frappe.throw(_("Permission denied"))

	diagnostics = {
		"timestamp": frappe.utils.now(),
		"zoom_accounts": _get_zoom_accounts_status(),
		"webhook_config": _get_webhook_config_status(),
		"pending_recordings": _get_pending_recordings(),
		"recent_recordings": _get_recent_recordings(),
		"recent_errors": _get_recent_errors(),
		"cron_job_status": _get_cron_job_status(),
	}

	return diagnostics


def _get_zoom_accounts_status():
	"""Get status of all configured Zoom accounts"""
	accounts = frappe.get_all(
		"LMS Zoom Settings",
		fields=["name", "account_name", "enabled", "member", "webhook_url"],
	)

	result = []
	for acc in accounts:
		# Check if credentials are set (without exposing them)
		doc = frappe.get_doc("LMS Zoom Settings", acc.name)
		has_account_id = bool(doc.account_id)
		has_client_id = bool(doc.client_id)
		has_client_secret = bool(doc.get_password("client_secret", raise_exception=False))
		has_webhook_secret = bool(doc.get_password("webhook_secret", raise_exception=False))

		# Test authentication
		auth_status = "Not tested"
		if acc.enabled and has_account_id and has_client_id and has_client_secret:
			try:
				from lms.lms.doctype.lms_batch.lms_batch import authenticate
				token = authenticate(acc.name)
				auth_status = "OK" if token else "Failed"
			except Exception as e:
				auth_status = f"Error: {str(e)[:50]}"

		result.append({
			"name": acc.name,
			"account_name": acc.account_name,
			"enabled": acc.enabled,
			"member": acc.member,
			"webhook_url": acc.webhook_url,
			"has_account_id": has_account_id,
			"has_client_id": has_client_id,
			"has_client_secret": has_client_secret,
			"has_webhook_secret": has_webhook_secret,
			"auth_status": auth_status,
		})

	return result


def _get_webhook_config_status():
	"""Get webhook configuration status"""
	base_url = frappe.utils.get_url()
	webhook_urls = [
		f"{base_url}/webhook/zoom",
		f"{base_url}/api/method/lms.lms.api.zoom_webhook",
	]

	# Check if any account has webhook secret configured
	accounts_with_secret = frappe.get_all(
		"LMS Zoom Settings",
		filters={"enabled": 1, "webhook_secret": ["is", "set"]},
		fields=["name"]
	)

	return {
		"webhook_urls": webhook_urls,
		"accounts_with_webhook_secret": len(accounts_with_secret),
		"signature_verification_enabled": len(accounts_with_secret) > 0,
	}


def _get_pending_recordings():
	"""Get live classes waiting for recordings"""
	from datetime import datetime, timedelta

	cutoff_time = datetime.now() - timedelta(minutes=90)
	ten_minutes_ago = datetime.now() - timedelta(minutes=10)

	pending = frappe.get_all(
		"LMS Live Class",
		filters={
			"auto_recording": ["!=", "No Recording"],
			"recording_available": 0,
		},
		fields=["name", "title", "date", "time", "duration", "meeting_id", "uuid", "auto_recording", "batch_name"],
		order_by="date desc, time desc",
		limit=20
	)

	result = []
	for lc in pending:
		try:
			class_start = datetime.combine(
				getdate(lc.date),
				datetime.strptime(str(lc.time), "%H:%M:%S").time() if isinstance(lc.time, str) else lc.time
			)
			class_end = class_start + timedelta(minutes=cint(lc.duration or 60))
			time_since_end = datetime.now() - class_end

			status = "Scheduled"
			if datetime.now() < class_start:
				status = "Not started"
			elif datetime.now() < class_end:
				status = "In progress"
			elif time_since_end.total_seconds() < 600:  # Less than 10 min
				status = "Just ended - waiting"
			elif time_since_end.total_seconds() < 5400:  # Less than 90 min
				status = "Ready for fetch"
			else:
				status = "Past fetch window"

			result.append({
				"name": lc.name,
				"title": lc.title,
				"date": str(lc.date),
				"time": str(lc.time),
				"batch": lc.batch_name,
				"meeting_id": lc.meeting_id,
				"has_uuid": bool(lc.uuid),
				"auto_recording": lc.auto_recording,
				"status": status,
				"minutes_since_end": round(time_since_end.total_seconds() / 60, 1) if datetime.now() > class_end else None,
			})
		except Exception as e:
			result.append({
				"name": lc.name,
				"title": lc.title,
				"error": str(e),
			})

	return result


def _get_recent_recordings():
	"""Get recently fetched recordings"""
	recent = frappe.get_all(
		"LMS Live Class",
		filters={
			"recording_available": 1,
		},
		fields=["name", "title", "date", "time", "batch_name", "recording_url", "modified"],
		order_by="modified desc",
		limit=10
	)

	result = []
	for lc in recent:
		# Check if lesson was created
		lesson_exists = frappe.db.exists(
			"Course Lesson",
			{"content": f"live_class:{lc.name}"}
		)

		result.append({
			"name": lc.name,
			"title": lc.title,
			"date": str(lc.date),
			"batch": lc.batch_name,
			"has_recording_url": bool(lc.recording_url),
			"recording_url_preview": lc.recording_url[:80] + "..." if lc.recording_url and len(lc.recording_url) > 80 else lc.recording_url,
			"lesson_created": bool(lesson_exists),
			"modified": str(lc.modified),
		})

	return result


def _get_recent_errors():
	"""Get recent Zoom-related errors from error log"""
	errors = frappe.get_all(
		"Error Log",
		filters={
			"creation": [">=", frappe.utils.add_days(frappe.utils.nowdate(), -7)],
			"error": ["like", "%Zoom%"]
		},
		fields=["name", "method", "error", "creation"],
		order_by="creation desc",
		limit=10
	)

	result = []
	for err in errors:
		result.append({
			"name": err.name,
			"method": err.method,
			"error_preview": err.error[:200] + "..." if len(err.error) > 200 else err.error,
			"creation": str(err.creation),
		})

	return result


def _get_cron_job_status():
	"""Get status of the recording fetch cron job"""
	# Check if there's a scheduled job log
	last_run = frappe.get_all(
		"Scheduled Job Log",
		filters={
			"scheduled_job_type": ["like", "%fetch_pending_recordings%"]
		},
		fields=["status", "creation", "details"],
		order_by="creation desc",
		limit=5
	)

	return {
		"job_name": "lms.lms.doctype.lms_live_class.lms_live_class.fetch_pending_recordings",
		"schedule": "Every 10 minutes",
		"recent_runs": [
			{
				"status": run.status,
				"creation": str(run.creation),
				"details": run.details[:100] if run.details else None,
			}
			for run in last_run
		]
	}


@frappe.whitelist()
def test_zoom_recording_fetch(live_class_name):
	"""
	Manually trigger recording fetch for a specific live class.
	Useful for testing and debugging.
	"""
	if not frappe.has_permission("LMS Live Class", "write"):
		frappe.throw(_("Permission denied"))

	live_class = frappe.get_doc("LMS Live Class", live_class_name)

	if not live_class.meeting_id:
		return {
			"status": "error",
			"message": "No meeting_id set for this live class"
		}

	if live_class.recording_available:
		return {
			"status": "info",
			"message": "Recording already available",
			"recording_url": live_class.recording_url
		}

	# Import and call fetch_recording
	from lms.lms.doctype.lms_live_class.lms_live_class import fetch_recording

	result = fetch_recording(live_class_name)

	return {
		"status": "success",
		"message": "Recording fetch attempted",
		"result": result
	}


@frappe.whitelist()
def simulate_zoom_webhook(live_class_name):
	"""
	Simulate a Zoom webhook for testing purposes.
	Creates a mock payload based on the live class data.
	"""
	if not frappe.has_permission("LMS Live Class", "write"):
		frappe.throw(_("Permission denied"))

	live_class = frappe.get_doc("LMS Live Class", live_class_name)

	# Create mock webhook payload similar to what Zoom sends
	mock_payload = {
		"event": "recording.completed",
		"payload": {
			"account_id": "test_account",
			"object": {
				"uuid": live_class.uuid or f"test-uuid-{live_class.name}",
				"id": int(live_class.meeting_id) if live_class.meeting_id else 12345678,
				"topic": live_class.title,
				"share_url": f"https://zoom.us/rec/share/test-{live_class.name}",
				"password": "TestPass123",
				"recording_files": [
					{
						"id": "test-recording-id",
						"file_type": "MP4",
						"recording_type": "shared_screen_with_speaker_view",
						"status": "completed",
						"play_url": f"https://zoom.us/rec/play/test-{live_class.name}",
						"download_url": f"https://zoom.us/rec/download/test-{live_class.name}",
					}
				]
			}
		},
		"event_ts": int(frappe.utils.now_datetime().timestamp() * 1000)
	}

	# Process the mock payload
	result = _handle_recording_event(mock_payload)

	return {
		"status": "success",
		"message": "Simulated webhook processed",
		"mock_payload": mock_payload,
		"result": result
	}


@frappe.whitelist()
def get_zoom_recording_logs(live_class_name=None, limit=50):
	"""
	Get recent logs related to Zoom recordings.
	Searches scheduler logs for recording-related entries.
	"""
	if not frappe.has_permission("LMS Live Class", "read"):
		frappe.throw(_("Permission denied"))

	# Get from Error Log
	filters = {
		"creation": [">=", frappe.utils.add_days(frappe.utils.nowdate(), -7)],
	}

	if live_class_name:
		filters["error"] = ["like", f"%{live_class_name}%"]
	else:
		filters["error"] = ["like", "%Recording%"]

	logs = frappe.get_all(
		"Error Log",
		filters=filters,
		fields=["name", "method", "error", "creation"],
		order_by="creation desc",
		limit=limit
	)

	return {
		"logs": [
			{
				"name": log.name,
				"method": log.method,
				"message": log.error[:500] if log.error else "",
				"creation": str(log.creation),
			}
			for log in logs
		]
	}
