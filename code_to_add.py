# ==========================================
# n8n-based Vimeo Integration API
# ==========================================
# Add this code to the END of lms/lms/api.py file on production server

def _validate_vimeo_n8n_payload(payload):
	"""
	Validate incoming payload from n8n for Vimeo recordings.

	Args:
		payload (dict): JSON payload from n8n

	Returns:
		list: List of validation error messages (empty if valid)
	"""
	errors = []

	# Required: video_url
	video_url = payload.get("video_url")
	if not video_url:
		errors.append("video_url is required")
	elif not isinstance(video_url, str) or "vimeo.com" not in video_url.lower():
		errors.append("video_url must be a valid Vimeo URL")

	# Required: video_id
	video_id = payload.get("video_id")
	if not video_id:
		errors.append("video_id is required")
	elif not str(video_id).isdigit():
		errors.append("video_id must be numeric")

	# Optional: created_time (validate if provided)
	created_time = payload.get("created_time")
	if created_time:
		try:
			if isinstance(created_time, (int, float)):
				# Unix timestamp - validate range (must be reasonable)
				from datetime import datetime
				datetime.fromtimestamp(created_time)
			else:
				# ISO format string
				get_datetime(created_time)
		except Exception as e:
			errors.append(f"created_time is invalid: {str(e)}")

	# Optional: meeting_id (validate if provided)
	meeting_id = payload.get("meeting_id")
	if meeting_id:
		meeting_id_str = str(meeting_id)
		if not (meeting_id_str.isdigit() and 10 <= len(meeting_id_str) <= 12):
			errors.append("meeting_id must be a 10-12 digit numeric string")

	return errors


@frappe.whitelist(allow_guest=True, methods=["POST"])
def process_vimeo_recording():
	"""
	Simplified API endpoint for n8n-processed Vimeo recordings.

	Architecture:
		Vimeo → n8n webhook → n8n transforms → LMS API (this endpoint)

	n8n handles:
		- Vimeo webhook signature verification
		- Vimeo API enrichment for metadata
		- Title cleaning (removes Vimeo timestamp suffix)
		- Meeting ID extraction from description

	LMS handles:
		- Request validation
		- Live Class matching (4-level cascade)
		- Recording URL update
		- Lesson creation

	Expected payload from n8n:
		{
			"video_url": "https://player.vimeo.com/video/123",
			"video_id": "123",
			"created_time": "2026-01-11T15:46:00Z" or 1736609160,
			"meeting_id": "12345678901",  // optional
			"title": "Live Class on Python",  // optional, already cleaned
			"description": "Meeting info...",  // optional
			"duration": 3600  // optional, seconds
		}

	Returns:
		Success response (200):
			{
				"status": "success",
				"message": "Recording updated for LMS-LC-00123",
				"live_class": "LMS-LC-00123",
				"lesson_created": true,
				"matched_by": "meeting_id"
			}

		No match response (200):
			{
				"status": "success",
				"message": "No matching live class found",
				"matched": false
			}

		Error response (400/500):
			{
				"status": "error",
				"message": "Missing required field: video_url",
				"code": "VALIDATION_ERROR"
			}
	"""
	try:
		# Disable CSRF for external n8n calls
		frappe.flags.ignore_csrf = True

		# Parse request body
		if frappe.request.data:
			request_data = frappe.request.data
			if isinstance(request_data, bytes):
				request_data = request_data.decode('utf-8')
			payload = json.loads(request_data)
		else:
			frappe.logger().error("[n8n Vimeo] No data received in request")
			return {
				"status": "error",
				"message": "No data received",
				"code": "NO_DATA"
			}

		frappe.logger().info(f"[n8n Vimeo] Received payload: {json.dumps(payload, indent=2)}")

		# Validate payload
		validation_errors = _validate_vimeo_n8n_payload(payload)
		if validation_errors:
			error_msg = "; ".join(validation_errors)
			frappe.logger().error(f"[n8n Vimeo] Validation failed: {error_msg}")
			return {
				"status": "error",
				"message": error_msg,
				"code": "VALIDATION_ERROR"
			}

		# Extract and normalize data
		video_url = payload.get("video_url")
		video_id = str(payload.get("video_id"))
		title = payload.get("title", "")
		description = payload.get("description", "")
		duration = payload.get("duration", 0)

		# Parse created_time (handle both ISO and Unix formats)
		created_time = payload.get("created_time")
		if created_time:
			if isinstance(created_time, (int, float)):
				# Unix timestamp
				from datetime import datetime
				created_time = datetime.fromtimestamp(created_time)
				frappe.logger().info(f"[n8n Vimeo] Converted Unix timestamp to: {created_time}")
			else:
				# ISO format
				created_time = get_datetime(created_time)
				frappe.logger().info(f"[n8n Vimeo] Parsed ISO timestamp: {created_time}")
		else:
			frappe.logger().warning("[n8n Vimeo] No created_time provided, matching may be less accurate")

		# Log incoming video info
		frappe.logger().info(f"[n8n Vimeo] Processing video: ID={video_id}, URL={video_url}, Title='{title}'")

		# Find matching Live Class using existing 4-level cascade
		live_class, match_method = _find_live_class_for_vimeo_video(
			video_title=title,
			video_description=description,
			created_time=created_time
		)

		if not live_class:
			frappe.logger().info("[n8n Vimeo] No matching Live Class found")
			return {
				"status": "success",
				"message": "No matching live class found (might not be an LMS recording)",
				"matched": False
			}

		frappe.logger().info(f"[n8n Vimeo] Matched Live Class: {live_class.name} using {match_method}")

		# Update Live Class with recording URL
		live_class.recording_url = video_url
		live_class.recording_available = 1
		live_class.save(ignore_permissions=True)
		frappe.logger().info(f"[n8n Vimeo] Updated recording URL for {live_class.name}")

		# Create lesson from recording
		lesson_created = False
		try:
			create_lesson_from_recording(live_class.name)
			lesson_created = True
			frappe.logger().info(f"[n8n Vimeo] Created/updated lesson for {live_class.name}")
		except Exception as e:
			frappe.logger().warning(f"[n8n Vimeo] Could not create lesson: {str(e)}")

		# Commit changes
		frappe.db.commit()

		return {
			"status": "success",
			"message": f"Recording updated with Vimeo URL for {live_class.name}",
			"live_class": live_class.name,
			"video_url": video_url,
			"lesson_created": lesson_created,
			"matched_by": match_method
		}

	except json.JSONDecodeError as e:
		frappe.logger().error(f"[n8n Vimeo] JSON decode error: {str(e)}")
		return {
			"status": "error",
			"message": "Invalid JSON in request body",
			"code": "JSON_ERROR"
		}
	except Exception as e:
		frappe.logger().error(f"[n8n Vimeo] Unexpected error: {str(e)}")
		frappe.log_error(title="n8n Vimeo Recording Error", message=frappe.get_traceback())
		return {
			"status": "error",
			"message": "Error processing recording",
			"code": "PROCESSING_ERROR"
		}
