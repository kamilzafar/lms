# Admin Permission Blocking Diagnostic Report

**Date**: January 6, 2026
**Issue**: Custom admin role (with ALL available roles) cannot perform admin operations
**Status**: Diagnostic & Investigation

---

## CRITICAL FINDING: Missing Permission Checks

The LMS has **ZERO permission validation** for these critical admin operations:

### Completely Open Functions (NO PERMISSION CHECKS)

| Function | File | Line | Operation | Security Risk |
|----------|------|------|-----------|---|
| `delete_lesson()` | api.py | 472-483 | Delete lesson from course | **CRITICAL** - Any user can delete any lesson |
| `delete_course()` | api.py | 846-884 | Delete entire course with all data | **CRITICAL** - Any user can delete any course |
| `delete_batch()` | api.py | 887-895 | Delete batch with enrollments | **CRITICAL** - Any user can delete any batch |
| `update_sidebar_item()` | api.py | 441-456 | Modify LMS system settings | **CRITICAL** - Any user can modify settings |
| `delete_sidebar_item()` | api.py | 459-469 | Delete system configuration | **CRITICAL** - Any user can delete settings |

---

## Understanding Your Custom Admin Role

You created an admin role by combining **ALL available roles**:

```
Custom Admin Role = System Manager + Course Creator + Moderator + Batch Evaluator + LMS Teacher + LMS Student
```

### The Problem

Even though your admin user has ALL these roles, they may be **blocked by**:

1. **Frontend permission checks** - Components that hide features based on specific role checks
2. **Incomplete permission logic** - Code using wrong operators (AND vs OR)
3. **Frappe DocType permissions** - Database-level permissions that don't account for "all roles"
4. **Missing permission validation** - APIs with zero checks getting blocked by Frappe's default permission system

---

## Locations That Might Block Your Admin

### 1. **Assignment Creation Blocking**
**File**: `lms/lms/doctype/lms_assignment/lms_assignment.py` (Lines 15-26)

```python
@frappe.whitelist()
def save_assignment(assignment, title, type, question):
    if not has_moderator_role() or not has_course_instructor_role():
        return
```

**The Bug**: Uses `or` instead of `and`
- **Current Logic**: Blocks if user is MISSING either Moderator OR Course Instructor role
- **Interpretation**: "Block if NOT moderator OR NOT instructor" = "Block if missing ANY admin role"
- **Impact**: Your admin user with ALL roles will PASS this check ✅

**Status**: ❌ Will NOT block your admin, but logic is backwards

---

### 2. **Batch Enrollment Restriction**
**File**: `lms/lms/doctype/lms_batch_enrollment/lms_batch_enrollment.py` (Lines 25-31)

```python
def validate_owner(self):
    roles = frappe.get_roles(self.owner)
    if "Moderator" not in roles and "Batch Evaluator" not in roles:
        frappe.throw(_("You must be a Moderator or Batch Evaluator..."))
```

**The Issue**: Only checks for Moderator or Batch Evaluator, NOT Course Creator
- **Your Admin**: Has both Moderator AND Batch Evaluator ✅

**Status**: ❌ Will NOT block your admin

---

### 3. **Frontend - BatchForm Component Blocking**
**File**: `frontend/src/pages/BatchForm.vue` (Lines 414-424)

```javascript
const canManageBatch = (
    user.data?.is_system_manager ||
    user.data?.is_instructor ||
    user.data?.is_moderator ||
    user.data?.is_evaluator
)

if (user.data?.is_teacher && !canManageBatch) {
    router.push({ name: 'Batches' })
}
if (!canManageBatch) {
    router.push({ name: 'Batches' })
}
```

**The Issue**: Checks for specific role flags in the USER OBJECT:
- `is_system_manager` - Set if "System Manager" in user roles ✅
- `is_instructor` - Set if "Course Creator" in user roles ✅
- `is_moderator` - Set if "Moderator" in user roles ✅
- `is_evaluator` - Set if "Batch Evaluator" in user roles ✅

**Your Admin**: Should have all 4 flags = TRUE ✅

**Status**: ❌ Will NOT block your admin

---

### 4. **Frontend - Settings Access**
**File**: `frontend/src/components/Sidebar/UserDropdown.vue` (Line 61)

```vue
<SettingsModal v-if="userResource.data?.is_moderator" ... />
```

**The Issue**: Only checks `is_moderator`, missing `is_system_manager`
- **Your Admin**: Has `is_moderator = true` ✅

**Status**: ❌ Will NOT block your admin (has moderator role)

**But**: You previously fixed this to also check `is_system_manager` ✅

---

### 5. **DocType Permission Rules - Most Likely Culprit**

DocTypes define **database-level permissions** that Frappe enforces:

#### LMS Course Permissions
**File**: `lms/lms/doctype/lms_course/lms_course.json`

Defined permissions:
```
✅ System Manager - FULL CRUD (create, read, write, delete, import)
✅ Course Creator - FULL CRUD
✅ Moderator - FULL CRUD
❌ LMS Teacher - Read-only (NO create, NO write, NO delete)
```

**Your Admin**: Has System Manager + Course Creator + Moderator ✅

---

#### LMS Batch Permissions
**File**: `lms/lms/doctype/lms_batch/lms_batch.json`

Defined permissions:
```
✅ System Manager - FULL CRUD
✅ Moderator - FULL CRUD
✅ Batch Evaluator - FULL CRUD
❌ Course Creator - NO ENTRY (might be implicitly denied!)
❌ LMS Student - Read-only
❌ LMS Teacher - Read-only
```

**🚨 CRITICAL**: Course Creator is NOT listed!
- If your admin only has Course Creator role, they CANNOT create batches
- **Your Admin**: Has System Manager + Moderator + Batch Evaluator ✅ (should work)

---

#### LMS Assignment Permissions
**File**: `lms/lms/doctype/lms_assignment/lms_assignment.json`

Defined permissions:
```
✅ System Manager - FULL CRUD
✅ Moderator - FULL CRUD
✅ Course Creator - FULL CRUD
✅ Batch Evaluator - FULL CRUD
❌ LMS Student - Read-only
```

**Your Admin**: Has all admin roles ✅

---

### 6. **Student/Teacher Management**

The LMS doesn't have dedicated "Student Management" or "Teacher Management" UI. These are managed through:

**Creating Users**: This is a Frappe operation, not LMS-specific
- Requires "User" DocType permissions
- Typically requires System Manager role or custom role with User CRUD
- **Check**: Does your admin role have User DocType permissions?

**Assigning to Courses**: Done through:
- **LMS Enrollment** (for students)
- **Course Instructor** table (for teachers/instructors)
- Uses LMS Course/Batch permissions (see above)

---

## DIAGNOSIS: What's Likely Blocking You

Based on the code analysis, your admin users might be blocked by:

### ✅ NOT Blocked By:
- ❌ `delete_course()` - Has NO permission checks (completely open)
- ❌ `delete_batch()` - Has NO permission checks (completely open)
- ❌ `delete_lesson()` - Has NO permission checks (completely open)
- ❌ Role-based frontend checks (all check for roles your admin has)

### 🚨 POSSIBLY Blocked By:
- **Frappe User DocType Permissions** - If your admin role doesn't have User CRUD permissions
- **LMS Batch creation** - If Course Creator role missing from batch permissions
- **DocType-level permission denials** - If your role combination contradicts itself

### ✅ NOT An Issue:
- LMS Course CRUD - Admin has all required roles
- LMS Assignment CRUD - Admin has all required roles
- Settings access - Already fixed to allow System Manager

---

## IMMEDIATE DIAGNOSTIC STEPS

### Step 1: Verify Admin Role Configuration
```
Go to: Admin > Role > Your Custom Admin Role
Check that it has these permissions:
  - System Manager: Full access to all DocTypes
  - Course Creator: Create/Read/Write/Delete for LMS Course, Assignment, Lesson, Quiz
  - Moderator: Full LMS access
  - Batch Evaluator: Full batch management
  - User CRUD: Create/Read/Write/Delete for User DocType
```

### Step 2: Test Each Operation
```
1. Create Course:
   - Frontend: Should see "Create Course" button
   - Backend: Check if succeeds or shows permission error

2. Delete Course:
   - Frontend: Should see delete option
   - Backend: Should succeed (NO permission checks in delete_course())

3. Create Batch:
   - Frontend: Should see "Create Batch" button
   - Backend: Check LMS Batch permissions (Course Creator might be missing)

4. Manage Students:
   - Enroll in course: Uses LMS Enrollment DocType
   - Enroll in batch: Uses LMS Batch Enrollment DocType
   - Check if "create" button appears in UI

5. Manage Teachers:
   - Assign to course: Uses Course Instructor table
   - Assign to batch: Uses Instructor field in LMS Batch
   - Check if dropdown shows users
```

### Step 3: Check Frappe Permission System
```
The issue might be in Frappe's role/permission system, not LMS.

Check:
1. Does your admin role have "System Manager" role included?
   - Yes: Should have access to everything
   - No: Might be blocked from User management, role assignment, etc.

2. Does your admin role have explicit permissions for:
   - User (to create/edit/delete users)
   - LMS Course (to create/edit/delete courses)
   - LMS Batch (to create/edit/delete batches)
   - LMS Enrollment (to enroll students)
```

---

## RECOMMENDED FIX

### Phase 1: Ensure Admin Role Has Full Permissions

Add this to your admin role:

```
Role: YourCustomAdminRole

Included Roles:
  ✅ System Manager (gives full Frappe access)
  ✅ Course Creator
  ✅ Moderator
  ✅ Batch Evaluator

Custom Permissions (if not covered by above):
  ✅ User - FULL CRUD
  ✅ Role - READ
  ✅ LMS Course - FULL CRUD
  ✅ LMS Batch - FULL CRUD
  ✅ LMS Assignment - FULL CRUD
  ✅ LMS Enrollment - FULL CRUD
```

### Phase 2: Fix LMS Batch Permissions

Add Course Creator to batch permissions:

**File**: `lms/lms/doctype/lms_batch/lms_batch.json`

```json
{
  "role": "Course Creator",
  "create": 1,
  "read": 1,
  "write": 1,
  "delete": 1,
  "import": 0,
  "export": 0,
  "report": 0,
  "share": 0,
  "submit": 0,
  "amend": 0,
  "print": 0,
  "email": 0,
  "cancel": 0
}
```

---

## TESTING MATRIX

| Operation | Your Admin | Status | Fix Needed |
|-----------|---|---|---|
| Create Course | All roles | ✅ | No |
| Edit Course | All roles | ✅ | No |
| Delete Course | No checks | ✅ | No |
| Create Batch | System Manager, Moderator, Batch Evaluator | ⚠️ | Maybe |
| Edit Batch | System Manager, Moderator, Batch Evaluator | ✅ | No |
| Delete Batch | No checks | ✅ | No |
| Create Assignment | All roles | ✅ | No |
| Create Lesson | All roles | ✅ | No |
| Create Quiz | All roles | ✅ | No |
| Enroll Student | LMS Enrollment perms | ⚠️ | Check |
| Assign Teacher | Course Instructor perms | ✅ | No |
| Manage Members | Settings dialog | ✅ | Fixed |
| Manage Evaluators | Settings dialog | ✅ | Fixed |
| Manage Categories | Settings dialog | ✅ | Fixed |

---

## NEXT STEPS

1. **Tell me exactly which operations are failing:**
   - Example: "Admin cannot create course" or "Admin cannot enroll students"
   - What error message do you see? (Permission denied? Not visible?)

2. **Then I can:**
   - Check the specific code path for that operation
   - Identify exactly what's blocking it
   - Provide targeted fix

3. **Possible fixes:**
   - Add missing role to DocType permissions
   - Fix permission check logic
   - Add admin user check to frontend/backend
   - Ensure admin role includes System Manager or all necessary roles

---

## SIGN-OFF

**Status**: Ready for specific issue identification
**Next**: Please tell me which specific admin operations are failing, and I'll provide targeted fixes.

