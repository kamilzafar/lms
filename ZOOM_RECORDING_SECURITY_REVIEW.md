# Zoom Recording Security Review

**Date**: 2026-01-02
**Scope**: Zoom recording access, embedding, and URL management in LMS

## Executive Summary

The Zoom recording feature has **good enrollment-based access control** but has a **URL exposure issue** that could allow authenticated users to share recordings with non-enrolled users. The implementation is functional but not optimally secure for sensitive content.

---

## ✅ GOOD SECURITY PRACTICES

### 1. Access Control - Enrollment Verification
**Location**: `lms/lms/api.py:1937-1966` (get_recording_embed_url)

```python
# Properly checks if user is enrolled in batch
enrolled_batches = frappe.get_all(
    "LMS Batch Enrollment",
    {"member": frappe.session.user},
    pluck="batch"
)

if live_class_doc.batch_name not in enrolled_batches:
    # Also checks if user is enrolled in course directly
    batch_courses = frappe.get_all(...)
    enrolled_courses = frappe.get_all(...)
    if not any(course in enrolled_courses for course in batch_courses):
        frappe.throw(_("You don't have access to this recording"))
```

**Status**: ✅ **SECURE** - API endpoint verifies enrollment before granting access

### 2. Guest User Protection
**Location**: `lms/lms/api.py:1940-1941`

```python
if frappe.session.user == "Guest":
    frappe.throw(_("Please login to view recordings"))
```

**Status**: ✅ **SECURE** - Prevents unauthenticated access

### 3. Efficient Recording Fetching
**Location**: `lms/lms/doctype/lms_live_class/lms_live_class.py:190-232`

- Scheduler checks every **10 minutes** (vs hourly)
- Only processes classes within **1.5 hour window** (efficient)
- Uses asynchronous job queuing

**Status**: ✅ **EFFICIENT** - Recordings available quickly without excessive resource usage

### 4. Database Security
**Location**: `lms/lms/doctype/lms_live_class/lms_live_class.json:188-201`

```json
{
  "fieldname": "recording_url",
  "fieldtype": "Small Text",
  "label": "Recording URL",
  "read_only": 1
},
{
  "fieldname": "recording_password",
  "fieldtype": "Password",
  "label": "Recording Password",
  "read_only": 1
}
```

**Status**: ✅ **SECURE** - Recording credentials stored as read-only fields in database

### 5. Proper Zoom API Authentication
**Location**: `lms/lms/doctype/lms_live_class/lms_live_class.py:248-250`

```python
headers = {
    "Authorization": "Bearer " + authenticate(live_class.zoom_account),
    "content-type": "application/json",
}
```

**Status**: ✅ **SECURE** - Uses OAuth token authentication with Zoom API

---

## ⚠️ SECURITY CONCERNS

### 1. CRITICAL: Recording URL Exposed to Frontend
**Severity**: ⚠️ HIGH
**Location**: `lms/lms/api.py:2001`

```python
# Backend returns actual Zoom URL to frontend
embed_url = recording_url

return {
    "embed_url": embed_url,  # ← This is the actual Zoom recording URL
    "title": live_class_doc.title,
    "description": live_class_doc.description,
    "has_password": bool(password)
}
```

**Problem**:
- The actual Zoom recording URL is sent directly to authenticated students
- Students can copy this URL from:
  - Browser developer tools (Network tab)
  - Browser history
  - Browser cache
  - Page source
- The URL can be shared with non-enrolled users who may still access it if:
  - Recording doesn't have password protection
  - Recording password is discovered (usually 6-8 digits)

**Attack Scenario**:
1. Student A is enrolled in Course XYZ and views recording: `https://zoom.us/rec/share/ABC123...`
2. Student A copies the URL and shares it in a Discord server
3. Non-enrolled users can access the recording directly

**Risk Level**: **MEDIUM-HIGH** - Depends on whether recordings are password-protected

---

### 2. Recording Password Flag Exposure
**Severity**: ⚠️ MEDIUM
**Location**: `lms/lms/api.py:2040`

```python
return {
    "embed_url": embed_url,
    "title": live_class_doc.title,
    "description": live_class_doc.description,
    "has_password": bool(password)  # ← Tells user a password exists
}
```

**Problem**:
- Frontend reveals `has_password` flag to students
- Students know whether to attempt password guessing
- Zoom passwords are typically weak (6-digit numeric codes)

---

### 3. No Audit Logging
**Severity**: ⚠️ MEDIUM
**Location**: Recording access not logged

**Problem**:
- No record of which students accessed which recordings
- No way to detect unauthorized access patterns
- Compliance/audit trail missing

---

### 4. No Rate Limiting
**Severity**: ⚠️ LOW-MEDIUM
**Location**: `lms/lms/api.py:1937` (get_recording_embed_url)

**Problem**:
- No rate limiting on API endpoint
- Malicious users could enumerate recording URLs
- Brute force password attempts (though limited by Zoom)

---

### 5. URL Password Handling Assumptions
**Severity**: ⚠️ MEDIUM
**Location**: `lms/lms/api.py:2012-2034`

```python
if password and "pwd=" not in recording_url and "password=" not in recording_url:
    if "/rec/share/" not in recording_url:
        # Try adding password as query parameter for direct playback URLs
```

**Problem**:
- Code assumes share URLs (`/rec/share/`) handle passwords via Zoom UI
- Not all Zoom recording types follow the same URL structure
- URL format detection is brittle and could break with Zoom API changes

---

## 📊 RISK MATRIX

| Issue | Severity | Likelihood | Impact | Recommendation |
|-------|----------|-----------|--------|---|
| URL exposed to frontend | HIGH | HIGH | Students can share URLs | Implement proxy/wrapper |
| Password flag disclosure | MEDIUM | MEDIUM | Weak password brute force | Remove flag or use time-limited tokens |
| No audit logging | MEDIUM | LOW | Compliance issues | Add access logging |
| No rate limiting | LOW-MEDIUM | LOW | Enumeration attacks | Add rate limiting |
| URL format assumptions | MEDIUM | LOW | URL handling failure | Use Zoom's embed API properly |

---

## 🔧 RECOMMENDED SOLUTIONS

### Solution 1: Backend Proxy (RECOMMENDED - Most Secure)
Instead of returning the Zoom URL to frontend:

```python
# Instead of:
return {"embed_url": recording_url}

# Do this:
return {
    "embed_url": f"/api/resource/LMS%20Live%20Class/{live_class}/recording",
    "title": live_class_doc.title
}

# Then create a new endpoint:
@frappe.whitelist()
def get_recording_proxy(live_class_name):
    """Proxy endpoint that re-authenticates on each request"""
    live_class = frappe.get_doc("LMS Live Class", live_class_name)

    # Verify access again
    verify_recording_access(live_class)

    # Return iframe that embeds via Zoom's official embed API
    # NOT a direct share URL
    return Response(
        f'<iframe src="{live_class.recording_url}"></iframe>',
        content_type="text/html"
    )
```

**Advantages**:
- ✅ Recording URL never exposed to frontend
- ✅ Access verified on each request
- ✅ Easy to add audit logging
- ✅ Can implement rate limiting

---

### Solution 2: Time-Limited JWT Tokens
Return temporary tokens instead of direct URLs:

```python
def get_recording_embed_url(live_class):
    verify_access(live_class)

    # Generate time-limited JWT (valid for 30 minutes)
    token = frappe.generate_hash(length=32)
    frappe.cache().set(
        f"recording_token_{live_class}_{frappe.session.user}",
        token,
        ex=1800  # 30 minutes
    )

    return {
        "embed_url": f"/api/method/get_recording_token?token={token}",
        "title": live_class_doc.title
    }
```

**Advantages**:
- ✅ Tokens expire automatically
- ✅ Tokens are user-specific
- ✅ Can't be reused indefinitely
- ✅ Easy to revoke

---

### Solution 3: Zoom Embed API (If Available)
Use Zoom's official embedding method instead of `play_url`:

```python
# Zoom provides embed URLs like:
# https://zoom.us/web_client/rec/play/MEETING_ID?pwd=PASSWORD

# Or use Zoom Web SDK for programmatic access control
```

---

## 📋 IMPLEMENTATION CHECKLIST

### Immediate (High Priority)
- [ ] **Add access logging** to `get_recording_embed_url()` endpoint
  - Log who accessed which recording and when
  - Store in new `LMS Recording Access Log` DocType

- [ ] **Add rate limiting** to prevent enumeration
  ```python
  from frappe.rate_limiter import rate_limit

  @frappe.whitelist()
  @rate_limit(limit_by="user", limit=10, window=60)  # 10 requests per minute
  def get_recording_embed_url(live_class):
  ```

- [ ] **Remove password flag** from response
  ```python
  # Change this:
  "has_password": bool(password)
  # To: Don't expose it at all
  ```

### Medium Priority
- [ ] Implement backend proxy endpoint
- [ ] Migrate to use time-limited tokens
- [ ] Add recording access audit report

### Long-term
- [ ] Implement Zoom Web SDK for native recording playback
- [ ] Add IP whitelisting for recording access
- [ ] Implement recording watermarking (if Zoom supports)
- [ ] Add DRM/Copy protection (if critical content)

---

## 🔍 TESTING RECOMMENDATIONS

### Access Control Tests
```bash
# Test 1: Non-enrolled user cannot access
curl -X POST /api/method/get_recording_embed_url \
  -d 'live_class=TEST-001' \
  # Should fail with "You don't have access to this recording"

# Test 2: Guest user cannot access
# (Already tested, but verify)

# Test 3: Enrolled user gets URL
# (Verify access control works)
```

### URL Exposure Tests
```bash
# Test 4: Verify URL cannot be shared
# 1. Logged in as Student A - Get recording URL
# 2. Log out
# 3. Try to access URL directly in browser
# 4. Check if Zoom enforces password protection

# Test 5: Check for URL in logs
# Search application logs for recording_url exposure
```

---

## 📌 SUMMARY

| Category | Status | Notes |
|----------|--------|-------|
| Access Control | ✅ Good | Enrollment verified properly |
| Authentication | ✅ Good | Zoom API auth is secure |
| URL Security | ⚠️ Needs Work | URLs exposed to frontend |
| Audit Trail | ❌ Missing | No logging of access |
| Rate Limiting | ❌ Missing | No protection against abuse |

---

## 🎯 CONCLUSION

**The feature works well for legitimate access but needs URL security improvements.**

The current implementation successfully:
- ✅ Prevents guest/unauthenticated access
- ✅ Verifies enrollment before granting access
- ✅ Efficiently fetches recordings
- ✅ Uses proper Zoom API authentication

However, it should be improved to:
- ⚠️ Implement backend proxy to avoid URL exposure
- ⚠️ Add access logging for compliance
- ⚠️ Implement rate limiting
- ⚠️ Use time-limited tokens instead of permanent URLs

**Recommendation**: Implement Solution 1 (Backend Proxy) for production use with sensitive content.
