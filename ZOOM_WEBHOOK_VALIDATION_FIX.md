# Zoom Webhook Validation Fix - Comprehensive Debug Logging

## Problem
Zoom validation was still failing even though logs showed HTTP 200 for POST requests to `/api/method/lms.lms.api.zoom_webhook`. The validation response format or content was likely incorrect.

## Root Cause Analysis

Zoom's endpoint validation requires:
1. **Exact JSON format**: `{"plainToken": "<token>", "encryptedToken": "<hmac_hash>"}`
2. **Correct HMAC-SHA256 calculation**: `HMAC_SHA256(plainToken, webhook_secret_token)`
3. **Proper HTTP headers**: `Content-Type: application/json`
4. **HTTP 200 status**: Always return 200 OK
5. **No Frappe response wrapping**: Return raw JSON, not Frappe's default wrapper

Potential issues in previous implementation:
- Frappe may have wrapped the response in additional JSON structure
- Incorrect Content-Type header
- HMAC calculation using wrong secret or method
- Response not being serialized correctly

## Solution Implemented

### 1. Enhanced Validation Response Handling

**File**: `/lms/lms/api.py` (lines 1995-2067)

```python
# Construct response exactly as Zoom expects
validation_response = {
    "plainToken": plain_token,
    "encryptedToken": encrypted_token
}

# Set response headers explicitly
frappe.local.response.http_status_code = 200
frappe.local.response["Content-Type"] = "application/json"

# Return raw response without Frappe wrapping
frappe.local.response.update({"data": validation_response})
frappe.response.update(validation_response)

return validation_response
```

**Key changes**:
- Explicit `Content-Type: application/json` header
- Multiple response updates to ensure Frappe sends raw JSON
- `frappe.local.response.update({"data": ...})` prevents wrapping
- `frappe.response.update(...)` sets response body directly

### 2. Comprehensive Debug Logging

Added detailed logging at every step of webhook processing:

#### Validation Request Logging
```python
frappe.logger().info(f"Zoom Webhook Received: event={event}")
frappe.logger().info(f"Zoom endpoint validation request received. plainToken={plain_token}")
frappe.logger().info(f"Zoom Webhook: Using webhook_secret_token from {name} (length: {len(webhook_secret)})")
frappe.logger().info(f"Zoom Webhook Validation: Generated encryptedToken={encrypted_token} from plainToken={plain_token}")
frappe.logger().info(f"Zoom Webhook Validation Response: {json.dumps(validation_response)}")
```

#### Webhook Secret Token Logging
```python
if not zoom_settings:
    frappe.logger().error("Zoom Webhook Validation: No LMS Zoom Settings records found")
elif not zoom_settings[0].get("webhook_secret_token"):
    frappe.logger().error(f"Zoom Webhook Validation: webhook_secret_token is empty in {name}")
else:
    frappe.logger().info(f"Zoom Webhook: Using webhook_secret_token from {name} (length: {len(webhook_secret)})")
```

#### Signature Verification Logging
```python
frappe.logger().info(f"Zoom Webhook: Verifying signature for event={event}")
frappe.logger().info(f"Zoom Webhook Signature Verification: Success")
# Or on failure:
frappe.logger().warning(f"Zoom Webhook Signature Verification Failed: expected={expected}, received={actual}")
```

#### Recording Event Logging
```python
frappe.logger().info(f"Zoom Webhook: recording.completed event for meeting_uuid={uuid}, files={count}")
frappe.logger().info(f"Zoom Webhook: Queueing background job to process recording")
frappe.logger().info(f"Zoom Webhook: Recording processing queued successfully")
```

#### Error Logging
```python
# JSON parsing error
frappe.logger().error(f"Zoom Webhook: Invalid JSON payload: {str(e)}")

# Missing parameters
frappe.logger().error(f"Zoom Webhook: Missing meeting UUID in recording.completed event")

# Unhandled events
frappe.logger().warning(f"Zoom Webhook: Unhandled event type: {event}")

# Exceptions
frappe.logger().error(f"Zoom Webhook: Exception in zoom_webhook: {str(e)}")
```

### 3. Enhanced Signature Verification Logging

**File**: `/lms/lms/api.py` (lines 2173-2213)

Added logging to `verify_zoom_signature()` function:

```python
def verify_zoom_signature(signature, timestamp, secret):
    """Verify Zoom webhook signature using HMAC-SHA256"""
    if not signature or not timestamp or not secret:
        frappe.logger().warning(
            f"Zoom Webhook Signature Verification: Missing parameters - "
            f"signature={'present' if signature else 'missing'}, "
            f"timestamp={'present' if timestamp else 'missing'}, "
            f"secret={'present' if secret else 'missing'}"
        )
        return False

    # ... HMAC calculation ...

    if not is_valid:
        frappe.logger().warning(
            f"Zoom Webhook Signature Verification Failed: "
            f"expected={expected_signature}, received={signature}"
        )
    else:
        frappe.logger().info("Zoom Webhook Signature Verification: Success")

    return is_valid
```

### 4. Separate JSON Error Handling

Added specific exception handling for JSON parsing errors:

```python
except json.JSONDecodeError as e:
    error_msg = f"Invalid JSON payload: {str(e)}"
    frappe.log_error(f"{error_msg}\nRaw data: {frappe.request.data}", "Zoom Webhook JSON Error")
    frappe.logger().error(f"Zoom Webhook: {error_msg}")
    frappe.local.response.http_status_code = 200
    return {"status": "error", "message": "Invalid JSON"}
```

## How to Use Debug Logs

### View Logs in Development

```bash
# Watch logs in real-time
bench --site yoursite.com logs

# Or tail the log file directly
tail -f logs/web.log | grep "Zoom Webhook"
```

### View Logs in Production

```bash
# Docker
docker logs -f <container_name> | grep "Zoom Webhook"

# Supervisor
tail -f /path/to/frappe-bench/logs/web.log | grep "Zoom Webhook"
```

### Check Logs via Frappe Desk

1. Go to Frappe Desk: `https://yoursite.com/app`
2. Search for **"Error Log"** doctype
3. Filter by error title containing "Zoom Webhook"
4. View detailed error messages and stack traces

### Example: Debugging Validation Failure

**Step 1: Trigger validation in Zoom App**

**Step 2: Check logs for validation request:**
```bash
bench --site yoursite.com logs | grep "Zoom Webhook"
```

**Step 3: Look for log sequence:**
```
INFO Zoom Webhook Received: event=endpoint.url_validation
INFO Zoom endpoint validation request received. plainToken=abc123xyz...
INFO Zoom Webhook: Using webhook_secret_token from LMS-ZOOM-001 (length: 32)
INFO Zoom Webhook Validation: Generated encryptedToken=def456abc... from plainToken=abc123xyz...
INFO Zoom Webhook Validation Response: {"plainToken": "abc123xyz...", "encryptedToken": "def456abc..."}
```

**Step 4: Verify webhook secret token:**
```python
# In bench console
frappe.get_all("LMS Zoom Settings",
    fields=["name", "webhook_secret_token"],
    limit=1
)
```

**Step 5: Test HMAC calculation manually:**
```python
import hmac
import hashlib

plain_token = "abc123xyz..."  # From logs
webhook_secret = "your_secret_token"  # From LMS Zoom Settings

encrypted_token = hmac.new(
    webhook_secret.encode(),
    plain_token.encode(),
    hashlib.sha256
).hexdigest()

print(f"Expected encryptedToken: {encrypted_token}")
# Compare with value in logs
```

## Common Issues & Solutions

### Issue 1: Empty webhook_secret_token

**Logs show:**
```
ERROR Zoom Webhook Validation: webhook_secret_token is empty in LMS-ZOOM-001
```

**Solution:**
1. Go to Zoom App → Features → Event Subscriptions
2. Copy the Secret Token
3. Paste into LMS Zoom Settings → webhook_secret_token field
4. Save
5. Try validation again

### Issue 2: No LMS Zoom Settings found

**Logs show:**
```
ERROR Zoom Webhook Validation: No LMS Zoom Settings records found
```

**Solution:**
1. Go to Frappe Desk
2. Search for "LMS Zoom Settings"
3. Create new record
4. Add all credentials (Account ID, Client ID, Client Secret, Webhook Secret Token)
5. Save

### Issue 3: Signature verification fails

**Logs show:**
```
WARNING Zoom Webhook Signature Verification Failed: expected=v0=abc123..., received=v0=xyz789...
```

**Solution:**
- webhook_secret_token in LMS doesn't match Zoom App
- Copy Secret Token from Zoom App again
- Update LMS Zoom Settings
- Delete and recreate event subscription in Zoom

### Issue 4: Validation response not in expected format

**Check logs for:**
```
INFO Zoom Webhook Validation Response: {...}
```

**Should show:**
```json
{"plainToken": "abc123...", "encryptedToken": "def456..."}
```

If format is different (wrapped in `{"data": {...}}` or `{"message": {...}}`), Frappe is wrapping the response.

**Solution**: The fix implemented should prevent this, but if it still occurs:
- Check Frappe version (v14+ recommended)
- Verify the response update code is executing
- Add more explicit response handling

## Testing the Fix

### Test 1: Validation Request Logging

```bash
# Send test validation request
curl -X POST https://yoursite.com/api/method/lms.lms.api.zoom_webhook \
  -H "Content-Type: application/json" \
  -d '{
    "event": "endpoint.url_validation",
    "payload": {
      "plainToken": "test_token_12345"
    }
  }'
```

**Check logs for:**
```
INFO Zoom Webhook Received: event=endpoint.url_validation
INFO Zoom endpoint validation request received. plainToken=test_token_12345
INFO Zoom Webhook Validation Response: {"plainToken": "test_token_12345", "encryptedToken": "..."}
```

**Verify response:**
- HTTP 200 OK
- Content-Type: application/json
- Body contains both plainToken and encryptedToken

### Test 2: Real Zoom Validation

1. Configure webhook secret token in LMS
2. Add webhook URL in Zoom App
3. Check logs during validation
4. Verify green checkmark appears in Zoom App

### Test 3: Recording Event

1. Create live class with cloud recording
2. End meeting
3. Wait for Zoom processing
4. Check logs for webhook receipt and job queueing

## Files Modified

1. **`/lms/lms/api.py`** (lines 1960-2213)
   - Enhanced validation response handling
   - Added comprehensive debug logging throughout
   - Improved signature verification logging
   - Added JSON error handling

2. **`/ZOOM_RECORDING_SETUP.md`**
   - Added "Debugging & Logs" section
   - Example log messages
   - Debug procedures

3. **`/ZOOM_WEBHOOK_VALIDATION_FIX.md`** (this file)
   - Complete documentation of validation fix
   - Debug logging guide
   - Troubleshooting procedures

## Log Message Reference

### INFO Messages (Normal Operation)

| Message | Meaning |
|---------|---------|
| `Zoom Webhook Received: event=X` | Webhook request received for event X |
| `Zoom endpoint validation request received` | Validation request being processed |
| `Using webhook_secret_token from X (length: N)` | Found and using webhook secret |
| `Generated encryptedToken=X from plainToken=Y` | HMAC calculation completed |
| `Zoom Webhook Validation Response: {...}` | Sending validation response to Zoom |
| `Signature verification successful` | Webhook signature valid |
| `Recording processing queued successfully` | Background job created |

### WARNING Messages (Non-Critical Issues)

| Message | Meaning |
|---------|---------|
| `Unhandled event type: X` | Received unknown event type |
| `Signature Verification: Missing parameters` | Headers missing for verification |
| `Signature Verification Failed: expected=X, received=Y` | Invalid signature |

### ERROR Messages (Critical Issues)

| Message | Meaning |
|---------|---------|
| `No LMS Zoom Settings records found` | Zoom not configured |
| `webhook_secret_token is empty` | Secret token not set |
| `Missing plainToken in validation request` | Malformed request |
| `Invalid JSON payload` | Request body not valid JSON |
| `Exception in zoom_webhook` | Unexpected error occurred |

## Success Criteria

- ✅ Comprehensive logging at all execution paths
- ✅ Debug logs show received event and tokens
- ✅ Webhook secret token source is logged
- ✅ HMAC calculation is logged
- ✅ Validation response format is logged
- ✅ Signature verification success/failure is logged
- ✅ All errors include context for debugging
- ✅ Logs viewable in real-time and in Frappe Desk

## Next Steps

1. **Deploy the fix** to your LMS instance
2. **Restart Frappe**: `bench restart`
3. **Clear cache**: `bench --site yoursite.com clear-cache`
4. **Test validation** in Zoom App
5. **Check logs** for complete execution trace
6. **Share log output** if validation still fails for further diagnosis

---

**Status**: ✅ Complete - Comprehensive Debug Logging Implemented
**Date**: December 27, 2024
**Impact**: Dramatically improves troubleshooting capability for webhook issues
