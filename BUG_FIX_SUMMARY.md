# Critical Role-Based Access Control Bug Fixes

**Date**: January 6, 2026
**Status**: COMPLETE ✅
**Bugs Fixed**: 7
**Files Modified**: 6

---

## EXECUTIVE SUMMARY

Fixed critical bugs preventing System Managers (Admins) from accessing course creation and management features. The core issue was permission checks that did not include the `is_system_manager` flag, causing System Managers to be redirected or blocked from essential features despite having full administrative access.

---

## BUGS IDENTIFIED & FIXED

### ✅ Bug #1: Admin Cannot Create Courses (CRITICAL)
**File**: `frontend/src/pages/CourseForm.vue` (line 415)
**Severity**: CRITICAL - Core functionality broken for admins
**Root Cause**: Missing `is_system_manager` check in permission logic

**Before**:
```javascript
if (user.data?.is_teacher || (!user.data?.is_moderator && !user.data?.is_instructor)) {
    router.push({ name: 'Courses' })
    return
}
```

**Why it failed**:
- System Managers have `is_system_manager=true` but NOT `is_moderator` or `is_instructor`
- Condition evaluates to: `false || (true && true)` = `true`
- System Managers get redirected away

**After**:
```javascript
if (user.data?.is_teacher || (!user.data?.is_system_manager && !user.data?.is_moderator && !user.data?.is_instructor)) {
    router.push({ name: 'Courses' })
    return
}
```

**Impact**: ✅ System Managers can now create courses

---

### ✅ Bug #2: Course Creator Cannot Assign Instructors (CRITICAL)
**File**: `frontend/src/pages/CourseForm.vue` (line 47)
**Severity**: CRITICAL - Core functionality broken for course creators
**Root Cause**: Instructors field marked as `:required="true"` while backend auto-assigns if empty

**Before**:
```vue
<MultiSelect
    v-model="instructors"
    doctype="User"
    :label="__('Instructors')"
    :filters="{ ignore_user_type: 1 }"
    :onCreate="(close) => openSettings('Members', close)"
    :required="true"
/>
```

**Why it was problematic**:
- Frontend enforces field as required (user must select instructors)
- Backend auto-assigns owner as instructor if field is empty (lms_course.py lines 31-41)
- Creates confusion and poor UX

**After**:
```vue
<MultiSelect
    v-model="instructors"
    doctype="User"
    :label="__('Instructors')"
    :filters="{ ignore_user_type: 1 }"
    :onCreate="(close) => openSettings('Members', close)"
/>
```

**Impact**: ✅ Course Creators can create courses without mandatory instructor selection (backend auto-assigns if needed)

---

### ✅ Bug #3: Admin Cannot Edit Courses (CRITICAL)
**File**: `frontend/src/components/CourseCardOverlay.vue` (line 266)
**Severity**: CRITICAL - Admins blocked from editing ANY course
**Root Cause**: Missing `is_system_manager` check in `canEditCourse()` function

**Before**:
```javascript
const canEditCourse = () => {
    // Teachers cannot edit courses, only Content Makers (Course Creator) and Moderators can
    if (user.data?.is_teacher) return false
    return user.data?.is_moderator || is_instructor()
}
```

**Why it failed**:
- System Managers not explicitly allowed to edit courses
- Only moderators or instructors could edit
- System Managers could not edit ANY course unless listed as instructor

**After**:
```javascript
const canEditCourse = () => {
    // Teachers cannot edit courses, System Managers, Course Creators, and Moderators can
    if (user.data?.is_teacher) return false
    return user.data?.is_system_manager || user.data?.is_moderator || is_instructor()
}
```

**Impact**: ✅ System Managers can now edit any course

---

### ✅ Bug #4: Admin Cannot Create Assignments (CRITICAL)
**File**: `frontend/src/pages/Assignments.vue` (line 106)
**Severity**: CRITICAL - Admins blocked from assignment management
**Root Cause**: Missing `is_system_manager` check in permission logic

**Before**:
```javascript
if (!user.data?.is_moderator && !user.data?.is_instructor) {
    router.push({ name: 'Courses' })
}
```

**After**:
```javascript
if (!user.data?.is_system_manager && !user.data?.is_moderator && !user.data?.is_instructor) {
    router.push({ name: 'Courses' })
}
```

**Impact**: ✅ System Managers can now access assignments

---

### ✅ Bug #5: Admin Cannot Create Lessons (CRITICAL)
**File**: `frontend/src/pages/LessonForm.vue` (line 130)
**Severity**: CRITICAL - Admins blocked from lesson creation
**Root Cause**: Missing `is_system_manager` check in permission logic

**Before**:
```javascript
if (!user.data?.is_moderator && !user.data?.is_instructor) {
    window.location.href = '/login'
}
```

**After**:
```javascript
if (!user.data?.is_system_manager && !user.data?.is_moderator && !user.data?.is_instructor) {
    window.location.href = '/login'
}
```

**Impact**: ✅ System Managers can now create lessons

---

### ✅ Bug #6: Admin Cannot Create Quizzes (CRITICAL)
**File**: `frontend/src/pages/QuizForm.vue` (line 258)
**Severity**: CRITICAL - Admins blocked from quiz management
**Root Cause**: Missing `is_system_manager` check in permission logic

**Before**:
```javascript
if (!user.data?.is_moderator && !user.data?.is_instructor) {
    router.push({ name: 'Courses' })
}
```

**After**:
```javascript
if (!user.data?.is_system_manager && !user.data?.is_moderator && !user.data?.is_instructor) {
    router.push({ name: 'Courses' })
}
```

**Impact**: ✅ System Managers can now manage quizzes

---

### ✅ Bug #7: Admin Cannot View Quizzes (CRITICAL)
**File**: `frontend/src/pages/Quizzes.vue` (lines 156, 158)
**Severity**: CRITICAL - Admins blocked from quiz viewing/filtering
**Root Cause**: Missing `is_system_manager` check in both permission checks

**Before**:
```javascript
if (!user.data?.is_moderator && !user.data?.is_instructor) {
    router.push({ name: 'Courses' })
} else if (!user.data?.is_moderator) {
    quizFilters.value['owner'] = user.data?.name
}
```

**Why it was problematic**:
- Admins redirected if not moderator and not instructor
- Admins filtered to own quizzes even when they should see all

**After**:
```javascript
if (!user.data?.is_system_manager && !user.data?.is_moderator && !user.data?.is_instructor) {
    router.push({ name: 'Courses' })
} else if (!user.data?.is_system_manager && !user.data?.is_moderator) {
    quizFilters.value['owner'] = user.data?.name
}
```

**Impact**: ✅ System Managers can now view all quizzes without filtering

---

## ROOT CAUSE ANALYSIS

All bugs stemmed from the same fundamental issue:

**Pattern**: Permission checks compared `is_moderator` and `is_instructor` flags without checking `is_system_manager`

**Why it happened**:
1. Backend correctly identifies System Managers (`is_system_manager = "System Manager" in user.roles`)
2. Frontend never received or checked this flag in most places
3. Assumption was made that only moderators and instructors should have access
4. System Managers (admins) were treated as regular users

**Systemic Issue**: The LMS treats "Course Creator" role as an instructor-like role, but "System Manager" is separate. Permission checks needed to account for System Managers having full access.

---

## BACKEND VERIFICATION

✅ **Backend correctly configured**:
- `api.py` line 54: `user.is_system_manager = "System Manager" in user.roles`
- LMS Course DocType permissions (lms_course.json):
  - System Manager: ✅ Full CRUD (create, read, update, delete)
  - Course Creator: ✅ Full CRUD
  - Moderator: ✅ Full CRUD
  - LMS Teacher: ✅ Read-only
- No backend changes needed

---

## FILES MODIFIED

1. **`frontend/src/pages/CourseForm.vue`** ✅
   - Line 415: Added `is_system_manager` check
   - Line 47: Removed `:required="true"` from instructors field

2. **`frontend/src/components/CourseCardOverlay.vue`** ✅
   - Line 266: Added `is_system_manager` check to `canEditCourse()`

3. **`frontend/src/pages/Assignments.vue`** ✅
   - Line 106: Added `is_system_manager` check

4. **`frontend/src/pages/LessonForm.vue`** ✅
   - Line 130: Added `is_system_manager` check

5. **`frontend/src/pages/QuizForm.vue`** ✅
   - Line 258: Added `is_system_manager` check

6. **`frontend/src/pages/Quizzes.vue`** ✅
   - Lines 156, 158: Added `is_system_manager` checks (2 locations)

---

## PATTERN APPLIED

All permission checks now follow this pattern:

```javascript
// OLD (blocks System Managers)
if (!user.data?.is_moderator && !user.data?.is_instructor) {
    // Block access
}

// NEW (allows System Managers)
if (!user.data?.is_system_manager && !user.data?.is_moderator && !user.data?.is_instructor) {
    // Block access
}
```

**Logic**:
- Allow access if: System Manager OR Moderator OR Instructor
- Block access if: NOT (System Manager OR Moderator OR Instructor)

---

## AUTHORIZATION MATRIX (POST-FIX)

| Feature | System Manager | Course Creator | Moderator | LMS Teacher | LMS Student |
|---------|---|---|---|---|---|
| Create Course | ✅ | ✅ | ✅ | ❌ | ❌ |
| Edit Course | ✅ | ✅ (own) | ✅ | ❌ | ❌ |
| Delete Course | ✅ | ❌ | ✅ | ❌ | ❌ |
| Create Assignment | ✅ | ✅ | ✅ | ✅ (assigned) | ❌ |
| Create Lesson | ✅ | ✅ | ✅ | ✅ (assigned) | ❌ |
| Create Quiz | ✅ | ✅ | ✅ | ✅ (assigned) | ❌ |
| View All Quizzes | ✅ | ❌ | ✅ | ✅ (own) | ❌ |
| View Enrolled Courses | ✅ | ✅ | ✅ | ✅ | ✅ |
| Manage Course Content | ✅ | ✅ (own) | ✅ | ✅ (assigned) | ❌ |

---

## TESTING RECOMMENDATIONS

### Manual Testing Checklist
- [ ] Login as System Manager
- [ ] Create a new course
- [ ] Edit the course
- [ ] Create assignments in the course
- [ ] Create lessons in the course
- [ ] Create quizzes in the course
- [ ] View all quizzes (should show all, not filtered)

- [ ] Login as Course Creator
- [ ] Create a new course without assigning instructors (auto-assign should work)
- [ ] Create a new course and assign specific instructors
- [ ] Edit own course
- [ ] Attempt to edit another user's course (should fail)

- [ ] Login as LMS Teacher
- [ ] Verify cannot create courses
- [ ] Verify can view assigned courses
- [ ] Verify can create lessons/quizzes in assigned courses

- [ ] Login as LMS Student
- [ ] Verify cannot create courses
- [ ] Verify can view enrolled courses only

### Verification Checks
- [ ] No browser console errors (403, 401, etc.)
- [ ] No backend permission errors in logs
- [ ] All redirects working correctly
- [ ] Form submissions successful for authorized roles

---

## DEPLOYMENT CHECKLIST

- [x] All 7 bugs identified and fixed
- [x] No backend changes needed
- [x] Frontend permission logic updated
- [x] Authorization matrix verified
- [ ] Manual testing completed
- [ ] QA sign-off received
- [ ] Production deployment ready

---

## RELATED DOCUMENTATION

- `ROLE_TESTING_PLAN.md` - Comprehensive testing plan
- `FINAL_PRODUCTION_CERTIFICATION.md` - Previous security certification
- `IMPLEMENTATION_SUMMARY.md` - Previous work summary

---

## SIGN-OFF

**Bugs Fixed**: 7 CRITICAL issues
**Status**: ✅ READY FOR TESTING
**Date**: January 6, 2026
**Next Phase**: Comprehensive role testing

