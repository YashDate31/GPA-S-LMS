<div align="center">

<img src="LibraryApp/logo.png" alt="GPA Library Logo" width="96" height="96" />

# GPA Student Library Management System

**Government Polytechnic Awasari (Khurd), Pune**

[![Live Demo](https://img.shields.io/badge/Live%20Demo-gpa--s--lms.onrender.com-2563EB?style=for-the-badge&logo=render&logoColor=white)](https://gpa-s-lms.onrender.com/)
[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![React](https://img.shields.io/badge/React-19-61DAFB?style=for-the-badge&logo=react&logoColor=black)](https://react.dev)
[![Flask](https://img.shields.io/badge/Flask-3.x-000000?style=for-the-badge&logo=flask&logoColor=white)](https://flask.palletsprojects.com)
[![Tailwind CSS](https://img.shields.io/badge/Tailwind-3.x-06B6D4?style=for-the-badge&logo=tailwindcss&logoColor=white)](https://tailwindcss.com)
[![Deployed on Render](https://img.shields.io/badge/Deployed-Render-46E3B7?style=for-the-badge&logo=render&logoColor=white)](https://render.com)
[![Database](https://img.shields.io/badge/DB-Supabase%20%2F%20SQLite-3ECF8E?style=for-the-badge&logo=supabase&logoColor=white)](https://supabase.com)
[![License](https://img.shields.io/badge/License-MIT-yellow?style=for-the-badge)](LICENSE)
[![Version](https://img.shields.io/badge/Version-v3.7-orange?style=for-the-badge)]()
[![PRs Welcome](https://img.shields.io/badge/PRs-Welcome-brightgreen?style=for-the-badge)](CONTRIBUTING.md)

*A full-stack, two-tier library management system built by students, for students — at Government Polytechnic Awasari.*

[🎓 For Students](#-for-students--how-to-use-the-portal) · [🏛️ For the College](#%EF%B8%8F-for-the-college) · [💻 For Developers](#-for-developers--technical-reference)

</div>

---

## 📋 Table of Contents

- [Project Overview](#-project-overview)
- [For the College](#%EF%B8%8F-for-the-college)
- [System Architecture](#-system-architecture)
- [Database Schema](#-database-schema)
- [For Students — How to Use the Portal](#-for-students--how-to-use-the-portal)
- [For Developers — Technical Reference](#-for-developers--technical-reference)
  - [Tech Stack](#tech-stack)
  - [Project Structure](#project-structure)
  - [Local Development Setup](#local-development-setup)
  - [Environment Variables](#environment-variables)
  - [API Reference](#api-reference)
  - [Frontend Pages](#frontend-pages)
  - [Known Issues & Technical Debt](#known-issues--technical-debt)
- [Deployment](#-deployment)
- [Roadmap](#-roadmap)
- [Contributing](#-contributing)
- [Contributors](#-contributors)

---

## 🌐 Project Overview

GPA-S-LMS is a **college-grade, two-tier Library Management System** developed for Government Polytechnic Awasari. It consists of two tightly integrated applications:

| Component | Description | Users |
|-----------|-------------|-------|
| **Desktop App** (`main.py`) | Tkinter GUI — librarian-facing admin panel. Manages books, students, loans, fines, reports, and data sync. | Librarian / Admin |
| **Student Web Portal** (`student_portal.py` + React frontend) | A mobile-first Progressive Web App (PWA) where students can browse the catalogue, track loans, request books, and download study materials. | All Students |

The two apps share the **same underlying library database** — the admin manages it via the desktop app, and students see a live, read-only view via the web portal.

> **Live URL:** [https://gpa-s-lms.onrender.com/](https://gpa-s-lms.onrender.com/)

---

## 🏛️ For the College

### What This System Provides

This system was built to solve real problems observed in the college library's day-to-day operations.

| Problem Before | Solution Now |
|----------------|--------------|
| Manual register for book loans | Digital borrow records with automatic due date tracking |
| No way for students to check book availability | Live online catalogue with availability status |
| Fine calculation done manually | Automatic fine computation per day after due date |
| Students unaware of overdue books | Email notifications + in-app alerts |
| Physical study material distribution | Centralized digital study materials portal |
| No broadcast channel for library notices | Admin can post notices visible to all students instantly |
| No data on reading habits or popular books | Analytics dashboard with category trends, badge system |
| No way for students to request new books | Formal request workflow with approval/rejection tracking |

### Features at a Glance

```
✅ Student self-registration and login
✅ Full book catalogue with search, category filters, availability filter
✅ Real-time loan tracking with overdue alerts and fine display
✅ Book renewal request system (librarian-approved)
✅ Waitlist / availability notifications for out-of-stock books
✅ Study materials upload and download (PDFs, notes)
✅ Admin broadcast notices to all students
✅ Email notifications for due dates and approvals
✅ PDF report generation for books and borrow records
✅ Excel export of student data
✅ Gamification: student badges (Bookworm, Scholar, Clean Sheet)
✅ Dark mode + responsive mobile layout (PWA installable)
✅ Cloud sync via Supabase PostgreSQL
✅ Pass-out / alumni student handling
```

### Data Summary (from Supabase schema)

The system manages **16 database tables** across two logical databases:

```mermaid
pie title Database Tables by Category
    "Library Core" : 6
    "Student Portal" : 10
```

---

## 🏗️ System Architecture

The system follows a **hybrid two-tier architecture** — a local desktop admin app that syncs to a cloud PostgreSQL database, and a cloud-hosted Flask API serving the React frontend.

```mermaid
graph TB
    subgraph ADMIN ["🖥️ Librarian Side — Desktop App (main.py)"]
        TK["Tkinter GUI\nAdmin Panel"]
        SYNC["Sync Manager\n(sync_manager.py)"]
    end

    subgraph CLOUD ["☁️ Cloud Layer"]
        SB[("Supabase\nPostgreSQL")]
        RENDER["Render.com\nWeb Server\n(Gunicorn)"]
    end

    subgraph PORTAL ["🌐 Student Web Portal"]
        FLASK["Flask API\n(student_portal.py)\n40+ endpoints"]
        REACT["React SPA\n(Vite + Tailwind)\n13 pages"]
    end

    subgraph STUDENT ["📱 Student Device"]
        BROWSER["Browser / PWA"]
    end

    subgraph LOCAL ["💾 Local Storage (Librarian's PC)"]
        LITELIB[("library.db\nSQLite")]
        LITEPORTAL[("portal.db\nSQLite")]
    end

    TK -->|"reads/writes"| LITELIB
    TK -->|"reads/writes"| LITEPORTAL
    SYNC -->|"push changes"| SB
    LITELIB <-->|"delta sync"| SB
    LITEPORTAL <-->|"delta sync"| SB
    SB -->|"read-only queries"| FLASK
    SB <-->|"read-write (requests,\nnotifs, settings)"| FLASK
    FLASK -->|"serves built React app"| RENDER
    RENDER -->|"HTTPS"| BROWSER
    REACT <-->|"axios API calls"| FLASK
    BROWSER -->|"renders"| REACT
```

### Request Lifecycle (Student Makes a Book Request)

```mermaid
sequenceDiagram
    actor Student
    participant React as React Frontend
    participant Flask as Flask API
    participant PortalDB as portal.db / Supabase
    participant LibDB as library.db / Supabase
    participant Librarian as Librarian Desktop App

    Student->>React: Clicks "Request Book" on catalogue
    React->>Flask: POST /api/request {type, details}
    Flask->>Flask: CSRF token validation
    Flask->>Flask: Rate limit check
    Flask->>PortalDB: INSERT into requests table
    Flask->>Flask: Trigger email notification
    Flask-->>React: 201 Created {req_id, status: "pending"}
    React-->>Student: Toast: "Request submitted for review"

    Note over Librarian: Later — Librarian opens Desktop App
    Librarian->>Flask: GET /api/admin/all-requests
    Flask->>PortalDB: SELECT pending requests
    Flask-->>Librarian: List of pending requests
    Librarian->>Flask: POST /api/admin/requests/:id/approve
    Flask->>LibDB: UPDATE borrow_records (if applicable)
    Flask->>PortalDB: UPDATE request status = "approved"
    Flask->>Student: Email: "Your request was approved"
    Flask-->>Librarian: 200 OK
```

---

## 🗃️ Database Schema

The system uses **16 tables** across two logical databases.

### Core Library Tables (library.db / Supabase)

```mermaid
erDiagram
    students {
        string enrollment_no PK
        string name
        string department
        string year
        string phone
        string email
    }

    books {
        string book_id PK
        string title
        string author
        string category
        string isbn
        int total_copies
        int available_copies
    }

    borrow_records {
        int id PK
        string enrollment_no FK
        string book_id FK
        string accession_no
        date borrow_date
        date due_date
        date return_date
        string status
        int fine
    }

    transactions {
        int id PK
        string enrollment_no FK
        string book_id FK
        string transaction_type
        date transaction_date
        decimal amount
    }

    promotion_history {
        int id PK
        string enrollment_no FK
        string from_year
        string to_year
        date promoted_on
    }

    academic_years {
        int id PK
        string year_label
        date start_date
        date end_date
        bool is_active
    }

    students ||--o{ borrow_records : "borrows"
    books ||--o{ borrow_records : "is borrowed in"
    students ||--o{ transactions : "has"
    books ||--o{ transactions : "involved in"
    students ||--o{ promotion_history : "has"
```

### Portal Tables (portal.db / Supabase)

```mermaid
erDiagram
    student_auth {
        string enrollment_no PK
        string password_hash
        bool is_first_login
        datetime last_login
    }

    requests {
        int req_id PK
        string enrollment_no
        string request_type
        string details
        string status
        datetime created_at
        string admin_note
    }

    notices {
        int id PK
        string title
        string message
        bool active
        datetime created_at
    }

    user_settings {
        string enrollment_no PK
        string email
        bool library_alerts
        bool loan_reminders
        string theme
        string language
        bool data_consent
    }

    user_notifications {
        int id PK
        string enrollment_no
        string type
        string message
        bool is_read
        datetime created_at
    }

    book_waitlist {
        int id PK
        string enrollment_no
        string book_id
        bool notified
        datetime created_at
    }

    study_materials {
        int id PK
        string title
        string subject
        string type
        string filename
        string uploaded_by
        datetime created_at
    }

    deletion_requests {
        int id PK
        string enrollment_no
        string reason
        string status
        datetime created_at
    }

    student_auth ||--|| user_settings : "has"
    student_auth ||--o{ user_notifications : "receives"
    student_auth ||--o{ requests : "submits"
    student_auth ||--o{ book_waitlist : "joins"
    student_auth ||--o{ deletion_requests : "can submit"
```

---

## 🎓 For Students — How to Use the Portal

### Getting Started

```mermaid
flowchart LR
    A([🌐 Visit Portal]) --> B{Have an account?}
    B -- No --> C[Register with\nEnrollment Number]
    C --> D[Set a new password\non first login]
    B -- Yes --> E[Log in]
    D --> E
    E --> F([🏠 Dashboard])
    F --> G[Browse Books]
    F --> H[Check Active Loans]
    F --> I[View Notices]
    F --> J[Download Study Materials]
    G --> K[Request a Book\nor Join Waitlist]
    H --> L[Request Renewal]
```

### Student Quick Reference

| Task | Where to go | Notes |
|------|-------------|-------|
| See books I've borrowed | **Dashboard → Active Loans** or **My Books** | Shows due dates and fine status |
| Search for a book | **Catalogue** → Search bar | Filter by category or availability |
| Request a new book | **Catalogue** → Book card → "Request" | Requires librarian approval |
| Join waitlist for unavailable book | **Book Details** → "Notify Me" | You'll get an email when it's available |
| View overdue fines | **Dashboard → Stats row** | Fine = ₹{rate} per day after due date |
| Request renewal | **Dashboard → Active Loans → Renew** | Renewal is subject to librarian approval |
| Download study notes | **Study Materials** | PDFs organized by subject |
| Change password | **Settings** | Change your default password immediately after first login |
| View borrowing history | **History** | All past books, dates, and categories |
| Check my requests | **Requests** | See status: Pending / Approved / Rejected |
| View library notices | **Dashboard → Announcements** | Posted by the librarian |

> ⚠️ **Important:** Change your default password immediately after first login. You will see a security alert on your dashboard until you do this.

### Understanding Your Dashboard

```mermaid
graph TD
    DASH["🏠 Dashboard"]
    DASH --> P["👤 Profile Card\nName · Enrollment No · Branch"]
    DASH --> AL["📚 Active Loans\nScrollable — up to 3 shown\nGreen = Safe · Yellow = Due Soon · Red = Overdue"]
    DASH --> STATS["📊 Stats Row\nBorrowed · Returned · Overdue · Active Fine"]
    DASH --> ANN["📢 Announcements\nLibrarian notices"]
    DASH --> REQ["🔄 Recent Requests\nYour last 3 requests + status"]
    DASH --> BADGE["🏅 Badges\nBookworm · Scholar · Clean Sheet"]
```

### Badge System

| Badge | Icon | How to Earn |
|-------|------|-------------|
| Bookworm | 🐛 | Borrow 5 or more books total |
| Scholar | 🎓 | Borrow 10 or more books total |
| Clean Sheet | 🛡️ | Never had an overdue book (with 2+ borrows) |

---

## 💻 For Developers — Technical Reference

### Tech Stack

```mermaid
graph LR
    subgraph Frontend
        R["React 19"]
        V["Vite 7"]
        TW["Tailwind CSS 3"]
        FM["Framer Motion 12"]
        AX["Axios"]
        RR["React Router 7"]
        LR["Lucide React"]
        PWA["Vite PWA Plugin"]
    end

    subgraph Backend
        FL["Flask 3"]
        WA["Waitress / Gunicorn"]
        PY["Python 3.10+"]
        PS["psycopg2"]
        DO["python-dotenv"]
    end

    subgraph Database
        SQ["SQLite\n(local dev)"]
        SB["Supabase\nPostgreSQL\n(production)"]
    end

    subgraph Desktop
        TK["Tkinter GUI"]
        PD["pandas + openpyxl"]
        RL["ReportLab PDF"]
        MP["Matplotlib Charts"]
        QR["qrcode"]
    end

    subgraph Infrastructure
        RD["Render.com\n(web hosting)"]
        SBH["Supabase\n(cloud DB)"]
        GH["GitHub\n(source control)"]
    end

    Frontend --> Backend
    Backend --> Database
    Database --> SBH
    Frontend --> RD
```

### Project Structure

```
GPA-S-LMS/
│
├── .env                          # 🔴 NEVER commit — real secrets
├── .env.example                  # ✅ Template — copy this to .env
├── .gitignore
├── Procfile                      # Render deployment command
├── walkthrough.md.resolved       # Supabase setup notes
│
└── LibraryApp/
    │
    ├── main.py                   # 🖥️ Desktop Admin App (Tkinter, ~800KB)
    ├── database.py               # Database schema + ORM helpers (~78KB)
    ├── database_pool.py          # Connection pooling
    ├── sync_manager.py           # Local ↔ Supabase sync logic (~60KB)
    ├── config_manager.py         # App configuration (fine rate, settings)
    ├── email_batch_service.py    # Background email sender
    ├── requirements.txt          # Python dependencies
    ├── logo.png                  # College logo
    │
    ├── Web-Extension/            # 🌐 Student Web Portal
    │   ├── student_portal.py     # Flask API (~158KB, 4000+ lines)
    │   ├── run_waitress_portal.py # Local server runner
    │   │
    │   └── frontend/             # React SPA (Vite + Tailwind)
    │       ├── src/
    │       │   ├── App.jsx       # Root router + session management
    │       │   ├── index.css     # Design tokens + global styles
    │       │   ├── main.jsx      # React entry point
    │       │   │
    │       │   ├── pages/        # 13 page-level components
    │       │   │   ├── Dashboard.jsx
    │       │   │   ├── Catalogue.jsx
    │       │   │   ├── BookDetails.jsx
    │       │   │   ├── MyBooks.jsx
    │       │   │   ├── History.jsx
    │       │   │   ├── Requests.jsx
    │       │   │   ├── Notifications.jsx
    │       │   │   ├── StudyMaterials.jsx
    │       │   │   ├── Profile.jsx
    │       │   │   ├── Settings.jsx
    │       │   │   ├── Services.jsx
    │       │   │   ├── Contact.jsx
    │       │   │   └── Login.jsx / Register.jsx
    │       │   │
    │       │   ├── components/   # Reusable components
    │       │   │   ├── Layout.jsx          # Sidebar + mobile nav wrapper
    │       │   │   ├── BookDetailModal.jsx # Full book info modal
    │       │   │   ├── BookLoanCard.jsx    # Active loan card
    │       │   │   ├── RequestModal.jsx    # Request submission form
    │       │   │   ├── AlertBanner.jsx     # Overdue / security alerts
    │       │   │   ├── DangerValidationModal.jsx
    │       │   │   ├── ActiveFilters.jsx
    │       │   │   ├── Breadcrumbs.jsx
    │       │   │   └── ErrorBoundary.jsx
    │       │   │
    │       │   ├── components/ui/  # Primitive UI components
    │       │   │   ├── Button.jsx
    │       │   │   ├── Card.jsx
    │       │   │   ├── Badge.jsx
    │       │   │   ├── Skeleton.jsx      # Loading placeholders
    │       │   │   ├── AppBar.jsx
    │       │   │   ├── BottomNav.jsx     # Mobile navigation
    │       │   │   ├── EmptyState.jsx
    │       │   │   ├── ErrorMessage.jsx
    │       │   │   ├── ImageWithSkeleton.jsx
    │       │   │   └── LoadingSpinner.jsx
    │       │   │
    │       │   ├── context/
    │       │   │   └── ToastContext.jsx   # Global toast notifications
    │       │   │
    │       │   └── utils/
    │       │       └── csrf.js           # CSRF token helpers
    │       │
    │       ├── package.json
    │       ├── tailwind.config.js
    │       └── vite.config.js
```

### Local Development Setup

#### Prerequisites

| Tool | Version | Check |
|------|---------|-------|
| Python | 3.10+ | `python --version` |
| Node.js | 18+ | `node --version` |
| npm | 9+ | `npm --version` |
| Git | any | `git --version` |

#### Step 1 — Clone the repository

```bash
git clone https://github.com/YashDate31/GPA-S-LMS.git
cd GPA-S-LMS
```

#### Step 2 — Set up environment variables

```bash
cp .env.example .env
# Now open .env and fill in the values (see Environment Variables section below)
```

> ⚠️ **Never commit your `.env` file.** It is already in `.gitignore`, but double-check.

#### Step 3 — Install Python dependencies

```bash
cd LibraryApp
pip install -r requirements.txt
```

#### Step 4 — Install frontend dependencies

```bash
cd Web-Extension/frontend
npm install
```

#### Step 5 — Run development servers

**Option A — Frontend + Backend together (recommended)**

Terminal 1 — Start the Flask API:
```bash
cd LibraryApp/Web-Extension
python run_waitress_portal.py
# API available at http://localhost:5000
```

Terminal 2 — Start the React dev server:
```bash
cd LibraryApp/Web-Extension/frontend
npm run dev
# Frontend available at http://localhost:5173
```

**Option B — Desktop Admin App**

```bash
cd LibraryApp
python main.py
```

#### Step 6 — Build for production

```bash
cd LibraryApp/Web-Extension/frontend
npm run build
# Built files go to dist/ — Flask serves these automatically
```

### Environment Variables

Copy `.env.example` to `.env` and fill in each value:

| Variable | Required | Description | Example |
|----------|----------|-------------|---------|
| `DATABASE_URL` | ✅ Yes | Full Supabase PostgreSQL connection URI | `postgresql://user:pass@host:5432/db?sslmode=require` |
| `FLASK_SECRET_KEY` | ✅ Yes | Random secret string for Flask sessions | Any long random string (50+ chars) |
| `PORTAL_USE_CLOUD` | For prod | Set to `1` to use Supabase instead of local SQLite | `1` |
| `VITE_SUPABASE_URL` | Optional | Supabase project URL | `https://xxxx.supabase.co` |
| `VITE_SUPABASE_ANON_KEY` | Optional | Supabase anon key | `eyJ...` |

> 💡 For local development without Supabase, leave `DATABASE_URL` empty — the app will automatically fall back to local SQLite databases.

### API Reference

All endpoints are prefixed with `/api/`. Authentication is cookie-session based.

#### Public Endpoints (no login required)

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/login` | Student login with enrollment number + password |
| `POST` | `/api/public/register` | New student self-registration |
| `POST` | `/api/public/forgot-password` | Send password reset email |
| `GET` | `/api/notices` | Fetch active library announcements |
| `GET` | `/api/version` | App version info |

#### Student Endpoints (login required)

| Method | Endpoint | Description | Key Response Fields |
|--------|----------|-------------|---------------------|
| `GET` | `/api/me` | Current logged-in student profile | `name, enrollment_no, department, year, privileges, settings` |
| `GET` | `/api/dashboard` | Full dashboard data in one call | `borrows, history, notices, analytics, summary, recent_requests` |
| `GET` | `/api/alerts` | Lightweight overdue + security check | `has_alert, type, count, fine_estimate` |
| `GET` | `/api/books` | Paginated book catalogue | `books[], categories[], pagination{}` |
| `GET` | `/api/books/:id` | Single book details | `title, author, category, isbn, available_copies` |
| `POST` | `/api/books/:id/notify` | Join waitlist for a book | — |
| `DELETE` | `/api/books/:id/notify` | Leave waitlist | — |
| `POST` | `/api/request` | Submit a new request (borrow/renewal/complaint) | `req_id, status` |
| `GET` | `/api/requests` | List my submitted requests | `requests[]` |
| `POST` | `/api/request/:id/cancel` | Cancel a pending request | — |
| `GET` | `/api/loan-history` | Full borrow history | `history[]` |
| `GET` | `/api/notifications` | In-app notifications | `notifications[], unread_count` |
| `POST` | `/api/notifications/mark-read` | Mark notifications as read | — |
| `DELETE` | `/api/notifications/:id` | Delete a notification | — |
| `GET` | `/api/study-materials` | List study materials | `materials[]` |
| `GET` | `/api/study-materials/:id/download` | Download a study material file | binary file |
| `GET` | `/api/services` | Digital library resources/links | `services[]` |
| `POST` | `/api/change_password` | Change password | — |
| `POST` | `/api/settings` | Update user preferences | — |
| `POST` | `/api/logout` | Log out and clear session | — |
| `POST` | `/api/request-deletion` | Request account deletion | — |
| `GET` | `/api/user-policies` | Fetch borrowing limits and policies | `policies{}` |

#### Admin Endpoints (librarian session required)

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/admin/all-requests` | All student requests |
| `POST` | `/api/admin/requests/:id/approve` | Approve a request |
| `POST` | `/api/admin/requests/:id/reject` | Reject a request |
| `GET` | `/api/admin/stats` | System-wide stats |
| `GET/POST/DELETE` | `/api/admin/notices` | Manage announcements |
| `GET/POST/DELETE` | `/api/admin/study-materials` | Manage study materials |
| `GET` | `/api/admin/auth-stats` | Login stats and security report |
| `POST` | `/api/admin/bulk-password-reset` | Reset multiple student passwords |
| `GET` | `/api/admin/observability` | Server health and request logs |

#### Dashboard API — Full Response Shape

```json
{
  "borrows": [
    {
      "title": "Introduction to Python",
      "author": "...",
      "borrow_date": "2026-03-01",
      "due_date": "2026-03-08",
      "book_id": "CS001",
      "accession_no": "ACC-123",
      "fine": 0,
      "status": "safe | warning | overdue",
      "days_msg": "3 days left"
    }
  ],
  "history": [...],
  "notices": [...],
  "notifications": [...],
  "recent_requests": [...],
  "analytics": {
    "stats": {
      "total_books": 12,
      "fav_category": "Programming",
      "categories": { "Programming": 5, "AI/ML": 3 }
    },
    "badges": [
      { "id": "bookworm", "label": "Bookworm", "icon": "🐛" }
    ]
  },
  "summary": {
    "borrowed_count": 2,
    "returned_count": 10,
    "overdue_count": 0,
    "pending_requests_count": 1,
    "wishlist_count": 2,
    "active_fine": 0,
    "total_fine_ever": 20
  }
}
```

### Frontend Pages

| Page | Route | Key Features |
|------|-------|-------------|
| Login | `/login` | Enrollment + password, forgot password link |
| Register | `/register` | Self-registration form |
| Dashboard | `/` | Profile card, active loans, stat grid, notices, recent requests, badges |
| Catalogue | `/books` | Search, category + availability filter, paginated grid, request modal |
| Book Details | `/books/:id` | Full book info, availability, waitlist button |
| My Books | `/my-books` | All currently borrowed books with renew button |
| History | `/history` | Complete borrow history with dates and categories |
| Requests | `/requests` | All submitted requests and their status |
| Notifications | `/notifications` | In-app notification centre |
| Study Materials | `/study-materials` | Browse and download uploaded materials |
| Services | `/services` | Digital resources and external links |
| Profile | `/profile` | Student info and account details |
| Settings | `/settings` | Theme, notifications, password, account deletion |
| Contact | `/contact` | Contact the librarian form |

### Known Issues & Technical Debt

These are active known issues that future contributors should be aware of:

```mermaid
quadrantChart
    title Issues — Impact vs. Effort to Fix
    x-axis Low Effort --> High Effort
    y-axis Low Impact --> High Impact
    quadrant-1 Do First
    quadrant-2 Plan Carefully
    quadrant-3 Low Priority
    quadrant-4 Quick Wins

    alert() calls: [0.15, 0.85]
    Duplicate CSS tokens: [0.2, 0.75]
    App loading spinner: [0.1, 0.55]
    Skeleton layout mismatch: [0.25, 0.60]
    Profile photo in localStorage: [0.45, 0.80]
    In-memory rate limiter: [0.55, 0.70]
    Admin role verification: [0.50, 0.85]
    Reading stats not shown: [0.20, 0.50]
    Fine history not shown: [0.15, 0.45]
    Wishlist count hidden: [0.15, 0.40]
```

| # | Issue | Severity | File | Fix |
|---|-------|----------|------|-----|
| 1 | `alert()` used for feedback instead of ToastContext | 🔴 High | `Dashboard.jsx` | Replace with `useToast()` — ToastContext already exists |
| 2 | Two conflicting `@layer base` blocks in `index.css` | 🔴 High | `index.css` | Merge into a single CSS variable block |
| 3 | App initial load shows bare `"Loading..."` text | 🟡 Medium | `App.jsx` | Replace with branded splash screen |
| 4 | DashboardSkeleton is 3-col, actual grid is 4-col | 🟡 Medium | `Dashboard.jsx` | Rebuild skeleton to match real layout |
| 5 | Date parsing uses brittle `.replace(' ', 'T')` | 🟡 Medium | Multiple pages | Use consistent `_to_iso_date()` server-side |
| 6 | Profile photo stored as base64 in localStorage | 🔴 Security | `Dashboard.jsx` | Move to server-side file storage |
| 7 | Rate limiter is in-memory (resets on restart) | 🟡 Security | `student_portal.py` | Use Redis or DB-backed counter |
| 8 | Admin endpoints lack role verification | 🔴 Security | `student_portal.py` | Add admin role check middleware |
| 9 | `analytics.stats.categories` never rendered | 🟢 Low | `Dashboard.jsx` | Add reading stats section |
| 10 | `wishlist_count` in summary never displayed | 🟢 Low | `Dashboard.jsx` | Add as 5th stat card |

> See the full audit report in `AUDIT.md` (coming soon).

---

## 🚀 Deployment

The production deployment runs on **Render.com** and connects to **Supabase PostgreSQL**.

```mermaid
flowchart LR
    GH["GitHub\nmain branch"] -->|"push triggers"| RD["Render.com\nAuto-deploy"]
    RD -->|"runs"| CMD["gunicorn student_portal:app\n(from LibraryApp/Web-Extension/)"]
    CMD -->|"connects to"| SB["Supabase\nPostgreSQL"]
    CMD -->|"serves"| STATIC["Built React dist/\n(pre-built and committed)"]
```

### Render Environment Variables

Set these in **Render Dashboard → Environment**:

```
DATABASE_URL    = postgresql://...  (from Supabase → Project Settings → Database URI)
FLASK_SECRET_KEY = <your-long-random-key>
PORTAL_USE_CLOUD = 1
```

### Procfile (already in repo)

```
web: cd LibraryApp/Web-Extension && gunicorn student_portal:app
```

### Supabase Database Setup

If setting up a fresh Supabase project, apply these 3 migrations in order:

1. `create_core_library_tables` — creates 6 library tables + 5 performance indexes
2. `create_portal_tables` — creates 10 portal tables
3. `disable_rls_for_direct_psycopg2_access` — disables Row Level Security (required because the app uses `psycopg2` directly, not the Supabase SDK)

> See `walkthrough.md.resolved` for detailed Supabase setup instructions.

---

## 🗺️ Roadmap

```mermaid
gantt
    title GPA-S-LMS Development Roadmap
    dateFormat  YYYY-MM
    section Phase 1 — Critical Fixes (Now)
    Fix alert() → Toast notifications         :done,    p1a, 2026-04, 1w
    Merge duplicate CSS tokens                :done,    p1b, 2026-04, 1w
    App loading splash screen                 :active,  p1c, 2026-04, 1w
    Fix skeleton layout mismatch              :         p1d, 2026-04, 2w

    section Phase 2 — Design Overhaul
    New institutional colour palette          :         p2a, 2026-05, 2w
    Content-matched skeleton loaders          :         p2b, 2026-05, 2w
    Empty state illustrations                 :         p2c, 2026-05, 1w
    Consistent typography scale               :         p2d, 2026-05, 1w

    section Phase 3 — Missing Features
    Reading stats / category chart on dashboard:        p3a, 2026-06, 2w
    Wishlist / waitlist dedicated page        :         p3b, 2026-06, 1w
    Fine history section on profile           :         p3c, 2026-06, 1w
    Show ISBN in book details                 :         p3d, 2026-06, 1w

    section Phase 4 — Security
    Server-side profile photo storage         :         p4a, 2026-07, 2w
    DB-backed rate limiter                    :         p4b, 2026-07, 1w
    Admin role verification middleware        :         p4c, 2026-07, 2w
    Remove .env from git history              :crit,    p4d, 2026-04, 3d

    section Phase 5 — Future Enhancements
    Book cover image support (Google Books API):        p5a, 2026-08, 3w
    Student reading streak / leaderboard      :         p5b, 2026-08, 2w
    QR code book scanning for librarian       :         p5c, 2026-09, 3w
    Push notifications (Web Push API)         :         p5d, 2026-09, 2w
```

### Feature Wishlist

| Feature | Description | Complexity | Assigned |
|---------|-------------|------------|---------|
| 📸 Book cover images | Fetch from Google Books API by ISBN | Medium | Open |
| 📊 Reading leaderboard | Top readers per semester | Medium | Open |
| 🔔 Push notifications | Web Push API for due date reminders | High | Open |
| 📱 QR code scanning | Mobile QR scan to look up any book instantly | Medium | Open |
| 💬 Book ratings | Let students rate and review books | Low | Open |
| 🔍 Advanced search | Search by ISBN, accession number, year | Low | Open |
| 📅 Calendar view | Due dates shown on a calendar | Medium | Open |
| 🌐 Multi-language | Marathi language support | High | Open |
| 📧 Bulk email | Librarian sends batch reminders | Low | Open |

---

## 🤝 Contributing

Contributions from students, faculty, and developers are welcome! This is a real production system used by the college, so contributions have real impact.

### How to Contribute

```mermaid
flowchart TD
    A([Find an issue\nor have an idea]) --> B[Fork the repository]
    B --> C["Create a branch\ngit checkout -b fix/your-feature-name"]
    C --> D[Make your changes]
    D --> E["Test locally\n(both Flask API + React frontend)"]
    E --> F{Tests pass?}
    F -- No --> D
    F -- Yes --> G["Commit with a clear message\ngit commit -m 'fix: replace alert with toast in Dashboard'"]
    G --> H["Push your branch\ngit push origin fix/your-feature-name"]
    H --> I[Open a Pull Request\non GitHub]
    I --> J[Review by maintainers]
    J --> K([✅ Merged!])
```

### Commit Message Convention

Use this format for all commits:

```
type: short description

Types:
  feat     — new feature
  fix      — bug fix
  style    — CSS/design changes
  refactor — code restructure (no feature change)
  docs     — documentation only
  chore    — build, config, dependencies
  security — security fix

Examples:
  feat: add reading stats chart to dashboard
  fix: replace alert() calls with useToast in Dashboard.jsx
  style: merge duplicate CSS token blocks in index.css
  security: remove .env from git history
```

### Branch Naming

```
feature/add-reading-stats
fix/dashboard-skeleton-layout
style/new-colour-palette
security/remove-env-from-history
docs/update-api-reference
```

### What to Work On

Check the [Known Issues](#known-issues--technical-debt) table — those are the most impactful starting points. Issues marked 🟢 Low are great for first-time contributors. Issues marked 🔴 High need careful review.

> Before starting any major feature, open a GitHub Issue first so we can discuss the approach.

---

## 🔒 Security Notes

- **Never commit `.env`** — always use `.env.example` as the template
- The Flask app uses **CSRF protection** on all state-changing endpoints
- Sessions use **httpOnly cookies** (not localStorage tokens)
- Rate limiting is applied to login, register, and forgot-password endpoints
- All SQL queries use **parameterized statements** — no raw string interpolation
- Student passwords are **hashed** before storage (never stored as plaintext)

To report a security vulnerability, please contact the maintainers directly rather than opening a public issue.

---

## 📜 Changelog

| Version | Date | Summary |
|---------|------|---------|
| v3.7 | Apr 2026 | Comprehensive UI/UX overhaul, critical bug fixes, PWA support |
| v3.x | Mar 2026 | Supabase cloud sync, Render deployment, study materials |
| v2.x | 2025 | Student portal (React + Flask), notification system |
| v1.x | 2024 | Desktop admin app, core library management |

---

## 👥 Contributors

<table>
<tr>
<td align="center">
<a href="https://github.com/YashDate31">
<img src="https://github.com/YashDate31.png" width="80" style="border-radius:50%"/><br/>
<b>Yash V Date</b><br/>
<sub>Project Lead & Full-Stack Dev</sub>
</a>
</td>
<td align="center">
<a href="https://github.com/yashmagar01">
<img src="https://github.com/yashmagar01.png" width="80" style="border-radius:50%"/><br/>
<b>Yash Ajay Magar</b><br/>
<sub>Backend & Database</sub>
</a>
</td>
</tr>
</table>

*Want to see your name here? [Contribute!](#-contributing)*

---

## 🏫 About

This project was built as a part of the **Diploma in Computer Engineering** program at **Government Polytechnic Awasari (Khurd), Pune** under MSBTE K-Scheme.

**Institution:** Government Polytechnic Awasari (Khurd), Pune, Maharashtra  
**Department:** Computer Engineering  
**Academic Year:** 2025–26  

---

<div align="center">

Made with ❤️ by students of Government Polytechnic Awasari

*If this project helped you, please give it a ⭐ on GitHub!*

</div>
