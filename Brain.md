# Brain.md - Frappe Learning LMS Project

## Project Overview
**Frappe Learning (ICT LMS)** - A full-stack Learning Management System for creating and delivering online courses, batches, and certifications.

- **License**: AGPL-3.0
- **Type**: Open-source LMS built on Frappe Framework
- **Purpose**: Enable instructors to create courses, manage batches, conduct live classes, issue certificates, and facilitate job placements

---

## Tech Stack

### Backend
- **Framework**: Frappe Framework (Python 3.10+)
- **Database**: MySQL/InnoDB (SQLite supported)
- **Server**: Gunicorn/WSGI
- **Real-time**: Socket.IO
- **Payment**: Razorpay integration

### Frontend
- **Framework**: Vue.js 3.5+
- **Build Tool**: Vite 5.0
- **UI Library**: Frappe-UI (0.1.227)
- **Router**: Vue Router 4.2
- **State**: Pinia 2.0
- **Styling**: TailwindCSS 3.4
- **Rich Editor**: EditorJS 2.29
- **Code Editor**: CodeMirror 6.0
- **Video Player**: Plyr 3.7
- **Charts**: ApexCharts, Chart.js

### Key Dependencies
- **Day.js** - Date handling
- **Socket.IO Client** - Real-time communication
- **Cypress** - E2E testing

---

## Project Structure

```
/lms/
├── frontend/                    # Vue.js SPA
│   ├── src/
│   │   ├── pages/              # 42+ page components
│   │   ├── components/         # 54+ reusable components
│   │   ├── stores/             # Pinia stores (user, session, settings)
│   │   ├── utils/              # Utility functions & composables
│   │   ├── router.js           # Route definitions
│   │   └── main.js             # App entry point
│   ├── vite.config.js
│   └── package.json
│
├── lms/                         # Frappe app directory
│   ├── lms/
│   │   ├── doctype/            # 67 DocType definitions
│   │   ├── api.py              # 115+ whitelisted API endpoints ⭐
│   │   ├── user.py             # Authentication & user management
│   │   ├── utils.py            # Shared utilities
│   │   ├── web_template/       # 5 web templates (disabled in UI)
│   │   ├── widgets.py          # HTML widget system
│   │   └── www/                # Web pages
│   ├── hooks.py                # Frappe app configuration ⭐
│   ├── install.py              # Installation & setup
│   └── patches/                # Database migrations
│
├── cypress/                     # E2E tests
├── docker/                      # Docker setup
└── pyproject.toml              # Python dependencies
```

---

## Core Features

### 1. Learning Content
- **Courses**: Hierarchical structure (Course > Chapter > Lesson)
- **Rich Content**: EditorJS, markdown macros
- **SCORM**: Package support
- **Videos**: YouTube embedding, watch duration tracking

### 2. Batches (Cohorts)
- Student grouping by course and schedule
- Seat management and capacity limits
- Batch-specific assessments and feedback

### 3. Live Classes
- **Zoom Integration**: Automatic meeting creation
- **Google Calendar Sync**: Event scheduling
- **Attendance Tracking**: Auto-updates from Zoom
- **Timezone Support**: Recently added (Karachi, etc.)

### 4. Assessments
- **Quizzes**: Multiple choice, open-ended questions
- **Programming Exercises**: Code execution with test cases
- **Assignments**: PDF/document submissions
- **Auto-grading**: For objective questions

### 5. Certification
- Certificate templates (default + custom)
- Automated issuance on completion
- Paid certificates with evaluator review
- Public certificate sharing

### 6. Job Opportunities
- Job posting and application system
- Company website links
- Application tracking

### 7. User Management
- **Roles**: Course Creator, Batch Evaluator, Moderator, LMS Student
- **Profiles**: Public profiles with achievements
- **Gamification**: Badges, streaks, activity heatmaps

---

## Key Architecture Patterns

### Data Flow
```
Frontend (Vue) → API Call (Frappe-UI createResource)
  → Backend API (api.py @frappe.whitelist)
  → DocType Methods (validate, save, hooks)
  → Database (MySQL)
  → Real-time Update (Socket.IO)
  → Frontend Update
```

### Important Files

| Purpose | File Path |
|---------|-----------|
| **All API endpoints** | `/lms/lms/api.py` ⭐ |
| **App configuration** | `/lms/hooks.py` |
| **User auth** | `/lms/lms/user.py` |
| **Frontend router** | `/frontend/src/router.js` |
| **Main Vue app** | `/frontend/src/App.vue` |
| **Home page** | `/frontend/src/pages/Home/Home.vue` |
| **Sidebar** | `/frontend/src/components/Sidebar/AppSidebar.vue` |

### DocTypes (Data Models)
67 DocTypes in `/lms/lms/doctype/`, key ones:
- `LMS Course` - Course definition
- `LMS Batch` - Batch/cohort
- `LMS Enrollment` - Student enrollments
- `LMS Live Class` - Zoom meetings
- `LMS Quiz` / `LMS Assignment` - Assessments
- `LMS Certificate` - Issued certificates
- `LMS Course Progress` - Lesson completion tracking

---

## Routes & Navigation

### Frontend Routes (~45 routes)
- `/` - Home (StudentHome or AdminHome based on role)
- `/courses` - Browse courses
- `/courses/:courseName` - Course detail
- `/courses/:courseName/learn/:chapterNumber-:lessonNumber` - Lesson view
- `/batches` - List batches
- `/batches/:batchName` - Batch detail
- `/quizzes`, `/assignments`, `/programming-exercises` - Assessments
- `/user/:username` - User profile
- `/job-openings` - Job opportunities
- `/notifications` - User notifications

**Base Path**: `/lms`

---

## Authentication & Authorization

### Session-Based Auth
- Frappe Framework handles sessions
- Website Users (students) vs System Users (admin/instructors)

### 4 Core Roles
1. **Course Creator** - Create/edit courses
2. **Batch Evaluator** - Grade assignments, issue certificates
3. **Moderator** - Full admin access
4. **LMS Student** - Default for enrolled users

### Permission Checks
- `@frappe.whitelist()` - Expose API to frontend
- Document-level permissions via DocPerm
- Owner-based checks in API methods

---

## Scheduled Jobs (Automated Tasks)

Defined in `/lms/hooks.py`:

**Hourly**:
- `schedule_evals()` - Schedule evaluations
- `update_course_statistics()` - Update enrollment counts
- `update_attendance()` - Sync Zoom attendance

**Daily**:
- `send_payment_reminder()` - Payment notifications
- `send_batch_start_reminder()` - Batch notifications
- `send_live_class_reminder()` - Class reminders

---

## Recent Changes (Last 5 Commits)

```
fb2e8c3 - update live class modal (Dec 26)
d36b73f - Refactor Home.vue admin logic and remove tabs (Dec 26)
fc00ed5 - Update LMS Home (Dec 26)
dbe9ca7 - Explicitly map form values in createLiveClass resource (Dec 26)
bfcb69a - update the error (Dec 26)
```

**Focus**: Live class UI improvements, timezone support, home page refactoring

---

## Common Development Tasks

### Add New API Endpoint
1. Edit `/lms/lms/api.py`
2. Add function with `@frappe.whitelist()` decorator
3. Use in frontend via `createResource({ url: 'lms.lms.api.function_name' })`

### Add New Page
1. Create component in `/frontend/src/pages/`
2. Add route in `/frontend/src/router.js`
3. Add sidebar link in `/frontend/src/utils/index.js` (`getSidebarLinks()`)

### Modify DocType Logic
1. Edit `/lms/lms/doctype/{doctype_name}/{doctype_name}.py`
2. Override methods: `validate()`, `before_save()`, `on_update()`, etc.

### Add Scheduled Task
1. Edit `/lms/hooks.py`
2. Add to `scheduler_events` dict
3. Create function in appropriate module

---

## Disabled Features

### Frontend-Only Disabled (UI Hidden, Backend Intact)
1. **Onboarding Panel** - "Getting started" banner
   - File: `/frontend/src/components/Sidebar/AppSidebar.vue:581`
   - Method: Set `showOnboarding.value = false`

2. **Website Builder** - Add web pages to sidebar
   - File: `/frontend/src/components/Sidebar/AppSidebar.vue:30`
   - Method: Set "More" section `v-if="false"`
   - Removed: PageModal component, openPageModal/deletePage functions

**Note**: Backend APIs still functional, can be re-enabled by reverting changes

---

## Environment & Configuration

### Settings Location
- **LMS Settings**: DocType in Frappe desk (`/app/lms-settings`)
- **Frontend Config**: `/frontend/vite.config.js`
- **Python Config**: `/pyproject.toml`
- **Hooks**: `/lms/hooks.py`

### Local Development
```bash
# Frontend
cd frontend
npm install
npm run dev

# Backend (Frappe)
bench start
```

### Docker
```bash
cd docker
docker-compose up
```

---

## Important Notes

### Code Style
- **Frontend**: Use Frappe-UI components, avoid inline styles
- **Backend**: Follow Frappe conventions, use `frappe.whitelist()` for APIs
- **No over-engineering**: Keep changes minimal and focused

### Git Workflow
- Main branch: `main`
- Current status: Clean working tree
- Always read files before modifying
- Use Edit tool for precise changes

### Real-time Features
- Socket.IO for live notifications
- Event: `publish_lms_notifications`
- Connected in `/frontend/src/socket.js`

### Widget System
- Location: `/lms/widgets.py`, `/lms/widgets/`
- Used for reusable HTML components
- Integrated via `update_website_context` hook

---

## Quick Reference

### Most Used APIs (in `/lms/lms/api.py`)
- `get_my_courses()` - User's enrolled courses
- `get_my_batches()` - User's batches
- `get_my_live_classes()` - Upcoming live classes
- `get_course_details()` - Course information
- `mark_lesson_progress()` - Track completion
- `get_user_info()` - Current user details
- `get_sidebar_settings()` - Sidebar configuration

### Most Used Stores (Pinia)
- **sessionStore** - User session, branding
- **usersStore** - User resource
- **useSidebar** - Sidebar state
- **useSettings** - App settings

### Common Utilities
- **formatTime()** - Format time strings
- **getSidebarLinks()** - Generate sidebar navigation
- **dayjs** - Date manipulation (injected globally)

---

## Support & Documentation

- **GitHub**: frappe/lms
- **Frappe Docs**: https://frappeframework.com/docs
- **Vue.js Docs**: https://vuejs.org/
- **Frappe-UI**: Custom component library

---

## Current Working Directory
`/Users/raibasharatali/Desktop/lms/frontend/src`

**Additional Working Directory**: `/Users/raibasharatali/desktop/lms`

---

*Last Updated: December 26, 2024*
*Git Commit: fb2e8c3 (update live class modal)*
