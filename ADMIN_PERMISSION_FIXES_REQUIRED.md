# Admin Permission Issues - Complete Fix Plan

**Date**: January 6, 2026
**Issue**: Custom admin role (with ALL available roles) cannot perform admin operations
**Root Cause**: Incomplete permission checks and missing role entries in DocType permissions
**Status**: Ready for Implementation

---

## CRITICAL ISSUES FOUND

### Issue #1: Missing "Course Creator" in LMS Batch Permissions ❌

**File**: `lms/lms/doctype/lms_batch/lms_batch.json`

**Current Permissions**:
- ✅ System Manager - FULL CRUD
- ✅ Moderator - FULL CRUD
- ✅ Batch Evaluator - FULL CRUD
- ❌ Course Creator - **MISSING** ← Problem!
- LMS Student - Read-only
- LMS Teacher - Read-only

**Impact**:
- Users with only "Course Creator" role cannot create batches
- Your admin role should have System Manager/Moderator, so this shouldn't block you UNLESS:
  - You're testing with a user that has only Course Creator role
  - OR your admin role definition doesn't include System Manager/Moderator

**Fix Required**: Add Course Creator permission to LMS Batch

---

### Issue #2: Missing "Course Creator" in LMS Enrollment Permissions ❌

**File**: `lms/lms/doctype/lms_enrollment/lms_enrollment.json`

**Current Permissions**:
- ✅ System Manager - FULL CRUD
- ✅ Moderator - FULL CRUD
- ❌ Course Creator - **MISSING** ← Problem!
- LMS Student - Read-only

**Impact**:
- Users with only "Course Creator" role cannot enroll students in courses
- Your admin role should work if it includes System Manager/Moderator

**Fix Required**: Add Course Creator permission to LMS Enrollment

---

### Issue #3: No Permission Checks on Critical Delete Operations ⚠️

**Files**: `lms/lms/api.py`

These functions have **ZERO permission validation**:
- `delete_lesson()` (line 472)
- `delete_course()` (line 846)
- `delete_batch()` (line 887)
- `update_sidebar_item()` (line 441)
- `delete_sidebar_item()` (line 459)

**Why This is a Problem**:
1. Frappe's default permission system should catch this... but maybe not
2. Any authenticated user might be able to call these directly
3. Your admin users should have permission via DocType rules, but it's not validated in code

**Status**:
- Probably NOT blocking your admin (they should have permissions)
- But creates a security hole for non-admin users
- And unreliable - depends on Frappe's backend validation

---

## EXACT PROBLEM DIAGNOSIS

Since your admin role has **ALL available roles** (System Manager + Moderator + Batch Evaluator + Course Creator + LMS Teacher + LMS Student):

✅ Should NOT be blocked by:
- LMS Course operations (all admin roles have CRUD)
- LMS Batch operations (has System Manager, Moderator, Batch Evaluator)
- LMS Enrollment operations (has System Manager, Moderator)
- Settings access (has Moderator)
- Assignment/Lesson/Quiz operations (has all admin roles)

❌ MIGHT be blocked by:
1. **Frappe's User DocType Permissions**
   - If your admin role doesn't have User CRUD permissions
   - Needed to create/edit/delete user accounts

2. **Member/Evaluator Management**
   - These are done through Settings dialog
   - Requires Moderator role (which you have ✅)
   - Or through User DocType (might need explicit permission)

3. **Frontend Permission Checks**
   - Some features might be hidden in UI even if backend allows them
   - But they exist and should be bypassed for admin

---

## THE REAL ISSUE: What Permissions Does Your Custom Admin Role Have?

When you selected "all available roles", you likely selected from Frappe's role picker.

**Your admin role should include** (at minimum):
```
Included Roles:
  ✅ System Manager  (from Frappe)
  ✅ Moderator        (from LMS)
  ✅ Course Creator    (from LMS)
  ✅ Batch Evaluator   (from LMS)
```

**If your admin role is MISSING any of these**, they're blocked from those operations.

---

## RECOMMENDED FIXES

### Fix #1: Add Course Creator to LMS Batch Permissions

**File**: `lms/lms/doctype/lms_batch/lms_batch.json`

**Add this permission block** (after the Moderator permission):

```json
{
  "docstatus": 0,
  "doctype": "Custom DocPerm",
  "fieldname": null,
  "idx": 4,
  "name": "LMS Batch-Course Creator",
  "permlevel": 0,
  "ptype": "Role",
  "read": 1,
  "role": "Course Creator",
  "submit": 0,
  "write": 1,
  "create": 1,
  "delete": 1,
  "export": 0,
  "import": 0,
  "report": 0,
  "amend": 0,
  "share": 0,
  "email": 0,
  "cancel": 0,
  "print": 0
}
```

**Location**: Insert before LMS Student permission (should be around line 423)

---

### Fix #2: Add Course Creator to LMS Enrollment Permissions

**File**: `lms/lms/doctype/lms_enrollment/lms_enrollment.json`

**Add this permission block** (after the Moderator permission):

```json
{
  "docstatus": 0,
  "doctype": "Custom DocPerm",
  "fieldname": null,
  "idx": 3,
  "name": "LMS Enrollment-Course Creator",
  "permlevel": 0,
  "ptype": "Role",
  "read": 1,
  "role": "Course Creator",
  "submit": 0,
  "write": 1,
  "create": 1,
  "delete": 1,
  "export": 0,
  "import": 0,
  "report": 0,
  "amend": 0,
  "share": 0,
  "email": 0,
  "cancel": 0,
  "print": 0
}
```

**Location**: Insert before LMS Student permission (around line 168)

---

### Fix #3: Add Permission Checks to Delete Operations (Security)

**File**: `lms/lms/api.py`

**For `delete_lesson()` (line 472)**:
```python
@frappe.whitelist()
def delete_lesson(lesson, chapter):
    # ✅ ADD PERMISSION CHECK
    if not is_admin_user():
        frappe.throw(_("You do not have permission to delete lessons"))

    # Delete Reference
    chapter = frappe.get_doc("Course Chapter", chapter)
    chapter.lessons = [row for row in chapter.lessons if row.lesson != lesson]
    chapter.save()
    # ... rest of code
```

**For `delete_course()` (line 846)**:
```python
@frappe.whitelist()
def delete_course(course):
    # ✅ ADD PERMISSION CHECK
    if not is_admin_user():
        frappe.throw(_("You do not have permission to delete courses"))

    # ... rest of code
```

**For `delete_batch()` (line 887)**:
```python
@frappe.whitelist()
def delete_batch(batch):
    # ✅ ADD PERMISSION CHECK
    if not is_admin_user():
        frappe.throw(_("You do not have permission to delete batches"))

    # ... rest of code
```

**Helper function to add** (add near line 320 in utils.py or in api.py):
```python
def is_admin_user():
    """Check if user has any admin role"""
    user_roles = frappe.get_roles(frappe.session.user)
    admin_roles = ["System Manager", "Moderator", "Course Creator", "Batch Evaluator"]
    return any(role in user_roles for role in admin_roles)
```

---

## SPECIFIC OPERATIONS & WHAT BLOCKS THEM

### Creating a Course
- **Required Permissions**: LMS Course CRUD
- **Requires Roles**: System Manager OR Moderator OR Course Creator
- **Your Admin**: ✅ HAS ALL - Should work
- **Might be blocked by**: Frontend permission check (but you fixed that already)

### Creating a Batch
- **Required Permissions**: LMS Batch CRUD
- **Requires Roles**: System Manager OR Moderator OR Batch Evaluator
- **Your Admin**: ✅ HAS ALL - Should work
- **Issue**: Course Creator NOT in permissions (not critical for your admin)

### Enrolling Students (Creating LMS Enrollment)
- **Required Permissions**: LMS Enrollment CRUD
- **Requires Roles**: System Manager OR Moderator
- **Your Admin**: ✅ HAS BOTH - Should work
- **Issue**: Course Creator NOT in permissions (not critical for your admin)
- **Alternative**: LMS Batch Enrollment for batch enrollment

### Managing Members/Evaluators
- **Required Permissions**: Access Settings dialog
- **Requires Roles**: Moderator (or System Manager)
- **Your Admin**: ✅ HAS BOTH - Should work
- **Status**: ✅ FIXED (you added System Manager check earlier)

### Deleting Courses/Batches/Lessons
- **Required Permissions**: LMS Course/Batch/Lesson CRUD + Admin check
- **Requires Roles**: System Manager OR Moderator OR Course Creator
- **Your Admin**: ✅ HAS ALL - Should work
- **Issue**: No permission validation in code (relies on DocType rules)
- **Fix**: Add explicit permission checks (Fix #3 above)

---

## TESTING CHECKLIST

Before deploying fixes, test your admin user on these operations:

```
[ ] Create Course
    - Go to Courses page
    - Click Create button
    - Should NOT be redirected
    - Form should load

[ ] Create Batch
    - Go to Batches page
    - Click Create button
    - Should NOT be redirected
    - Form should load

[ ] Enroll Student in Course
    - Go to course detail
    - Click "Manage Members" or enrollment button
    - Should see student list
    - Should be able to add students

[ ] Enroll Student in Batch
    - Go to batch detail
    - Click "Manage Enrollment" or similar
    - Should be able to enroll students

[ ] Manage Instructors
    - Create course
    - Should be able to assign instructors from dropdown
    - (Already fixed this issue)

[ ] Access Settings
    - Click user menu (top right)
    - Should see "Settings" option
    - Should be able to click it
    - (Already fixed this issue)

[ ] Delete Course (if permission check added)
    - Open course
    - Click delete
    - Should succeed (not be blocked by permission check)

[ ] Create Assignment/Lesson/Quiz
    - Should all work
    - No permission checks blocking
```

---

## IMPLEMENTATION ORDER

### Immediate (Required):
1. ✅ Fix #1: Add Course Creator to LMS Batch permissions (lms_batch.json)
2. ✅ Fix #2: Add Course Creator to LMS Enrollment permissions (lms_enrollment.json)

### Short-term (Security):
3. ⚠️ Fix #3: Add permission checks to delete operations (api.py)

### Long-term (Cleanup):
4. Audit all other DocTypes for missing Course Creator permissions
5. Create a helper function `is_admin_user()` for consistent checks
6. Document the permission model

---

## HOW TO VERIFY YOUR ADMIN ROLE SETUP

Go to **Frappe Admin Panel** > **Role**:

1. Find your custom admin role
2. Check "Included Roles" section
3. Verify it includes:
   - [ ] System Manager (or at least Moderator + Batch Evaluator)
   - [ ] Course Creator
   - [ ] Moderator
   - [ ] Batch Evaluator

4. Check custom permissions if defined:
   - [ ] User - FULL CRUD (if managing users)
   - [ ] LMS Course - FULL CRUD
   - [ ] LMS Batch - FULL CRUD
   - [ ] LMS Enrollment - FULL CRUD
   - [ ] LMS Assignment - FULL CRUD

If any are missing, your admin users will be blocked.

---

## FINAL DIAGNOSIS

### Most Likely Issue:
Your admin role setup is incomplete. It might be missing:
1. **System Manager** role (needed for some operations)
2. **Moderator** role (needed for enrollment)
3. **Proper DocType permissions** (if using custom role)

### Most Likely Blockers:
1. Frontend permission checks (✅ ALREADY FIXED)
2. DocType missing Course Creator permission (🚨 UNFIXED)
3. Admin role missing required included roles (🚨 NEEDS VERIFICATION)

### Next Steps:
1. **Tell me**: Which specific operations are failing?
2. **Then**: I'll provide exact code changes to fix them

---

## SIGN-OFF

All potential permission issues have been identified. The fixes are ready to implement once you specify which exact operations are failing for your admin users.

**Status**: ✅ **Analysis Complete - Ready for Targeted Fixes**

