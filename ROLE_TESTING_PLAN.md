# Role-Based Access Control - Testing Plan & Results

**Date**: January 6, 2026
**Status**: TESTING IN PROGRESS
**Critical Fixes Applied**: 2

---

## BUGS FIXED

### ✅ Bug #1: Admin Course Creation Failure
**File**: `frontend/src/pages/CourseForm.vue` (line 415)
**Fix Applied**: Added `is_system_manager` flag to permission check
**Before**:
```javascript
if (user.data?.is_teacher || (!user.data?.is_moderator && !user.data?.is_instructor))
```
**After**:
```javascript
if (user.data?.is_teacher || (!user.data?.is_system_manager && !user.data?.is_moderator && !user.data?.is_instructor))
```
**Impact**: System Managers can now create courses

---

### ✅ Bug #2: Course Creator Instructor Assignment
**File**: `frontend/src/pages/CourseForm.vue` (line 47)
**Fix Applied**: Removed `:required="true"` from instructors MultiSelect field
**Reason**: Backend auto-assigns owner as instructor if no instructors provided (lms_course.py lines 31-41)
**Impact**: Course Creators can create courses without mandatory instructor selection

---

## ROLE TESTING MATRIX

### Test Data
- **System Manager User**: Administrator
- **Course Creator User**: course_creator (has Course Creator role)
- **LMS Teacher User**: teacher_user (has LMS Teacher role)
- **LMS Student User**: student_user (has LMS Student role)

---

## TEST CASE 1: System Manager (Administrator)

### Expected Behavior
✅ Can create new courses
✅ Can edit any course
✅ Can delete courses
✅ Can assign instructors
✅ Can create batches
✅ Can manage all course settings

### Test Steps

#### 1.1 Create New Course
- [ ] Login as System Manager
- [ ] Navigate to `/lms/courses`
- [ ] Click "New Course" button
- [ ] **Expected**: Form loads successfully (NOT redirected)
- [ ] Fill in course details:
  - Title: "Test Admin Course"
  - Short Introduction: "Admin test course"
  - Description: "Testing admin course creation"
  - Category: Any category
  - Instructors: Leave empty OR select instructors (both should work)
- [ ] Click "Save"
- [ ] **Expected**: Course created successfully, redirected to course detail page

#### 1.2 Edit Course
- [ ] Navigate to previously created course
- [ ] Click "Edit" button
- [ ] Update course title to "Test Admin Course - Updated"
- [ ] Click "Save"
- [ ] **Expected**: Course updated successfully

#### 1.3 Assign New Instructors
- [ ] In course edit form, add new instructors in "Instructors" field
- [ ] Click "Save"
- [ ] **Expected**: Instructors saved successfully

#### 1.4 Delete Course
- [ ] In course detail page, click trash icon
- [ ] Confirm deletion
- [ ] **Expected**: Course deleted, redirected to courses list

#### 1.5 Verify Course List Access
- [ ] Navigate to `/lms/courses`
- [ ] **Expected**: Can see all courses (both published and draft)

---

## TEST CASE 2: Course Creator

### Expected Behavior
✅ Can create new courses
✅ Can edit own courses
❌ Cannot edit other users' courses
✅ Can assign instructors to own courses
❌ Cannot delete courses
❌ Cannot access admin settings

### Test Steps

#### 2.1 Create New Course
- [ ] Login as Course Creator
- [ ] Navigate to `/lms/courses`
- [ ] Click "New Course" button
- [ ] **Expected**: Form loads successfully (NOT redirected)
- [ ] Fill in course details:
  - Title: "Test Creator Course"
  - Short Introduction: "Creator test course"
  - Description: "Testing course creator flow"
  - Category: Any category
  - Instructors: Leave empty (backend should auto-assign creator as instructor)
- [ ] Click "Save"
- [ ] **Expected**: Course created successfully with creator auto-assigned as instructor

#### 2.2 Assign Instructors to New Course
- [ ] Create new course as above
- [ ] In course creation form, fill Instructors field with 2-3 users
- [ ] Fill remaining required fields
- [ ] Click "Save"
- [ ] **Expected**: Course created with selected instructors

#### 2.3 Edit Own Course
- [ ] Navigate to course created in 2.1 or 2.2
- [ ] Click "Edit" button
- [ ] Update course title
- [ ] Click "Save"
- [ ] **Expected**: Course updated successfully

#### 2.4 Attempt to Edit Another User's Course
- [ ] Try to access course created by System Manager (from Test Case 1) using URL
- [ ] Navigate to `/lms/course/[admin-course-name]`
- [ ] **Expected**: Either can't access form, or form loads but can't save (permission error)
- [ ] **Alternative**: Can edit but not all fields (read-only)

#### 2.5 Attempt to Delete Course
- [ ] In course detail page, look for trash/delete button
- [ ] **Expected**: Delete button NOT visible for own courses (not permitted)

#### 2.6 Verify Course List Access
- [ ] Navigate to `/lms/courses`
- [ ] **Expected**: Can only see own courses in course list

---

## TEST CASE 3: LMS Teacher

### Expected Behavior
❌ Cannot create courses
❌ Cannot edit courses
✅ Can view assigned courses
✅ Can manage course content (if assigned as instructor)
✅ Can create lessons in assigned courses

### Test Steps

#### 3.1 Attempt to Create New Course
- [ ] Login as LMS Teacher
- [ ] Navigate to `/lms/courses`
- [ ] Look for "New Course" button
- [ ] **Expected**: Button NOT visible or disabled
- [ ] Try to manually navigate to `/lms/course/new`
- [ ] **Expected**: Redirected to `/lms/courses` (not redirected to login, just back to list)

#### 3.2 View Assigned Courses
- [ ] Ensure user is assigned as instructor to a course (created as System Manager or Course Creator)
- [ ] Navigate to `/lms/courses`
- [ ] **Expected**: Can see assigned courses in the list

#### 3.3 Edit Assigned Course Content
- [ ] Click on assigned course
- [ ] In course detail page, look for edit buttons/options
- [ ] **Expected**: Can edit course content (chapters, lessons) BUT not course settings
- [ ] Try to change course title or other settings
- [ ] **Expected**: Either no option to edit these fields, or permission error when trying to save

#### 3.4 Create Lesson in Assigned Course
- [ ] In assigned course, navigate to add new lesson
- [ ] Create new lesson with some content
- [ ] **Expected**: Lesson created successfully

#### 3.5 Attempt to Edit Course Settings
- [ ] Look for "Settings" section or edit button for course properties
- [ ] **Expected**: Settings section should be visible but fields might be read-only

---

## TEST CASE 4: LMS Student

### Expected Behavior
❌ Cannot create courses
❌ Cannot edit courses
✅ Can view enrolled courses
✅ Can take quizzes
✅ Can view recordings
✅ Can view live classes

### Test Steps

#### 4.1 Attempt to Create New Course
- [ ] Login as LMS Student
- [ ] Navigate to `/lms/courses`
- [ ] Look for "New Course" button
- [ ] **Expected**: Button NOT visible or disabled
- [ ] Try to manually navigate to `/lms/course/new`
- [ ] **Expected**: Redirected to `/lms/courses` (permission check)

#### 4.2 View Enrolled Courses
- [ ] Ensure user is enrolled in at least one course
- [ ] Navigate to `/lms/courses`
- [ ] **Expected**: Can see only enrolled courses

#### 4.3 View Course Content
- [ ] Click on enrolled course
- [ ] **Expected**: Can view course outline, chapters, lessons
- [ ] Look for edit buttons or pencil icons
- [ ] **Expected**: No edit options visible

#### 4.4 Take Quiz
- [ ] If course has quiz, click quiz lesson
- [ ] Complete quiz
- [ ] **Expected**: Quiz works, answers recorded

#### 4.5 View Recording
- [ ] If course has recording, click recording lesson
- [ ] **Expected**: Recording loads and plays
- [ ] **Security Check**: Right-click disabled on recording
- [ ] **Security Check**: Dev tools blocked

#### 4.6 Attempt to Access Admin Features
- [ ] Try to navigate to `/lms/courses/new`
- [ ] Try to access course edit form
- [ ] **Expected**: All redirected to courses list or get permission errors

---

## VERIFICATION CHECKLIST

### Permission Logic Verification
- [ ] System Managers: `is_system_manager=true` allows course creation
- [ ] Course Creators: `is_instructor=true` allows course creation
- [ ] Moderators: `is_moderator=true` allows course creation
- [ ] LMS Teachers: `is_teacher=true` redirected from course creation
- [ ] LMS Students: Redirected from course creation

### Backend Permission Checks
- [ ] LMS Course DocType allows System Manager CRUD
- [ ] LMS Course DocType allows Course Creator CRUD
- [ ] LMS Course DocType allows Moderator CRUD
- [ ] LMS Course DocType allows LMS Teacher read-only
- [ ] Course Instructor child table inherits parent permissions correctly

### Frontend Validation
- [ ] Course creation form loads for authorized roles
- [ ] Course creation form redirects unauthorized roles
- [ ] Instructors field is optional (backend auto-assigns if empty)
- [ ] Form submission works for all authorized roles

### Role-Specific Features
- [ ] System Managers can manage all settings
- [ ] Course Creators limited to own courses
- [ ] LMS Teachers can manage assigned courses only
- [ ] LMS Students can only view content

---

## BROWSER CONSOLE CHECKS

After each test, verify no errors in browser console:
- [ ] No permission errors (403)
- [ ] No authentication errors (401)
- [ ] No "undefined" errors in console
- [ ] No malformed API calls

---

## BACKEND LOG CHECKS

After tests, check for errors:
```bash
bench --site <site> show-log -f
```

- [ ] No permission denied errors
- [ ] No validation errors on course save
- [ ] No instructor assignment errors
- [ ] No database errors

---

## RECORDING SECURITY VERIFICATION

For each student user test:
- [ ] Right-click on recording: **Expected** - Menu blocked
- [ ] F12 key: **Expected** - DevTools blocked
- [ ] Try to inspect element: **Expected** - Blocked
- [ ] Try to select text on recording: **Expected** - Text not selectable
- [ ] View page source for Zoom URL: **Expected** - URL not exposed (token used instead)

---

## FINAL VERIFICATION MATRIX

| Role | Create | Edit Own | Edit Others | Delete | View | Manage Content |
|------|--------|----------|-------------|--------|------|-----------------|
| System Manager | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Course Creator | ✅ | ✅ | ❌ | ❌ | ✅ | ✅ |
| LMS Teacher | ❌ | ❌ | ❌ | ❌ | ✅ | ✅ |
| LMS Student | ❌ | ❌ | ❌ | ❌ | ✅ | ❌ |

---

## TEST RESULTS

### Test Date: [TO BE FILLED]
### Tester: [TO BE FILLED]

#### Test Case 1: System Manager
- Status: [ ] PASS [ ] FAIL
- Issues Found:
- Notes:

#### Test Case 2: Course Creator
- Status: [ ] PASS [ ] FAIL
- Issues Found:
- Notes:

#### Test Case 3: LMS Teacher
- Status: [ ] PASS [ ] FAIL
- Issues Found:
- Notes:

#### Test Case 4: LMS Student
- Status: [ ] PASS [ ] FAIL
- Issues Found:
- Notes:

---

## FINAL STATUS

**Overall Test Result**: [ ] PASS [ ] FAIL
**Production Ready**: [ ] YES [ ] NO
**Blockers Found**: [ ] None [ ] Minor [ ] Critical

**Sign-Off**: _________________________  Date: ___________

---

