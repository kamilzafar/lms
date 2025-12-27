# Zoom Auto-Recording Upload - Setup Guide

## Overview

The Zoom Auto-Recording Upload feature automatically downloads cloud recordings from Zoom meetings and uploads them directly to the associated course lesson in the LMS. This eliminates manual recording downloads and uploads, saving significant time for instructors.

---

## How It Works

### Automated Workflow

```
1. Instructor ends Zoom meeting with cloud recording enabled
   ↓
2. Zoom processes the recording (5-60 minutes)
   ↓
3. Zoom sends "recording.completed" webhook to LMS
   ↓
4. LMS verifies webhook signature for security
   ↓
5. System downloads MP4 file from Zoom
   ↓
6. File is uploaded to Frappe File system
   ↓
7. Video block automatically added to lesson content (EditorJS)
   ↓
8. Recording marked as processed in Live Class record
```

### Technical Components

**Backend Files:**
- **Webhook Handler**: `/lms/lms/api.py`
  - `zoom_webhook()` - Receives Zoom webhook events
  - `verify_zoom_signature()` - Validates webhook authenticity

- **Recording Processor**: `/lms/lms/doctype/lms_live_class/lms_live_class.py`
  - `process_zoom_recording()` - Downloads and uploads recording

**Database Fields:**
- `LMS Zoom Settings`:
  - `webhook_secret_token` - Security token for webhook validation

- `LMS Live Class`:
  - `recording_processed` - Flag (0 or 1)
  - `recording_file` - Link to File doctype
  - `recording_url` - URL of the uploaded file

---

## Setup Instructions

**IMPORTANT - Order of Operations**:
1. Configure your Zoom App and get credentials (Step 1)
2. **Configure the Webhook Secret Token in LMS FIRST** (Step 2)
3. Then validate the webhook endpoint in Zoom (Step 1.6)

This order is critical - Zoom validation will fail if the secret token is not configured in LMS first.

---

### Step 1: Configure Zoom App

1. **Go to Zoom App Marketplace**
   - Visit: https://marketplace.zoom.us/
   - Sign in with your Zoom account

2. **Create or Edit Your Server-to-Server OAuth App**
   - Navigate to "Develop" → "Build App"
   - Select "Server-to-Server OAuth" app type
   - Note your **Client ID** and **Client Secret**

3. **Configure Webhook Subscription**
   - In your Zoom app settings, go to "Feature" tab
   - Click "Add New Event Subscription"

   **Event Subscription Details:**
   ```
   Subscription Name: LMS Recording Upload
   Event notification endpoint URL: https://yoursite.com/api/method/lms.lms.api.zoom_webhook
   ```

   Replace `yoursite.com` with your actual LMS domain.

4. **Add Event Types**
   - Under "Event types", click "Add events"
   - Select: **"All Recordings" → "Recording Completed"**
   - Save the subscription

5. **Copy Secret Token**
   - After saving, Zoom will generate a **Secret Token**
   - Copy this token (you'll need it in Step 2)

6. **Validate Endpoint** (if required)
   - Zoom may send a validation request to your endpoint
   - The LMS automatically handles this validation

### Step 2: Configure LMS Zoom Settings

**IMPORTANT**: You MUST configure the Webhook Secret Token BEFORE validating the endpoint in Step 1.

1. **Login to Frappe Desk**
   - Navigate to: `https://yoursite.com/app`

2. **Open LMS Zoom Settings**
   - Search for "LMS Zoom Settings" in the search bar
   - Open your existing Zoom Settings record (or create new)

3. **Enter Credentials**
   ```
   Account ID: [Your Zoom Account ID]
   Client ID: [From Zoom App]
   Client Secret: [From Zoom App]
   Webhook Secret Token: [Secret Token from Step 1.5]
   ```

4. **Save the Document**

**Note**: The webhook endpoint will fail validation if the Webhook Secret Token is not configured first. Make sure to save this field before attempting to validate the endpoint in the Zoom App.

### Step 3: Ensure Background Worker is Running

The recording processing happens in background jobs.

**For Development:**
```bash
bench worker
```

**For Production (Docker):**
- Worker container should be running automatically
- Verify with: `docker ps | grep worker`

**For Production (Bench):**
```bash
# Using Supervisor
sudo supervisorctl status all

# Should see workers running
```

### Step 4: Test the Setup

1. **Create a Live Class**
   - Go to your LMS → Create a batch
   - Schedule a live class (Zoom meeting will be auto-created)

2. **Start and Record the Meeting**
   - Click "Start" to launch Zoom meeting
   - **Important**: Enable "Record to Cloud" during the meeting
   - Conduct your class (even 1-2 minutes is fine for testing)
   - End the meeting

3. **Wait for Processing**
   - Zoom takes 5-60 minutes to process recordings
   - Monitor the background job queue:
   ```bash
   bench --site yoursite.com console
   ```
   ```python
   frappe.get_all("RQ Job", filters={"status": "queued"}, fields=["name", "job_name"])
   ```

4. **Verify Auto-Upload**
   - Open the associated Course Lesson
   - Check if video block appears at the top of the content
   - Open the Live Class record → `recording_processed` should be `1`

---

## Configuration Checklist

- [ ] Zoom Server-to-Server OAuth app created
- [ ] Webhook endpoint configured in Zoom app
- [ ] "Recording Completed" event subscribed
- [ ] Webhook Secret Token copied
- [ ] LMS Zoom Settings updated with all credentials
- [ ] `webhook_secret_token` field populated in LMS
- [ ] Background worker running (`bench worker` or supervisor)
- [ ] Test recording uploaded successfully

---

## Troubleshooting

### Endpoint Validation Failing ("Please validate your endpoint URL")

This error occurs when Zoom cannot verify your webhook endpoint.

**Common Causes & Solutions**:

1. **Webhook Secret Token Not Configured**
   - Error logged: "No webhook_secret_token configured"
   - **Solution**: Configure the Webhook Secret Token in LMS Zoom Settings BEFORE validating in Zoom App
   ```bash
   # Check if token is configured
   bench --site yoursite.com console
   ```
   ```python
   frappe.get_all("LMS Zoom Settings", fields=["webhook_secret_token"])
   # Should return a record with the token, not empty
   ```

2. **Endpoint Not Accessible**
   - Zoom cannot reach your server
   - **Solution**: Ensure your server is publicly accessible (not localhost)
   - Test with: `curl -X POST https://yoursite.com/api/method/lms.lms.api.zoom_webhook`

3. **HTTPS/SSL Issues**
   - Zoom requires valid HTTPS
   - **Solution**: Ensure your SSL certificate is valid and trusted

4. **Check Error Logs**
   ```bash
   # View webhook validation errors
   bench --site yoursite.com console
   ```
   ```python
   frappe.get_all("Error Log",
       filters={"error": ["like", "%Zoom Webhook Validation%"]},
       fields=["name", "error", "creation"],
       order_by="creation desc",
       limit=5
   )
   ```

### Recording Not Uploading

**Check 1: Verify Webhook is Reaching LMS**
```bash
# Check Frappe error logs
bench --site yoursite.com console
```
```python
# Check for webhook activity
frappe.get_all("Error Log",
    filters={"error": ["like", "%Zoom Webhook%"]},
    fields=["name", "error", "creation"],
    order_by="creation desc",
    limit=10
)
```

**Check 2: Verify Background Worker**
```bash
# Development
ps aux | grep "bench worker"

# Production (supervisor)
sudo supervisorctl status frappe-bench-workers:
```

**Check 3: Webhook Secret Token**
- Ensure `webhook_secret_token` in LMS Zoom Settings matches Zoom app EXACTLY
- Signature validation will fail if mismatched
- No extra spaces or special characters

**Check 4: Zoom API Permissions**
- Ensure your Zoom app has recording download permissions
- Check: App → Scopes → `recording:read:admin`
- Check: App → Feature → Event Subscriptions → "Recording Completed" is subscribed

### Webhook Signature Validation Failed

**Error**: "Invalid webhook signature" in Error Log

**Solution**:
1. Copy the **exact** Secret Token from Zoom app
   - Go to Zoom App → Feature → Event Subscriptions
   - Copy the "Secret Token" (not the subscription name)
2. Paste into `webhook_secret_token` field in LMS Zoom Settings
   - Remove any extra spaces before/after
   - Ensure no line breaks or special characters
3. Save LMS Zoom Settings
4. Test by creating a new recording

### Recording Downloads But Doesn't Appear in Lesson

**Check**:
1. Open LMS Live Class record
2. Verify `lesson` field is populated (linked to Course Lesson)
3. Check if `recording_file` field has a value
4. Manually open the Course Lesson → Check content

**Manual Fix** (if needed):
```python
# In bench console
lesson = frappe.get_doc("Course Lesson", "your-lesson-name")
import json
content = json.loads(lesson.content) if lesson.content else {"blocks": []}

# Add video block manually
content["blocks"].insert(0, {
    "type": "upload",
    "data": {
        "file_url": "/files/your-recording.mp4",
        "title": "Class Recording"
    }
})

lesson.content = json.dumps(content)
lesson.save(ignore_permissions=True)
frappe.db.commit()
```

### Large File Upload Timeout

**Error**: "Request timeout" or partial upload

**Solution** - Increase timeout in site config:
```bash
# Edit site_config.json
nano sites/yoursite.com/site_config.json
```
```json
{
  "max_file_size": 2147483648,
  "http_timeout": 3600
}
```
```bash
bench restart
```

### Check Background Job Status

```bash
bench --site yoursite.com console
```
```python
# Check queued jobs
frappe.get_all("RQ Job",
    filters={"job_name": "lms.lms.doctype.lms_live_class.lms_live_class.process_zoom_recording"},
    fields=["name", "status", "modified"]
)

# Check for failed jobs
frappe.get_all("RQ Job",
    filters={"status": "failed"},
    fields=["name", "exc_info"],
    limit=5
)
```

---

## Security Notes

### Webhook Security

- **Webhook Secret Token** validates that requests are from Zoom (not spoofed)
- Signature verification uses HMAC-SHA256
- All API calls to Zoom use OAuth2 authentication
- Recordings are downloaded securely via HTTPS
- Files stored in Frappe's private file system by default

### CSRF Exemption (Production-Safe)

The webhook endpoint is **CSRF-exempt** to allow Zoom to send POST requests without CSRF tokens. This is safe because:

1. **External Service**: Only Zoom calls this endpoint, not user browsers
2. **Signature Verification**: Every webhook event (except validation) is verified using HMAC-SHA256
3. **Guest Context**: The endpoint runs in guest context with no user permissions
4. **Validation Handshake**: Zoom's validation uses plainToken/encryptedToken mechanism
5. **Always HTTP 200**: Returns 200 OK for all requests (Zoom requirement), logs errors instead

**Testing the endpoint**:
```bash
# Test endpoint accessibility (should return 200, not 403)
curl -X POST https://yoursite.com/api/method/lms.lms.api.zoom_webhook \
  -H "Content-Type: application/json" \
  -d '{"event": "endpoint.url_validation", "payload": {"plainToken": "test123"}}'

# Expected response (HTTP 200):
# {"plainToken": "test123", "encryptedToken": "...hash..."}
```

If you receive **403 Forbidden**, the CSRF exemption may not be working. Check:
- Frappe version (v14+ recommended)
- Error logs for middleware blocking
- Site configuration for restrictive security settings

---

## Advanced Configuration

### Change Recording File Privacy

By default, recordings are saved as private files. To make them public:

**Edit**: `/lms/lms/doctype/lms_live_class/lms_live_class.py`

Find `process_zoom_recording()` function, modify:
```python
file_doc = save_file(
    fname=file_name,
    content=file_content,
    dt="LMS Live Class",
    dn=self.name,
    is_private=0  # Change from 1 to 0 for public
)
```

### Custom Recording Position in Lesson

By default, video is inserted at the **top** of lesson content.

To change position, edit `process_zoom_recording()`:
```python
# Insert at end instead
content["blocks"].append({  # Changed from insert(0, ...)
    "type": "upload",
    "data": {"file_url": file_url, "title": "Recording"}
})
```

### Enable Recording Notifications

Add email notification when recording is processed:

```python
# In process_zoom_recording() after successful upload
frappe.sendmail(
    recipients=[self.owner],
    subject=f"Recording Ready: {self.title}",
    message=f"Your class recording has been uploaded to the lesson."
)
```

---

## Webhook Payload Reference

**Example Zoom webhook payload** (`recording.completed`):
```json
{
  "event": "recording.completed",
  "payload": {
    "object": {
      "uuid": "meeting-uuid",
      "id": 123456789,
      "recording_files": [
        {
          "id": "file-id",
          "recording_type": "shared_screen_with_speaker_view",
          "file_type": "MP4",
          "file_size": 524288000,
          "download_url": "https://zoom.us/rec/download/..."
        }
      ]
    }
  }
}
```

The system automatically:
- Filters for MP4 files only
- Selects `shared_screen_with_speaker_view` or gallery view
- Downloads using OAuth access token

---

## Support

For issues:
1. Check Error Log in Frappe Desk
2. Review background job queue
3. Verify webhook endpoint is accessible (test with curl)
4. Check Zoom app event subscription status

**Community**: https://discuss.frappe.io/c/lms/70

---

*Last updated: December 27, 2024*
