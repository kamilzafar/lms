# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

Frappe Learning (LMS) is an open-source Learning Management System built on the Frappe Framework. It features a 3-level course hierarchy (Course → Chapter → Lesson), live Zoom integration, quizzes, assignments, and certificate management. The codebase consists of a Python backend (Frappe DocType models) and a Vue 3 + TypeScript frontend (Vite-based).

## Architecture

### High-Level Structure

```
Frappe Learning = Frappe Framework + Vue 3 Frontend

Backend (Frappe DocTypes):
├── Course (parent) → Chapter (child) → Lesson (nested child)
├── LMS Batch (batch enrollment, timetable, pricing)
├── LMS Live Class (Zoom meetings with automatic recording)
├── Quiz / Assignment / Certificate system
└── Payment gateway integration

Frontend (Vue 3 + Frappe UI):
├── /lms (landing page, course browsing)
├── /courses (user dashboard, course navigation)
├── /course/{id} (course detail with chapter/lesson outline)
├── /course/{id}/{chapter}/{lesson} (lesson viewer with editor content)
└── Admin desk (Frappe's built-in admin interface)
```

### Critical Data Relationships

**3-Level Hierarchy:**
- **LMS Course** (main record)
  - **Chapter Reference** (child table) → links to Course Chapter
    - **Lesson Reference** (child table in Course Chapter) → links to Course Lesson
      - **Course Lesson** (contains content: JSON editor data, YouTube URL, quiz ID, or "live_class:xxx")

**Live Class Recording Flow:**
- **LMS Live Class** (Zoom meeting) → recording arrives via webhook
- **Recording stored as:** lesson.content = "live_class:{live_class_id}"
- **Rendered in frontend:** ZoomRecordingEmbed component detects prefix and embeds via backend proxy

**Access Control:**
- Batch → Enrollment (students per batch)
- Course → Enrollment (direct course registration)
- Instructor assignment via Course Instructor table
- Role-based: System Manager, LMS Admin, Moderator, Course Creator, LMS Teacher, LMS Student

### Key Directories

**Backend:**
- `lms/lms/` - Core app module
  - `api.py` - REST endpoints for frontend (lessons, recordings, quizzes, etc.)
  - `utils.py` - Shared utilities (get_course_outline, access checks, etc.)
  - `doctype/` - Frappe DocType definitions (20+ business models)
  - `page/` - Web template pages
- `lms/lms/lms/` - Internal LMS namespace (mirrors doctype structure)

**Frontend:**
- `frontend/src/pages/` - Route-mapped Vue components (Lesson, CourseDetail, Quiz, etc.)
- `frontend/src/components/` - Reusable Vue components (CourseOutline, ZoomRecordingEmbed, etc.)
- `frontend/src/stores/` - Pinia state management (session, user, sidebar)
- `frontend/src/utils/` - Frontend utilities (compose functions, API helpers)

### Frontend Routing

Base: `/lms/` (defined in `frontend/src/router.js`)

Key routes:
- `/lms` - Home/landing
- `/lms/courses` - User dashboard
- `/lms/course/{courseName}` - Course detail
- `/lms/course/{courseName}/{chapterNumber}/{lessonNumber}` - Lesson viewer
- `/lms/batch/{batchName}` - Batch detail
- `/lms/profile` - User profile

## Development Setup

### Prerequisites

- **Backend:** Frappe bench environment (Python 3.11+, MariaDB/PostgreSQL)
- **Frontend:** Node 16+, Yarn

### Running Locally

**Backend:**
```bash
# Assume you have a bench installation at ~/frappe-bench
cd ~/frappe-bench

# Start dev server (runs on port 8000)
bench start

# In another terminal, run site-specific tasks
bench --site lms.test install-app lms
```

**Frontend (development with hot reload):**
```bash
cd lms/frontend

# Install dependencies
yarn install

# Start Vite dev server (port 8080, proxies to bench on 8000)
yarn dev

# Open http://lms.test:8080 in browser
```

**Frontend (production build):**
```bash
cd lms/frontend

# Build (output to ../lms/public/frontend/)
yarn build

# The build runs:
# 1. vite build --base=/assets/lms/frontend/
# 2. Copies index.html to ../lms/www/lms.html
# 3. Copies Frappe UI colors JSON for Tailwind
```

### Running Tests

**E2E Tests (Cypress):**
```bash
# Run tests in headless mode
npm run test-local  # Opens interactive Cypress GUI

# Tests located in: root of repo (look for cypress.config.js)
```

**Python Tests:**
```bash
# Run LMS-specific tests
bench --site lms.test run-tests --app lms

# Run single test file
bench --site lms.test run-tests --module lms.lms.doctype.course_lesson.test_course_lesson
```

## Common Development Tasks

### Adding a New API Endpoint

1. Add function to `lms/lms/api.py`
2. Decorate with `@frappe.whitelist()` (if authenticated) or `@frappe.whitelist(allow_guest=True)` (public)
3. Call from frontend via `call()` from frappe-ui: `call('lms.lms.api.your_function', {params})`

Example:
```python
@frappe.whitelist()
def get_recording_embed_url(live_class):
    """Docstring for clarity"""
    if frappe.session.user == "Guest":
        frappe.throw(_("Please login"))
    # ... implementation
    return {"token": "...", "recording_available": True}
```

### Modifying the Course Structure

Core DocTypes (don't modify without understanding implications):
- **LMS Course** - Main course record
- **Course Chapter** - Chapter within course
- **Course Lesson** - Individual lesson (contains content)
- **Chapter Reference** - Junction table (Course → Chapters)
- **Lesson Reference** - Junction table (Chapter → Lessons)

When adding fields to lessons:
1. Edit DocType via Frappe desk or JSON file in `doctype/course_lesson/course_lesson.json`
2. Run `bench migrate` to sync database
3. Update frontend components that display lessons (usually `CourseOutline.vue`, `Lesson.vue`)

### Adding a Frontend Component

1. Create `.vue` file in `frontend/src/components/`
2. Use Vue 3 `<script setup>` syntax (preferred)
3. Import from `frappe-ui` for UI components (Button, Input, Dialog, etc.)
4. Use Tailwind CSS classes (not scoped CSS) for styling
5. Use `lucide-vue-next` for icons

Example:
```vue
<template>
  <div class="p-4">
    <Button @click="handleClick">
      {{ __('Click me') }}
    </Button>
  </div>
</template>

<script setup>
import { Button } from 'frappe-ui'
import { ref } from 'vue'

const count = ref(0)
const handleClick = () => count.value++
</script>
```

### Working with Recordings (Zoom Integration)

**Flow:**
1. Zoom webhook → `zoom_webhook_n8n()` in `api.py` receives recording
2. Webhook extracts meeting ID, recording URL, password
3. Embeds password in URL (prevents Zoom from asking user for passcode)
4. Updates LMS Live Class with recording_url and recording_available=1
5. Triggers `create_lesson_from_recording()` which:
   - Creates/finds "Recordings" chapter in course
   - Creates Course Lesson with content="live_class:{live_class_id}"
   - Appends Lesson Reference to chapter
6. Frontend displays lesson with ZoomRecordingEmbed component
7. Component calls `get_recording_embed_url()` to get secure token
8. Backend proxy (`get_recording_secure()`) serves recording securely

**Key functions in `lms/lms/api.py`:**
- `zoom_webhook_n8n()` - Receives webhook from n8n
- `_handle_recording_event()` - Processes recording completion
- `create_lesson_from_recording()` - Creates lesson with recording
- `get_recording_embed_url()` - Returns secure token for frontend
- `get_recording_secure()` - Backend proxy that serves recording

**Frontend components:**
- `ZoomRecordingEmbed.vue` - Renders iframe with secure token
- `Lesson.vue` - Detects "live_class:" prefix and renders ZoomRecordingEmbed

### Fixing JSON Parsing Errors in Lesson.vue

**Issue:** Code tries to JSON.parse lesson.content without checking if it's a recording ("live_class:xxx")

**Solution:** Check prefix before parsing:
```javascript
if (data.content && !data.content.startsWith('live_class:')) {
    editor.value = renderEditor('editor', data.content)
}
```

Apply similar checks to:
- `checkIfDiscussionsAllowed()` - Skip JSON parsing for recordings
- Instructor content validation - Use `isValidJSON()` helper before parsing

## Important Implementation Details

### Recording Lesson Storage

Recording lessons store content differently than normal lessons:
- **Normal lesson:** `content` = Editor.js JSON (for Frappe's RichText editor)
- **Recording lesson:** `content` = `"live_class:{live_class_id}"` (plain string)

Frontend detects this with: `lesson.data.content.startsWith('live_class:')`

### Lesson Icon Detection

Function `get_lesson_icon()` in `utils.py` determines icon based on content:
- Recording lesson (content starts with "live_class:") → "icon-youtube"
- Video/media upload → "icon-youtube"
- Quiz → "icon-quiz"
- Text-only → "icon-list"

Frontend displays appropriate icon in CourseOutline.

### Access Control Layers

**Multiple verification points prevent unauthorized access:**
1. `get_recording_embed_url()` - Validates user enrollment/role
2. Token generation + cache storage
3. `get_recording_secure()` - Re-validates token and access before serving
4. Frontend never sees actual Zoom URL (only secure token)

### Password Handling in Recording URLs

Password embedded in 3 stages for redundancy:
1. **Webhook stage** (primary) - `_handle_recording_event()` embeds password immediately
2. **Direct API fetch** (backup) - `fetch_recording()` embeds if not already present
3. **Display stage** (fallback) - `get_recording_secure()` as final safety net

Uses `urllib.parse.quote()` for proper URL encoding of special characters.

## Important Gotchas

### Child Table Operations

When working with child tables (Lesson Reference, Chapter Reference):
- **Correct:** Use `.append()` method, then `.save()`
- **Incorrect:** Creating separate document and calling `.insert()` (breaks relationships)

Example:
```python
# CORRECT
chapter_doc = frappe.get_doc("Course Chapter", chapter_name)
chapter_doc.append("lessons", {
    "lesson": lesson.name,
    "idx": idx,
})
chapter_doc.save(ignore_permissions=True)

# WRONG - Don't do this for child tables
lesson_ref = frappe.new_doc("Lesson Reference")
lesson_ref.insert()  # Creates orphaned record
```

### Frontend Content Types

Lesson content can be multiple types - check type before processing:
- `content` = Editor.js JSON string (parse with `JSON.parse()`)
- `content` = `"live_class:xxx"` (don't parse, extract ID)
- `body` = HTML/markdown (render directly)
- `youtube` = YouTube URL
- `quiz_id` = Quiz ID

Always check `content.startsWith()` before attempting JSON parse.

### Frappe UI vs Regular Vue Components

- Use components from `frappe-ui` (Button, Input, Dialog, etc.) for consistency
- Use `lucide-vue-next` for icons (integrates with Frappe UI)
- Custom components in `frontend/src/components/` should follow same patterns

## Build and Deploy

### Frontend Build Process

```bash
cd frontend
yarn build

# Creates:
# - ../lms/public/frontend/  (static assets)
# - ../lms/www/lms.html      (entry point for Frappe)
```

The build output is served by Frappe:
- `https://your-site/assets/lms/frontend/` (JS/CSS bundles)
- `https://your-site/lms` (entry point HTML)

### Deployment Considerations

- **CSRF protection:** Set `ignore_csrf: 1` in site_config.json for dev; production handles this automatically
- **API access:** Frontend calls backend via `/api/method/` endpoint
- **Authentication:** Sessions managed by Frappe; token stored in browser
- **Recording security:** Zoom URLs never exposed to frontend; only tokens passed

## Logging and Debugging

### Backend Logging

Use frappe logger throughout code:
```python
frappe.logger().info(f"[Module Name] Message: {variable}")
frappe.logger().error(f"[Module Name] Error: {str(e)}")
```

Key logged components:
- `[Recording Embed]` - Recording access flow
- `[Zoom Webhook]` - Recording webhook processing
- `[Recording Fetch]` - Direct Zoom API calls
- `[Recording Lesson]` - Lesson creation from recordings

View logs:
```bash
bench --site lms.test show-log -f
```

### Frontend Logging

Use browser console for debugging:
```javascript
console.log('[ComponentName] message:', data)
console.error('Error in function:', error)
```

Key log messages:
- `[ZoomRecordingEmbed] API response:` - Recording embed API call
- `[Lesson] loading lesson data` - Lesson page initialization

## Related Documentation

Comprehensive guides in repo root:
- `ZOOM_RECORDING_EMBEDDING_CHECKLIST.md` - Complete verification of recording flow
- `SECURE_RECORDING_IMPLEMENTATION.md` - Security architecture for recordings
- `README.md` - General project overview

## Contribution Guidelines

- Follow semantic commit messages (fix: ..., feat: ..., refactor: ...)
- Test changes locally before committing
- For recording features, ensure multi-layer security is maintained
- Update CLAUDE.md if adding new significant architecture patterns
