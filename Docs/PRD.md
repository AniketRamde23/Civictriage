# Product Requirements Document (PRD)

# CivicTriage: Multilingual Civic Grievance Triage & Urgency Ranking Platform

---

## Document Control

| Attribute | Details |
| :--- | :--- |
| **Project Name** | CivicTriage (Municipal Grievance Intelligence System) |
| **Document Version** | 2.4.0 (Web Architecture & Production Standard) |
| **Status** | Approved / Production Baseline |
| **Author** | Senior Engineering & Product Team |
| **Target Audience** | Municipal Corporations (ULBs), Civic Engineers, Triage Officers, Capstone Review Committee |
| **Deployment Target** | On-Premise Air-Gapped Municipal Servers / Edge Hardware |

---

## 1. Executive Summary & Problem Statement

### 1.1 Context
Urban Local Bodies (ULBs) and Municipal Corporations in India receive thousands of civic complaints weekly covering vital municipal services: **Water Supply, Roads & Traffic, Sanitation, Electricity, and Other infrastructure**. Complaints are submitted in regional languages—principally **English, Hindi (हिन्दी), and Telugu (తెలుగు)**—often using informal dialects, varied scripts, and emotionally charged vocabulary.

### 1.2 The Core Problem
1. **Critical Triage Delays**: Manual classification causes life-threatening emergencies (e.g., snapped high-voltage electric cables, open manholes on active highways, toxic sewer overflows into homes) to sit in unread backlogs alongside routine requests (e.g., park speed breaker repainting).
2. **Language Barrier & Staff Fatigue**: Frontline municipal staff are overwhelmed by multi-script intake, causing errors in department assignment and prolonged processing times.
3. **Data Loss During Ingestion**: Cloud-dependent or synchronous AI systems lose complaints when network latency spikes or when LLM API endpoints timeout.
4. **Lack of Transparency**: Citizens submit grievances into a "black box", leading to repetitive calls, escalating frustration, and erosion of public trust.

### 1.3 Solution Vision
**CivicTriage** is an explainable, air-gapped, multilingual civic grievance triage web platform designed for municipal operations. It guarantees **instant complaint persistence (zero data loss)**, detects English, Hindi, and Telugu, performs structured classification via a localized Small Language Model (SLM), enforces a **deterministic safety escalation layer**, and serves municipal officers with a strictly prioritized, urgency-ranked action queue.

---

## 2. Product Objectives & Key Results (OKRs)

* **Objective 1: Zero Grievance Ingestion Loss**
  * *KR 1.1*: 100% of complaints saved to persistent SQLite storage with status `Received` in `< 50ms` prior to triggering any AI inference.
* **Objective 2: Life-Safety Emergency Acceleration**
  * *KR 2.1*: 100% recall on life-safety emergency hazards via deterministic keyword rules escalation.
  * *KR 2.2*: Emergency items ranked at the top of the officer triage queue within seconds of receipt.
* **Objective 3: Multilingual Autonomy & Data Sovereignty**
  * *KR 3.1*: Zero citizen grievance data transmitted to external public cloud APIs (100% on-device Ollama SLM execution).
  * *KR 3.2*: Accurate multilingual triage across English, Hindi, and Telugu with `> 85%` priority agreement on ground-truth benchmark datasets.
* **Objective 4: Actionable Officer Efficiency & Auditability**
  * *KR 4.1*: Ranked triage queue with filter query execution under `30ms` for 1,000+ active complaints.
  * *KR 4.2*: Full chronological audit trail of officer inspection notes visible in real-time to citizens.

---

## 3. User Personas & Journey Mapping

### Persona 1: The Citizen (Complainant)
* **Profile**: Resident of Municipal Ward (e.g., Ramesh, Ward 4). Submits grievances during distressing situations (e.g., water supply stopped for 4 days or sparking wire outside school).
* **Pain Points**: Doesn't know administrative department structures; prefers writing in native language; worries whether the complaint was received; lacks status visibility.
* **Journey**:
  1. Accesses Citizen Portal (web or mobile browser).
  2. Types grievance in native language (English, Hindi, or Telugu).
  3. Receives instant acknowledgment receipt with Grievance ID (`Received` status).
  4. Tracks live status transitions (`Received` $\to$ `In Progress` $\to$ `Resolved`) and reads officer field notes.

### Persona 2: The Municipal Triage Officer (Field Inspector)
* **Profile**: Ward officer or municipal engineer (e.g., Inspector Verma) handling intake across 15 wards.
* **Pain Points**: Backlog overload; inability to spot life-threatening emergencies among hundreds of mundane complaints; lack of audit logging when assigning repair crews.
* **Journey**:
  1. Signs into the Officer Command Center.
  2. Inspects KPI metrics (Total in Queue, 🚨 Immediate, ⚠️ Soon, ⚙️ Needs Review).
  3. Works down the **Ranked Queue**, where Immediate items always appear at the top.
  4. Inspects single items: reviews original text, AI summary, detected tone, and keyword escalation justification.
  5. Updates status to `In Progress` or `Resolved` and appends field notes (e.g., "Repair crew dispatched").

### Persona 3: Municipal Commissioner / Ward Administrator
* **Profile**: Senior municipal leadership monitoring ward health, infrastructure vulnerabilities, and SLA compliance.
* **Journey**:
  1. Reviews Insights & Analytics Dashboard.
  2. Identifies systemic failure hotspots (e.g., recurring Water grievances in Ward 4).
  3. Exports grievance ledger to CSV for executive reporting and inter-departmental reviews.

---

## 4. System Architecture & Tech Stack

```
   ┌────────────────────────────────────────────────────────────────────────┐
   │             Modern Web Interface (HTML5 / Vanilla CSS3 / JS)           │
   │  ┌───────────────────────────┐ ┌─────────────────────────────────────┐  │
   │  │    Citizen Portal         │ │    Officer Command Center & Queue   │  │
   │  │ (Submit & Track Receipts) │ │  (Ranked Queue, Filters, Inspector) │  │
   │  └─────────────┬─────────────┘ └──────────────────┬──────────────────┘  │
   └────────────────┼──────────────────────────────────┼─────────────────────┘
                    │                                  │
                    ▼                                  ▼
   ┌────────────────────────────────────────────────────────────────────────┐
   │                 FastAPI RESTful Application Server                     │
   │  - Stateless Signed URL-safe Session Tokens (itsdangerous)             │
   │  - Strict Role-Based Access Control (RBAC: Citizen vs Officer)         │
   │  - Asynchronous Background Classification Worker Pool (3 workers)      │
   │  - Static Asset Serving & Real-Time System Health Telemetry            │
   └────────────────┬──────────────────────────────────┬─────────────────────┘
                    │                                  │
                    ▼                                  ▼
   ┌─────────────────────────────────┐┌─────────────────────────────────────┐
   │         Core AI & Rules         ││      SQLite Persistent Storage      │
   │ ┌─────────────────────────────┐ ││  (civictriage.db, WAL Mode)         │
   │ │ langdetect (EN, HI, TE)     │ ││                                     │
   │ └──────────────┬──────────────┘ ││  - users (bcrypt hashed passwords)  │
   │                ▼                ││  - grievances (composite indexes)   │
   │ ┌─────────────────────────────┐ ││  - status_notes (audit history)     │
   │ │ Local SLM (Ollama)          │ ││                                     │
   │ │ llama3.2:3b JSON Validation │ ││  Query Latency: < 30ms              │
   │ └──────────────┬──────────────┘ ││  Zero SQL Injection (Parameterised) │
   │                ▼                │└─────────────────────────────────────┘
   │ ┌─────────────────────────────┐ │
   │ │ Deterministic Keyword Safety│ │
   │ │ Escalator (config/keywords) │ │
   │ └─────────────────────────────┘ │
   └─────────────────────────────────┘
```

### Technology Matrix

| Layer | Component | Specification | Rationale |
| :--- | :--- | :--- | :--- |
| **Frontend UI** | Semantic HTML5 / Vanilla CSS3 / Vanilla JS | Zero heavyweight framework overhead; responsive design system; Dark & Light themes | Instant load time (< 150ms), zero node_modules build complexity, browser universal |
| **Application Server** | FastAPI + Uvicorn (ASGI) | Python 3.10+ / FastAPI 0.110+ | High throughput async IO, native OpenAPI schemas, sub-millisecond route dispatch |
| **Authentication** | `itsdangerous` + `bcrypt` | Signed URL-safe bearer token + HTTP-only cookies; salted bcrypt hashes | Stateless, secure, resilient across server restarts, role isolation |
| **Local SLM Engine** | Ollama (`llama3.2:3b`) | Local HTTP endpoint `http://localhost:11434` | Complete data privacy, zero API costs, runs on standard edge workstation (8GB+ RAM) |
| **Language Detection** | `langdetect` + Unicode scripts | ISO-639 codes: `en`, `hi`, `te` | High-speed script recognition before prompt injection |
| **Database** | SQLite3 with WAL mode | Write-Ahead Logging, composite indexes, foreign key cascades | Zero maintenance overhead, ACID compliant, sub-30ms performance on 1,000+ rows |

---

## 5. Functional Requirements (FR1 – FR7)

### FR1: Immediate Grievance Intake & Persistence
* **Specification**: When a citizen submits a grievance, the system must persist the record into the database with `status = 'Received'` **immediately**, before initiating any language processing or LLM inference.
* **Acceptance Criteria**:
  * Grievance ID returned to complainant in `< 100ms`.
  * If the LLM engine is offline, slow, or errors out, the record is safely stored and never lost.
  * Grievance text minimum length validation: $\ge 5$ characters.

### FR2: Multilingual Language Detection
* **Specification**: Detect whether the text is composed in English (`en`), Hindi (`hi`), or Telugu (`te`).
* **Acceptance Criteria**:
  * Utilizes `langdetect` supplemented by Unicode script character range checks (Devanagari for Hindi, Telugu block for Telugu).
  * Passes native text directly to the model prompt without pre-translation artifacts.
  * Stores `detected_language` in the grievance record.

### FR3: Structured SLM Classification & Fault Tolerance
* **Specification**: The local SLM (`llama3.2:3b`) analyzes the grievance and outputs a strict JSON object containing:
  ```json
  {
    "emotion": "Angry | Anxious | Sad | Neutral",
    "priority": "Immediate | Soon | Routine",
    "category": "Water | Roads | Sanitation | Electricity | Other",
    "english_summary": "<One-sentence English translation/summary>",
    "reason": "<Brief explanation for urgency assignment>"
  }
  ```
* **Acceptance Criteria**:
  * **JSON Normalization**: Cleans code fences (````json ... ````) and performs regex boundary extraction.
  * **Retry-Once Logic**: If output is invalid JSON, the system sends an immediate correction retry prompt.
  * **Needs Review Fallback**: If the retry fails or the model server is unreachable, the system automatically assigns `priority = 'Routine'`, `category = 'Other'`, and sets `status = 'Needs Review'`, ensuring manual officer inspection.

### FR4: Deterministic Safety Keyword Escalation Layer
* **Specification**: A post-LLM rule engine scans the native text against a multilingual safety dictionary (`config/keywords.json`).
* **Rule Logic**:
  * If critical emergency keywords (e.g., *live wire, open manhole, करंट, खुला गटर, లైవ్ వైర్, ప్రమాదం*) are present:
    $$\text{Routine} \longrightarrow \text{Soon} \longrightarrow \text{Immediate}$$
  * **Non-Demotion Invariant**: The rule engine can **only escalate** or maintain priority; it can **never downgrade** a priority assigned by the LLM.
  * Appends an audit note: `"Escalated to Immediate: safety keyword detected: '[keyword]'."`

### FR5: Ranked Officer Triage Action Queue
* **Specification**: An interactive triage table sorting active complaints for municipal officers.
* **Sorting Hierarchy**:
  1. **Urgency Tier**: `Immediate` (Rank 1) $\longrightarrow$ `Soon` (Rank 2) $\longrightarrow$ `Routine` (Rank 3) $\longrightarrow$ `Unassigned` (Rank 4).
  2. **Age / Timestamp**: Oldest complaints first (`created_at ASC`), preventing old emergencies from starving.
* **Filtering Capabilities**: Multi-criteria dropdowns for Priority, Category, Ward, and Status, plus full-text search across citizen name, ward, and complaint text.

### FR6: Citizen Status Transparency & Officer Audit Trail
* **Specification**: Officers update grievance status (`Received`, `In Progress`, `Needs Review`, `Resolved`) and append progress notes.
* **Acceptance Criteria**:
  * Appending a note updates `status_notes` table with `officer_id` and timestamp.
  * Complainants view live notes timeline in their portal under "My Grievances".
  * Strict Citizen Data Isolation: Citizens can only query their own grievances (`WHERE user_id = ?`).

### FR7: Insights & Analytics Dashboard
* **Specification**: Aggregates municipal telemetry into summary cards and visual distributions:
  * Total grievances count, Immediate count, Resolved count, Active reporting wards.
  * Distribution by Category (Bar Chart).
  * Distribution by Priority / Urgency (Segmented Donut Breakdown).
  * Geographic Distribution by Ward.
  * CSV Data Export streaming endpoint (`/api/insights/export`).

---

## 6. Non-Functional Requirements (NFRs)

### 6.1 Performance & Response Times
* **Receipt Response**: Citizen submission API responds in $< 100\text{ms}$.
* **Queue Latency**: Officer queue query with filtering executes in $< 30\text{ms}$ on 1,000+ rows.
* **Background Inference**: Async SLM classification completed within $1.5\text{s} - 3.5\text{s}$ per grievance.
* **UI Bundle**: Vanilla CSS/JS assets $< 80\text{KB}$ uncompressed; initial paint $< 200\text{ms}$.

### 6.2 Data Privacy & Air-Gap Compliance
* 100% of LLM inferencing executes on the local host (`localhost:11434`).
* Zero external network calls required for core grievance processing.
* Complies with Indian Digital Personal Data Protection (DPDP) Act by maintaining citizen grievance records within municipal jurisdiction.

### 6.3 Security & Role-Based Access Control (RBAC)
* **Passwords**: Salted hashing with `bcrypt` (work factor 12).
* **Injection Defense**: 100% parameterised SQL queries (`cursor.execute(sql, (param,))`). Zero string interpolation.
* **Session Tokens**: Signed, URL-safe tokens with expiration (7-day validity).
* **Officer Provisioning Guard**: Officers **cannot self-register** via public UI; provisioning is restricted to administrative CLI script (`scripts/create_officer.py`).

### 6.4 Reliability & Graceful Degradation
* **Database Concurrency**: SQLite configured with `PRAGMA journal_mode=WAL;` and `timeout=30.0` to support concurrent reader threads while background workers write.
* **Thread Pool Isolation**: Dedicated 3-worker `ThreadPoolExecutor` prevents background LLM tasks from blocking the FastAPI event loop.

---

## 7. Data Dictionary & Database Schema

### 7.1 Schema Definitions

#### Table: `users`
| Column | Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `id` | INTEGER | PRIMARY KEY AUTOINCREMENT | Unique user identifier |
| `name` | TEXT | NOT NULL | Full name of citizen or officer |
| `email` | TEXT | UNIQUE, NOT NULL | Lowercase email address |
| `password_hash` | TEXT | NOT NULL | Bcrypt salted hash |
| `role` | TEXT | CHECK(`role` IN ('citizen', 'officer')) | Role authorization level |
| `created_at` | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | Registration timestamp |

#### Table: `grievances`
| Column | Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `id` | INTEGER | PRIMARY KEY AUTOINCREMENT | Unique grievance ticket ID |
| `user_id` | INTEGER | NOT NULL, FK(`users.id`) | Submitting citizen |
| `ward` | TEXT | DEFAULT 'Unspecified' | Municipal Ward / Zone |
| `original_text` | TEXT | NOT NULL | Native language description |
| `detected_language`| TEXT | NULL | Language code (`en`, `hi`, `te`) |
| `english_summary` | TEXT | NULL | LLM generated English translation |
| `emotion` | TEXT | NULL | `Angry`, `Anxious`, `Sad`, `Neutral` |
| `priority` | TEXT | NULL | `Immediate`, `Soon`, `Routine` |
| `category` | TEXT | NULL | `Water`, `Roads`, `Sanitation`, `Electricity`, `Other` |
| `reason` | TEXT | NULL | Triage reasoning and safety trigger |
| `status` | TEXT | CHECK(`status` IN ('Received', 'In Progress', 'Resolved', 'Needs Review')) | Current lifecycle state |
| `created_at` | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | Submission timestamp |

#### Table: `status_notes`
| Column | Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `id` | INTEGER | PRIMARY KEY AUTOINCREMENT | Note identifier |
| `grievance_id` | INTEGER | NOT NULL, FK(`grievances.id`) | Target grievance |
| `officer_id` | INTEGER | NOT NULL, FK(`users.id`) | Authoring municipal officer |
| `note` | TEXT | NOT NULL | Inspection or progress update |
| `created_at` | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | Entry timestamp |

### 7.2 Database Performance Indexes
* `CREATE INDEX idx_grievances_user_id ON grievances(user_id);`
* `CREATE INDEX idx_grievances_priority ON grievances(priority);`
* `CREATE INDEX idx_grievances_status ON grievances(status);`
* `CREATE INDEX idx_grievances_ward ON grievances(ward);`
* `CREATE INDEX idx_grievances_created_at ON grievances(created_at);`
* `CREATE INDEX idx_grievances_perf ON grievances(priority, status, ward, created_at);`
* `CREATE INDEX idx_status_notes_grievance ON status_notes(grievance_id);`

---

## 8. API Specification

| Method | Endpoint | Auth | Description |
| :--- | :--- | :--- | :--- |
| `POST` | `/api/auth/login` | Public | Authenticates citizen or officer; returns session token & user profile |
| `POST` | `/api/auth/register` | Public | Citizen self-registration endpoint |
| `POST` | `/api/auth/logout` | Public | Clears session cookie and invalidates client session |
| `GET` | `/api/auth/me` | Bearer / Cookie | Retrieves profile of currently authenticated user |
| `GET` | `/api/system/health` | Public | Non-blocking telemetry check of Ollama model server |
| `GET` | `/api/wards` | Public | Retrieves distinct ward options |
| `POST` | `/api/grievances` | Citizen | Submits grievance; saves as `Received` & queues background classification |
| `GET` | `/api/citizen/grievances` | Citizen | Retrieves complaints filed by the current citizen (isolated) |
| `GET` | `/api/officer/queue` | Officer | Retrieves ranked queue with filters (`priority`, `category`, `ward`, `status`) |
| `GET` | `/api/officer/grievance/{id}` | Officer | Retrieves grievance details and full audit trail of notes |
| `POST` | `/api/officer/grievance/{id}/status` | Officer | Updates grievance status and appends official officer note |
| `GET` | `/api/insights` | Any Authenticated | Retrieves metrics, category/priority/ward distributions |
| `GET` | `/api/insights/export` | Any Authenticated | Streams entire grievance dataset as downloadable CSV |

---

## 9. Evaluation Criteria & Benchmark Targets

The platform is evaluated against a curated gold-standard benchmark dataset (`data/labelled_grievances.csv`) comprising 60 balanced samples:
* **English**: 20 samples
* **Hindi**: 20 samples
* **Telugu**: 20 samples

```
Benchmark Metrics:
├── Priority Agreement Rate      : Target ≥ 85%
├── Immediate Recall (Emergency) : Target = 100% (Guaranteed by keyword escalation)
├── Language Detection Accuracy  : Target ≥ 95%
├── Needs Review Fallback Rate   : Target ≤ 5% (under active Ollama availability)
└── Zero Data Ingestion Loss     : Target = 100%
```

---

## 10. Operational Playbook & Deployment Guide

### 10.1 Prerequisites
* Python 3.10+ (Tested on Python 3.13)
* Ollama running locally with `llama3.2:3b`:
  ```bash
  ollama run llama3.2:3b
  ```

### 10.2 Installation & Server Launch
```bash
# 1. Clone repository & install dependencies
pip install -r requirements.txt

# 2. Seed demo dataset (optional)
python scripts/seed_sample_data.py

# 3. Launch CivicTriage Web Server
python app.py
```
Server binds to `http://127.0.0.1:8000`.

### 10.3 Default Demo Credentials
* **Citizen Demo**: `citizen@example.com` / `Citizen123`
* **Officer Demo**: `officer@civictriage.gov.in` / `Officer123`

### 10.4 Automated Test Suite
```bash
pytest -v
```
Executes all 24 automated unit and integration tests across database indexes, authentication, keyword escalation, classifier fault tolerance, and REST API routes.

---

## 11. Release Roadmap

* **Phase 1 (Delivered / Current)**:
  * Full migration from Streamlit to high-performance FastAPI + Vanilla HTML5/CSS3/JS architecture.
  * Modern senior-level dark/light UI with glassmorphism, glowing urgency badges, and responsive tables.
  * Multi-script support (EN, HI, TE), background thread pool classification, and SQLite composite indexing.
* **Phase 2 (Near-Term)**:
  * On-device speech-to-text integration (local Whisper model) allowing citizens to record voice grievances directly in Hindi or Telugu.
  * Citizen SMS / WhatsApp notification gateway on status transition.
* **Phase 3 (Long-Term)**:
  * GIS / Mapbox spatial clustering for automatic detection of multi-citizen duplicate complaints (e.g., 10 citizens reporting the same broken water main).
  * Automated municipal departmental SLA timers and escalation alerts.
