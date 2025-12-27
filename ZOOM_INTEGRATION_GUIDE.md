# Complete Zoom Integration Guide for Auto-Recording Upload

This guide walks you through connecting Zoom with your LMS so that class recordings automatically upload to lessons.

---

## Prerequisites

- ✅ LMS installed and running on a publicly accessible domain (not localhost)
- ✅ HTTPS/SSL certificate configured and valid
- ✅ Zoom Pro/Business/Education account (cloud recording enabled)
- ✅ Admin access to Zoom App Marketplace
- ✅ Moderator/System Manager access to LMS

---

## Part 1: Create Zoom Server-to-Server OAuth App

### Step 1: Go to Zoom App Marketplace

1. Visit: https://marketplace.zoom.us/
2. Sign in with your Zoom account
3. Click **"Develop"** in the top right
4. Click **"Build App"**

### Step 2: Create Server-to-Server OAuth App

1. Select **"Server-to-Server OAuth"**
2. Click **"Create"**
3. Enter app details:
   ```
   App Name: LMS Auto Recording Upload
   Company Name: [Your Organization Name]
   Developer Name: [Your Name]
   Developer Email: [Your Email]
   ```
4. Click **"Create"**

### Step 3: Configure App Information

1. Fill in the app information:
   ```
   Short Description: Automatically upload Zoom recordings to LMS lessons
   Long Description: This integration automatically downloads cloud recordings from Zoom meetings and uploads them to the associated course lessons in the LMS.
   ```
2. Click **"Continue"**

### Step 4: Configure Scopes (Permissions)

Add the following scopes - these are REQUIRED:

**Meeting Scopes:**
- ✅ `meeting:read:admin` - View meeting details
- ✅ `meeting:write:admin` - Create meetings

**Recording Scopes:**
- ✅ `recording:read:admin` - View recordings
- ✅ `recording:write:admin` - Download recordings

**User Scopes:**
- ✅ `user:read:admin` - View user information

To add scopes:
1. Click **"+ Add Scopes"**
2. Search for each scope above
3. Toggle them ON
4. Click **"Done"**
5. Click **"Continue"**

### Step 5: Copy Your Credentials

**IMPORTANT**: Copy these credentials - you'll need them later!

```
Account ID: [Copy this - looks like: abc123xyz]
Client ID: [Copy this - looks like: AbC123XyZ456...]
Client Secret: [Copy this - looks like: A1b2C3d4E5f6...]
```

**Save these securely** - you cannot view the Client Secret again after leaving this page.

### Step 6: Activate the App

1. Toggle **"Activation"** to ON
2. The app is now active and ready to use

---

## Part 2: Configure LMS Zoom Settings

### Step 1: Access Frappe Desk

1. Navigate to: `https://yoursite.com/app`
2. Login with admin credentials

### Step 2: Create LMS Zoom Settings

1. In the search bar (Ctrl+K or Cmd+K), type: **"LMS Zoom Settings"**
2. Click **"New LMS Zoom Settings"** or open existing one

### Step 3: Enter Zoom Credentials

Fill in the form with credentials from Part 1, Step 5:

```
Account ID: [Paste Account ID from Zoom]
Client ID: [Paste Client ID from Zoom]
Client Secret: [Paste Client Secret from Zoom]
User: [Select your user email]
```

**Note**: Leave `Webhook Secret Token` blank for now - we'll add it in Part 3.

### Step 4: Save and Test Connection

1. Click **"Save"**
2. The system will attempt to authenticate with Zoom
3. If successful, you'll see authentication confirmation

**Troubleshooting**:
- If authentication fails, verify credentials are correct
- Ensure scopes are configured in Zoom app
- Check that the app is activated

---

## Part 3: Configure Zoom Webhook for Auto-Upload

This is the most critical part for automatic recording upload.

### Step 1: Go Back to Your Zoom App

1. Visit: https://marketplace.zoom.us/
2. Click **"Manage"** → **"Build App"**
3. Open your **"LMS Auto Recording Upload"** app

### Step 2: Navigate to Features Tab

1. Click on the **"Features"** tab
2. Scroll to **"Event Subscriptions"** section
3. Click **"Add New Event Subscription"**

### Step 3: Configure Event Subscription

1. **Subscription Name**: `LMS Recording Upload`

2. **Event notification endpoint URL**:
   ```
   https://yoursite.com/api/method/lms.lms.api.zoom_webhook
   ```
   Replace `yoursite.com` with your actual domain.

   **Examples**:
   - `https://lms.example.com/api/method/lms.lms.api.zoom_webhook`
   - `https://learning.myschool.edu/api/method/lms.lms.api.zoom_webhook`

3. **IMPORTANT**: After entering the URL, Zoom will show a **Secret Token**
   - Copy this token (looks like: `aBc123XyZ789...`)
   - **DO NOT click "Validate" yet!**

### Step 4: Add Secret Token to LMS (Critical Step!)

**Before validating the endpoint, you MUST configure the secret token in LMS:**

1. Go back to Frappe Desk: `https://yoursite.com/app`
2. Open **LMS Zoom Settings** (search: Ctrl+K)
3. Open the record you created in Part 2
4. Paste the Secret Token into the **"Webhook Secret Token"** field
5. Click **"Save"**

**Why this order matters**: The webhook endpoint needs the secret token to validate Zoom's request. If you validate before configuring the token, validation will fail.

### Step 5: Subscribe to Recording Events

Back in the Zoom App:

1. Under **"Event types"**, click **"+ Add events"**
2. Expand **"Recording"** category
3. Select these events:
   - ✅ **Recording Completed** (`recording.completed`) - REQUIRED
   - ✅ **Recording Ready** (optional, for redundancy)
4. Click **"Done"**

### Step 6: Validate the Endpoint

**Now** you can validate:

1. Click **"Save"** at the bottom of the Event Subscription
2. Zoom will send a validation request to your endpoint
3. If configured correctly, you'll see a ✅ green checkmark
4. Status will show: **"Enabled"**

**If validation fails**, see troubleshooting section below.

---

## Part 4: Test the Integration

### Step 1: Create a Batch and Live Class

1. In LMS, go to **Batches**
2. Create a new batch or open existing one
3. Click **"+ Create Live Class"**
4. Fill in details:
   ```
   Title: Test Auto Recording
   Date: [Today or tomorrow]
   Time: [Any time]
   Duration: 30 minutes
   ```
5. **Important**: Link to a lesson:
   - Select a course
   - Select a specific lesson
6. Click **"Create"**

The system will automatically create a Zoom meeting.

### Step 2: Start the Meeting and Record

1. In the live class details, click **"Start Meeting"**
2. Zoom will open
3. **Important**: Click **"Record to Cloud"** (not local recording!)
4. Conduct a short test session (even 1-2 minutes is fine)
5. End the meeting

### Step 3: Wait for Zoom Processing

- Zoom takes **5-60 minutes** to process cloud recordings
- Longer recordings take more time
- You'll receive an email from Zoom when processing is complete

### Step 4: Verify Auto-Upload

After Zoom processing completes:

1. Go to the **Course Lesson** linked to your live class
2. Check the lesson content
3. You should see a **video block at the top** with the recording
4. The video should be playable directly in the lesson

**What happens behind the scenes**:
1. Zoom sends webhook to LMS: "Recording completed"
2. LMS queues a background job
3. Job downloads the MP4 file from Zoom
4. Uploads to Frappe file system
5. Adds video block to lesson content
6. Marks recording as processed

---

## Verification Checklist

After setup, verify everything is working:

### Zoom App Configuration
- [ ] Server-to-Server OAuth app created
- [ ] All required scopes added
- [ ] App is activated
- [ ] Credentials copied

### LMS Zoom Settings
- [ ] Account ID configured
- [ ] Client ID configured
- [ ] Client Secret configured
- [ ] User selected
- [ ] Webhook Secret Token configured
- [ ] Settings saved successfully

### Webhook Configuration
- [ ] Event subscription created
- [ ] Correct endpoint URL entered
- [ ] Secret token copied to LMS
- [ ] "Recording Completed" event subscribed
- [ ] Endpoint validation successful (green checkmark)

### Testing
- [ ] Live class created and linked to lesson
- [ ] Meeting started with cloud recording
- [ ] Meeting ended
- [ ] Recording appeared in lesson (after Zoom processing)

---

## Troubleshooting

### Zoom App Issues

#### "Scopes not authorized"
**Solution**: Go to Zoom App → Scopes tab → Add all required scopes listed in Part 1, Step 4

#### "Authentication failed"
**Solution**:
1. Verify Account ID, Client ID, Client Secret are correct
2. Ensure app is activated in Zoom
3. Check if scopes include `meeting:write:admin`

### Webhook Issues

#### "Please validate your endpoint URL"

**Common causes**:

1. **Secret token not configured in LMS**
   ```bash
   # Check if configured
   bench --site yoursite.com console
   ```
   ```python
   frappe.get_all("LMS Zoom Settings", fields=["webhook_secret_token"])
   ```
   Should show a token, not empty. If empty, go back to Part 3, Step 4.

2. **Endpoint not accessible**
   ```bash
   # Test from external server
   curl -X POST https://yoursite.com/api/method/lms.lms.api.zoom_webhook
   ```
   Should return HTTP 200, not timeout or error.

3. **SSL certificate issue**
   - Zoom requires valid, trusted SSL
   - Self-signed certificates will fail
   - Use Let's Encrypt or commercial SSL

4. **Wrong URL format**
   - Must include `/api/method/` prefix
   - Must be HTTPS (not HTTP)
   - Correct: `https://site.com/api/method/lms.lms.api.zoom_webhook`
   - Wrong: `https://site.com/lms.lms.api.zoom_webhook`

#### "Invalid signature" error in logs

**Solution**:
1. Go to Zoom App → Features → Event Subscriptions
2. Copy the **Secret Token** exactly (no spaces)
3. Paste into LMS Zoom Settings → Webhook Secret Token
4. Save
5. Delete and recreate the event subscription in Zoom to get a fresh validation

### Recording Not Uploading

#### Check webhook is being received

```bash
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

If no logs, webhook isn't reaching your server. Check:
- Event subscription is "Enabled" in Zoom
- Correct endpoint URL
- Server is accessible from internet

#### Check background worker is running

```bash
# Development
ps aux | grep "bench worker"

# Production (Supervisor)
sudo supervisorctl status frappe-bench-workers:

# Production (Docker)
docker ps | grep worker
```

If no worker running:
```bash
# Development
bench worker

# Production - restart supervisor
sudo supervisorctl restart frappe-bench-workers:*
```

#### Recording downloads but doesn't appear in lesson

**Check**:
1. Was the live class linked to a lesson?
   - Open LMS Live Class record
   - Check "Lesson" field is populated

2. Check recording processed flag:
   ```python
   # In bench console
   frappe.get_value("LMS Live Class", "LIVE-CLASS-NAME",
       ["recording_processed", "recording_file", "recording_url"],
       as_dict=1
   )
   ```
   Should show `recording_processed = 1`

3. Manually check lesson content:
   ```python
   import json
   lesson = frappe.get_doc("Course Lesson", "LESSON-NAME")
   content = json.loads(lesson.content)
   print(json.dumps(content, indent=2))
   # Look for "type": "upload" blocks
   ```

---

## Advanced Configuration

### Multiple Zoom Accounts

The LMS supports multiple Zoom accounts:

1. Create multiple LMS Zoom Settings records
2. Each with different Account ID, Client ID, Secret
3. When creating live class, select which Zoom account to use

### Custom Recording Position

By default, recordings are added to the **top** of the lesson.

To change position, edit:
`/lms/lms/doctype/lms_live_class/lms_live_class.py`

```python
# Find process_zoom_recording() function
# Change:
content["blocks"].insert(0, video_block)  # Top

# To:
content["blocks"].append(video_block)  # Bottom
```

### Recording Notifications

To email instructors when recording is ready:

Edit: `/lms/lms/doctype/lms_live_class/lms_live_class.py`

```python
# In process_zoom_recording(), after successful upload:
frappe.sendmail(
    recipients=[self.owner],
    subject=f"Recording Ready: {self.title}",
    message=f"Your class recording has been uploaded to the lesson.<br><br>"
            f"<a href='{frappe.utils.get_url()}/app/course-lesson/{lesson_doc.name}'>View Lesson</a>"
)
```

---

## Security Best Practices

1. **Keep credentials secure**
   - Never commit Client Secret to git
   - Restrict access to LMS Zoom Settings doctype

2. **Use dedicated Zoom user**
   - Create a service account in Zoom for LMS
   - Don't use personal Zoom accounts

3. **Monitor webhook logs**
   - Regularly check Error Logs for suspicious activity
   - Investigate unexpected signature failures

4. **Limit permissions**
   - Only give Moderator role to trusted users
   - They can create meetings and access recordings

---

## FAQ

**Q: Can I use a free Zoom account?**
A: No, cloud recording requires Zoom Pro or higher.

**Q: How long are recordings stored?**
A: Recordings are uploaded to your LMS file system and stored indefinitely. The original Zoom recording follows your Zoom account's retention policy.

**Q: Can I manually upload recordings?**
A: Yes, you can manually add video blocks to lessons using the lesson editor.

**Q: What video formats are supported?**
A: The system automatically downloads MP4 files from Zoom recordings.

**Q: Can I disable auto-upload for specific meetings?**
A: Not currently. All cloud recordings from linked live classes will auto-upload. To prevent upload, don't enable cloud recording.

**Q: What if the recording fails to upload?**
A: Check Error Logs in Frappe Desk. Common issues: background worker not running, Zoom API permissions, network issues.

**Q: Can I re-process a failed recording?**
A: Yes, manually trigger the background job:
```bash
bench --site yoursite.com console
```
```python
frappe.enqueue(
    "lms.lms.doctype.lms_live_class.lms_live_class.process_zoom_recording",
    meeting_uuid="MEETING-UUID",
    recording_files=[...],  # From webhook payload
    queue="long"
)
```

---

## Support Resources

- **LMS Documentation**: Check `CLAUDE.md` in repository
- **Zoom API Docs**: https://developers.zoom.us/docs/api/
- **Frappe Community**: https://discuss.frappe.io/c/lms/70
- **Error Logs**: Always check Frappe Error Log for detailed error messages

---

## Quick Reference Card

### Zoom App Scopes Required
```
✅ meeting:read:admin
✅ meeting:write:admin
✅ recording:read:admin
✅ recording:write:admin
✅ user:read:admin
```

### Webhook Endpoint URL
```
https://YOURSITE.com/api/method/lms.lms.api.zoom_webhook
```

### Setup Order (Critical!)
```
1. Create Zoom App + Copy credentials
2. Configure LMS Zoom Settings with credentials
3. Add webhook URL in Zoom
4. Copy Secret Token from Zoom
5. ADD SECRET TOKEN TO LMS FIRST ← Critical!
6. Then validate endpoint in Zoom
7. Test with live class recording
```

### Check Integration Status
```bash
# LMS settings configured?
bench console → frappe.get_all("LMS Zoom Settings")

# Webhook logs?
bench console → frappe.get_all("Error Log", filters={"error": ["like", "%Zoom%"]})

# Worker running?
ps aux | grep "bench worker"
```

---

*Last updated: December 27, 2024*
*Version: 1.0 - Compatible with Frappe LMS*
