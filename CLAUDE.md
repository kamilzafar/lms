# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project: Frappe Learning LMS

A full-stack Learning Management System built on Frappe Framework (Python/MySQL) with a Vue.js 3 frontend. Supports courses, batches, live classes (Zoom), assessments, certifications, and job opportunities.

**Stack**: Frappe Framework + Vue 3 + Vite + TailwindCSS + EditorJS

---

## Development Commands

### Backend (Frappe)

```bash
# Start development server (runs on port 8000)
bench start

# Create a new site
bench new-site learning.test

# Install the LMS app
bench --site learning.test install-app lms

# Run migrations after DocType changes
bench --site learning.test migrate

# Access Python console
bench --site learning.test console

# Clear cache
bench --site learning.test clear-cache

# Rebuild DocTypes after JSON changes
bench --site learning.test migrate

# Background worker (required for scheduled jobs and webhooks)
bench worker
```

### Frontend (Vue.js)

```bash
cd frontend

# Install dependencies
yarn install

# Development server (port 8080, proxies to backend on 8000)
yarn dev

# Production build (outputs to ../lms/public/frontend/)
yarn build

# Preview production build
yarn serve
```

**Important**: Add `"ignore_csrf": 1` to `site_config.json` during development to prevent CSRF errors with Vite dev server.

### Docker

```bash
# Start containers
docker compose up -d

# Access at http://lms.localhost:8000/lms
# Default: Administrator / admin
```

### Code Quality

```bash
# Python linting (configured in pyproject.toml)
ruff check lms/

# Python formatting
ruff format lms/
```

---

## Architecture Overview

### Dual-Codebase Structure

**Backend** (`/lms/lms/`): Frappe Framework app
- 67 DocTypes in `/lms/lms/doctype/`
- API endpoints in `/lms/lms/api.py` (115+ methods)
- Server-side logic, database, auth, scheduled jobs

**Frontend** (`/frontend/`): Vue.js 3 SPA
- 42+ pages in `/frontend/src/pages/`
- 54+ components in `/frontend/src/components/`
- Runs at `/lms` base path

### Request Flow

```
Vue Component → Frappe-UI createResource({ url: 'lms.lms.api.method_name' })
  ↓
Backend API (@frappe.whitelist decorator in api.py)
  ↓
DocType Logic (validate, save, custom methods)
  ↓
Database (MySQL/MariaDB)
  ↓
Response → Frontend State Update
```

### Key Integration Points

1. **API Layer**: `/lms/lms/api.py` - All frontend ↔ backend communication
2. **Hooks**: `/lms/hooks.py` - App configuration, scheduled jobs, event handlers
3. **Router**: `/frontend/src/router.js` - SPA routes (base: `/lms`)
4. **DocTypes**: `/lms/lms/doctype/` - Data models with Python controllers

---

## Critical Files Reference

| Purpose | File Path |
|---------|-----------|
| **All API endpoints** | `/lms/lms/api.py` |
| **App configuration & hooks** | `/lms/hooks.py` |
| **Frontend routes** | `/frontend/src/router.js` |
| **Sidebar navigation logic** | `/frontend/src/utils/index.js` (`getSidebarLinks()`) |
| **Main app component** | `/frontend/src/App.vue` |
| **User session store** | `/frontend/src/stores/session.js` |
| **User authentication** | `/lms/lms/user.py` |

---

## Common Development Workflows

### Adding a New API Endpoint

1. **Backend** - Edit `/lms/lms/api.py`:
```python
@frappe.whitelist()
def get_my_data():
    # Your logic here
    return frappe.get_all("DocType Name", filters={...})
```

2. **Frontend** - Use in component:
```javascript
import { createResource } from 'frappe-ui'

const myData = createResource({
    url: 'lms.lms.api.get_my_data',
    auto: true  // Load on mount
})

// Access: myData.data
```

### Adding a New Page

1. **Create component**: `/frontend/src/pages/MyNewPage.vue`
2. **Add route**: `/frontend/src/router.js`
```javascript
{
    path: '/my-new-page',
    name: 'MyNewPage',
    component: () => import('@/pages/MyNewPage.vue')
}
```
3. **Add sidebar link** (optional): `/frontend/src/utils/index.js` in `getSidebarLinks()`

### Modifying a DocType

1. **JSON Schema**: Edit `/lms/lms/doctype/{doctype_name}/{doctype_name}.json`
   - Add/modify fields in `fields` array
   - Update `field_order` list

2. **Python Logic**: Edit `/lms/lms/doctype/{doctype_name}/{doctype_name}.py`
```python
class MyDocType(Document):
    def validate(self):
        # Runs before save
        pass

    def on_update(self):
        # Runs after save
        pass
```

3. **Run migration**: `bench --site learning.test migrate`

### Adding a Scheduled Job

1. **Edit** `/lms/hooks.py`:
```python
scheduler_events = {
    "hourly": [
        "lms.lms.module.my_hourly_task"
    ]
}
```

2. **Create function** in appropriate module
3. **Ensure worker running**: `bench worker`

### Modifying Sidebar Navigation

**File**: `/frontend/src/utils/index.js`

The `getSidebarLinks()` function returns role-based navigation:
- Uses `userResource.data` to check roles (is_instructor, is_moderator, etc.)
- Each link has `condition: () => boolean` for visibility
- Order matters for display

**Example - Hide a sidebar item**:
```javascript
{
    label: 'Statistics',
    condition: () => false  // Always hidden
}
```

---

## Frappe Framework Patterns

### Whitelisted Methods
Only functions with `@frappe.whitelist()` are accessible from frontend:
```python
@frappe.whitelist(allow_guest=True)  # Public
def public_method():
    pass

@frappe.whitelist()  # Requires login
def authenticated_method():
    current_user = frappe.session.user
```

### Database Queries
```python
# Get single value
frappe.db.get_value("DocType", {"field": "value"}, "return_field")

# Get multiple
frappe.get_all("DocType",
    filters={"status": "Active"},
    fields=["name", "title"],
    order_by="creation desc"
)

# Get document
doc = frappe.get_doc("DocType", "name")
doc.field = "new value"
doc.save()
```

### Permissions
- System Roles: `System Manager`, `Moderator`, `Course Creator`, `Batch Evaluator`, `LMS Student`
- Check in code: `if "Moderator" in frappe.get_roles(user):`
- DocType permissions: Defined in DocType JSON under `permissions`

---

## Frontend Patterns

### Frappe-UI Resources
Primary way to fetch data:
```javascript
const courses = createResource({
    url: 'lms.lms.api.get_courses',
    cache: ['courses'],  // Cache key
    auto: true,          // Load immediately
    onSuccess(data) {
        // Handle response
    }
})

// Usage
courses.reload()         // Refetch
courses.data             // Response data
courses.list.loading     // Loading state
```

### Vue Router Navigation
```javascript
import { useRouter } from 'vue-router'
const router = useRouter()

router.push({ name: 'CourseName', params: { id: '123' } })
router.push('/path')
```

### Global Injects
Available in all components:
- `$user` - Current user data and roles
- `$dayjs` - Date/time utility
- `$socket` - Socket.IO instance

---

## Role-Based UI Customization

### User Roles & UI Variations

**Key computed properties** (check in components):
```javascript
const isLMSStudent = computed(() => {
    return user.data && !user.data.is_moderator
        && !user.data.is_instructor && !user.data.is_evaluator
})

const isModerator = computed(() => user.data?.is_moderator)
const isInstructor = computed(() => user.data?.is_instructor)
```

**Role-based UI filtering** (frontend-only, backend unchanged):

1. **Courses page** (`/frontend/src/pages/Courses.vue` lines 362-433):
   - **Administrator** (`is_system_manager`): Sees ALL tabs (Live, New, Upcoming, Enrolled, Created, Unpublished, Teacher of) + all filters + Create button
   - **LMS Students**: See only "Enrolled" and "Live" tabs, no filters, no Create button
   - **Teachers/Moderators**: See only "Teacher of" tab, no filters, no Create button
   - **Instructors/Evaluators**: See full tab list with Create/Unpublished tabs

2. **Sidebar** (`/frontend/src/components/Sidebar/AppSidebar.vue`):
   - Statistics hidden from Students & Teachers
   - Website builder hidden (More section: `v-if="false"`)

3. **Role display mapping** (`/frontend/src/components/Settings/Members.vue:227`):
   - Backend role "Moderator" displays as "Teacher" in UI

**Important**: Administrator role check should always come **first** in role-based conditionals to prevent being treated as other roles.

---

## Important DocTypes

**Core Learning**:
- `LMS Course` - Course structure (has chapters)
- `Course Chapter` - Groups lessons
- `Course Lesson` - Individual lesson (EditorJS content)
- `LMS Enrollment` - Student enrollments
- `LMS Course Progress` - Lesson completion tracking

**Batches**:
- `LMS Batch` - Cohort with schedule
- `LMS Batch Enrollment` - Batch members

**Live Classes**:
- `LMS Live Class` - Zoom meeting metadata
- `LMS Zoom Settings` - OAuth credentials per user
- `LMS Live Class Participant` - Attendance records

**Assessments**:
- `LMS Quiz` / `LMS Quiz Question` / `LMS Quiz Submission`
- `LMS Assignment` / `LMS Assignment Submission`
- `Exercise` / `Exercise Submission` - Programming exercises

**Certification**:
- `LMS Certificate` - Issued certificates
- `LMS Certificate Request` - Paid certificate requests
- `LMS Certificate Evaluation` - Evaluator reviews

---

## Zoom Integration

### OAuth Flow
1. User creates `LMS Zoom Settings` with Client ID/Secret
2. Uses Server-to-Server OAuth (account credentials grant)
3. Function: `authenticate(zoom_account)` in `/lms/lms/doctype/lms_batch/lms_batch.py`

### Live Class Creation
- Creates Zoom meeting via API
- Optionally creates Google Calendar event
- Stores `meeting_id`, `uuid`, `start_url`, `join_url`

### Attendance Tracking
- **Scheduled job**: `update_attendance()` runs hourly
- Fetches participant data from Zoom API
- Creates `LMS Live Class Participant` records

### Recording System (Metadata-Only Architecture)
**Webhook endpoint**: `/api/method/lms.lms.api.zoom_webhook`

**Important**: The system stores only **metadata**, not video files. Recordings remain in Zoom Cloud and are streamed via Zoom's CDN.

**Flow**:
1. Teacher ends meeting with cloud recording enabled (default: "Cloud")
2. Zoom processes recording (5-60 min)
3. Zoom sends `recording.completed` webhook with HMAC-SHA256 signature
4. System verifies signature, extracts metadata only (duration, file size, recording ID, passcode)
5. Stores metadata in `LMS Live Class` DocType
6. Marks `recording_processed = 1`

**Playback Flow**:
1. Student clicks "Watch Recording" on lesson page
2. Frontend calls `lms.lms.api.get_zoom_recording_playback(live_class_name)`
3. Backend verifies student enrollment in batch
4. Fetches fresh `play_url` from Zoom API (valid for limited time)
5. Returns URL + passcode to frontend
6. Frontend embeds Zoom player in iframe

**Files**:
- Webhook handler: `/lms/lms/api.py` (`zoom_webhook()` lines 1960-2154, `verify_zoom_signature()` lines 2156-2180)
- Metadata processor: `/lms/lms/doctype/lms_live_class/lms_live_class.py` (`process_zoom_recording()` lines 168-296)
- Playback API: `/lms/lms/api.py` (`get_zoom_recording_playback()` lines 2184-2340)
- Frontend player: `/frontend/src/components/ZoomRecordingPlayer.vue`

**Fields in `LMS Live Class`**:
- `recording_processed` (Check) - Whether metadata has been extracted
- `zoom_recording_id` (Data) - Zoom recording file ID for API retrieval
- `recording_passcode` (Password) - Passcode for Zoom cloud recording access (encrypted)
- `recording_url` (Data) - Zoom play_url (metadata only, fetched on-demand)
- `recording_duration` (Int) - Duration in seconds
- `recording_file_size` (Int) - Size in bytes

**Configuration**:
- Set webhook URL in Zoom App to `https://yoursite.com/api/method/lms.lms.api.zoom_webhook`
- Add `webhook_secret_token` to `LMS Zoom Settings` for signature verification
- Default `auto_recording` = "Cloud" (set in DocType JSON and frontend modal)

---

## EditorJS Content System

Lessons use EditorJS for rich content editing.

**Content structure** (JSON in `Course Lesson.content` field):
```json
{
    "blocks": [
        {"type": "header", "data": {"text": "Title"}},
        {"type": "paragraph", "data": {"text": "Content"}},
        {"type": "upload", "data": {"file_url": "/files/video.mp4"}},
        {"type": "quiz", "data": {"quiz": "quiz-id"}},
        {"type": "assignment", "data": {"assignment": "assignment-id"}}
    ]
}
```

**Custom blocks**:
- `upload` - Video/file uploads
- `quiz` - Embedded quiz
- `assignment` - Embedded assignment
- `exercise` - Programming exercise

**Adding video programmatically**:
```python
import json
lesson = frappe.get_doc("Course Lesson", lesson_name)
content = json.loads(lesson.content) if lesson.content else {"blocks": []}
content["blocks"].insert(0, {
    "type": "upload",
    "data": {"file_url": file_url, "title": "Recording"}
})
lesson.content = json.dumps(content)
lesson.save(ignore_permissions=True)
```

---

## Background Jobs & Workers

**Requirement**: Run `bench worker` for async tasks to process.

**Queue types**:
- `default` - General background jobs
- `long` - Long-running tasks (recordings, large exports)
- `short` - Quick tasks

**Enqueueing a job**:
```python
frappe.enqueue(
    "lms.module.function_name",
    queue="long",
    timeout=1800,  # 30 minutes
    arg1="value"
)
```

**Scheduled jobs** (defined in `/lms/hooks.py`):
```python
scheduler_events = {
    "hourly": [
        "lms.lms.doctype.lms_live_class.lms_live_class.update_attendance"
    ],
    "daily": [
        "lms.lms.doctype.lms_live_class.lms_live_class.send_live_class_reminder"
    ]
}
```

---

## Testing

### E2E Tests (Cypress)
Location: `/cypress/`

**Note**: Test setup exists but testing strategy not documented in README.

---

## Branding Customization

This instance is customized as "Zensbot LMS":

**Modified files** (frontend only):
- `/frontend/src/components/InstallPrompt.vue` - PWA install text
- `/frontend/src/pages/PersonaForm.vue` - Onboarding copy
- `/frontend/src/components/Modals/EmailTemplateModal.vue` - Email signatures
- `/frontend/src/components/Sidebar/AppSidebar.vue` - Help modal title

**Backend** (`/lms/hooks.py`):
```python
app_name = "ict_lms"
app_title = "ICT LMS"
app_email = "kamil@zensbot.com"
```

---

## Build & Deployment

### Frontend Build Process
```bash
cd frontend
yarn build
```

**What happens**:
1. Vite builds to `/lms/public/frontend/`
2. Copies `index.html` → `/lms/www/lms.html` (Frappe web route)
3. Copies Frappe-UI colors → `/src/utils/frappe-ui-colors.json`

**Production access**: `https://yoursite.com/lms`

### Production Deployment

**Docker** (recommended):
```bash
python3 ./easy-install.py deploy \
    --project=learning_prod \
    --email=admin@example.com \
    --image=ghcr.io/frappe/lms \
    --version=stable \
    --app=lms \
    --sitename=lms.yoursite.com
```

**Bench** (self-hosted):
```bash
bench get-app https://github.com/frappe/lms
bench --site sitename install-app lms
```

---

## File Upload & Storage

**Frappe File System**:
- Public files: `/sites/sitename/public/files/`
- Private files: `/sites/sitename/private/files/`

**Uploading via API**:
```python
from frappe.utils.file_manager import save_file

file_doc = save_file(
    fname="filename.pdf",
    content=file_content,  # bytes
    dt="Course Lesson",    # Attached to doctype
    dn=lesson_name,        # Attached to document
    is_private=1           # Private file
)
# Returns File doctype with file_doc.file_url
```

**Frontend upload**: EditorJS uses custom upload plugin in `/frontend/src/utils/upload.js`

---

## Read-Only Mode

Window variable `window.read_only_mode` disables certain UI elements when true.

**Check in components**:
```javascript
const readOnlyMode = window.read_only_mode
```

Example: `/frontend/src/pages/ProfileRoles.vue` - Disables role checkboxes

---

## Debugging Tips

### Backend Debugging
```python
# Logging
frappe.log_error(title="Error Title", message=str(error))

# Console output
print("Debug:", variable)

# Breakpoint (use with bench console)
import pdb; pdb.set_trace()
```

View logs: Frappe Desk → Error Log DocType

### Frontend Debugging
```javascript
// Console logging
console.log('Debug:', data)

// Vue DevTools (browser extension)
// Inspect component state, Pinia stores, router

// Network tab: Check API responses
```

### Common Issues

**CSRF Token Error**:
- Add `"ignore_csrf": 1` to `site_config.json` for dev

**404 on /lms**:
- Ensure DNS points to server OR add to `/etc/hosts`
- Check `bench start` is running

**Build not reflecting**:
- Clear cache: `bench --site sitename clear-cache`
- Hard refresh browser: Ctrl+Shift+R
- Verify build timestamp: `ls -la lms/public/frontend/`

**Frontend build fails**:
- If `socket.js` import error: File uses default port 8000 (hardcoded, no config import needed)
- If `telemetry.ts` import error: Posthog library loaded from Frappe at runtime (import commented out)
- Run `yarn install` to ensure dependencies are installed

**Webhook not working**:
- Check `bench worker` is running
- Verify webhook secret in LMS Zoom Settings
- Check Error Log for signature validation failures
- Verify webhook URL matches: `/api/method/lms.lms.api.zoom_webhook`

**"Invalid Date" errors in Live Class cards**:
- Ensure date/time fields have null checks before dayjs formatting
- Example: `cls.date ? dayjs(cls.date).format('DD MMMM YYYY') : 'Date not set'`
- Helper functions should return safe defaults when data is missing

---

## Git Workflow

**Main branch**: `main`

**Making changes**:
1. Always use Read tool before editing files
2. Make focused, minimal changes
3. Test locally before committing
4. For DocType JSON changes, run `bench migrate` after commit

**Current customizations** (frontend-only, easily reversible):
- Onboarding disabled
- Website builder hidden
- Role-based Courses page filtering (Administrator sees all tabs)
- "Moderator" → "Teacher" display text
- Zensbot branding
- Default Live Class recording: "Cloud" (backend + frontend)
- Date validation with null safety in Live Class components

---

## External Integrations

### Razorpay (Payments)
- Used for paid certificates and course payments
- Configuration in LMS Settings

### Google Calendar
- Auto-creates events for live classes
- Requires OAuth setup per user
- Integration: `Google Calendar` DocType

### Zoom
- Server-to-Server OAuth (no user interaction)
- Recording webhooks with HMAC-SHA256 signature verification
- Metadata-only storage (videos stay in Zoom Cloud, streamed via CDN)
- Access control: Batch enrollment verification for playback
- Configuration: `LMS Zoom Settings` DocType (multiple accounts supported)
- Default recording mode: "Cloud" (auto-enabled for all new Live Classes)

---

## Performance Considerations

**Caching**:
- Frappe-UI `createResource` supports cache keys
- Backend: `@frappe.cache()` decorator for expensive operations

**Large files**:
- Zoom recordings can exceed 1GB
- Use streaming downloads: `stream=True` in requests
- Background jobs with extended timeout (1800s)

**Database**:
- Index important fields in DocType JSON
- Use `pluck` to fetch single field efficiently
- Avoid N+1 queries (use `get_all` with filters)

---

## Critical Patterns & Best Practices

### Date/Time Handling in Frontend

Always add null checks before formatting dates with dayjs:

```vue
<!-- BAD - Will show "Invalid Date" if data is missing -->
<span>{{ dayjs(cls.date).format('DD MMMM YYYY') }}</span>

<!-- GOOD - Safe with fallback -->
<span>{{ cls.date ? dayjs(cls.date).format('DD MMMM YYYY') : 'Date not set' }}</span>
```

In helper functions, return safe defaults:

```javascript
// BAD - Crashes if date/time are null
const getClassStart = (cls) => {
    return new Date(`${cls.date}T${cls.time}`)
}

// GOOD - Returns safe default
const getClassStart = (cls) => {
    if (!cls.date || !cls.time) return new Date()
    return new Date(`${cls.date}T${cls.time}`)
}
```

### Role-Based UI Conditionals

Always check Administrator **first** to prevent role conflicts:

```javascript
// GOOD - Administrator check comes first
const courseTabs = computed(() => {
    if (user.data?.is_system_manager) {
        return [...allTabs]  // Administrator sees everything
    }
    if (isModerator.value) {
        return [...limitedTabs]  // Moderators see subset
    }
    // ...other roles
})

// BAD - Administrator might be caught by Moderator check
const courseTabs = computed(() => {
    if (isModerator.value) {  // Administrator might also be Moderator!
        return [...limitedTabs]
    }
    if (user.data?.is_system_manager) {
        return [...allTabs]  // Never reached if also Moderator
    }
})
```

### Build Process Resilience

Frontend build should not depend on Frappe runtime files:

```javascript
// BAD - Breaks build if Frappe not running
import { socketio_port } from '../../../../sites/common_site_config.json'

// GOOD - Uses default, loads config at runtime if needed
let socketio_port = 8000  // Default
// Config loaded dynamically at runtime via window variables
```

### Webhook Security

Always verify webhook signatures before processing:

```python
# CRITICAL - Verify before processing
if not verify_zoom_signature(request_body, signature, secret_token):
    frappe.log_error("Invalid Zoom webhook signature")
    return {"status": "error", "message": "Invalid signature"}

# Only process if signature is valid
process_webhook_data(payload)
```

### Scalability Patterns

**Multiple Recordings per Course**: Use separate lessons, not multiple Live Classes per lesson

```
✅ GOOD:
Course → Lesson 1 → Live Class 1
Course → Lesson 2 → Live Class 2
Course → Lesson 3 → Live Class 3

❌ AVOID:
Course → Lesson 1 → Live Class 1, 2, 3  (only 1 shows in UI)
```

**Reason**: Current UI (`lms/lms/utils.py` line 1027) uses `get_value()` which returns only one record. For multiple sessions, create separate lessons.

---

## Support Resources

- **Frappe Docs**: https://frappeframework.com/docs
- **Vue.js Guide**: https://vuejs.org/guide/
- **Frappe-UI**: https://github.com/frappe/frappe-ui (component library)
- **Community**: https://discuss.frappe.io/c/lms/70
- **Telegram**: https://t.me/frappelms

---

*Last updated: December 28, 2024*
