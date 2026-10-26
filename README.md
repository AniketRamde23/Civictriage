# CivicTriage — Multilingual Civic Grievance Triage & Urgency Ranking System

> **B.Tech Final-Year Capstone Project**  
> A lightweight, robust, and explainable AI-powered civic grievance triage web platform designed for Indian municipal corporations.

---

## 1. Executive Summary & Problem Statement

Municipal offices receive large volumes of citizen grievances across municipal domains (Water, Roads, Sanitation, Electricity, and Other) in multiple regional languages (English, Hindi, and Telugu). Manual classification causes severe delays in addressing life-threatening emergencies (e.g., live electrical wires, open manholes) while routine requests consume frontline staff bandwidth.

**CivicTriage** automates grievance intake, triage, and ranking:
1. **Immediate Persistence**: Saves complaints instantly with status `Received` before any inference begins.
2. **Language Detection & Multilingual Understanding**: Detects English, Hindi, and Telugu; passes native text directly to a small local LLM (`llama3.2:3b` via Ollama) with strict prompt constraints to extract emotion, category, priority, and an English summary.
3. **Hybrid Urgency Triage**: Combines structured LLM reasoning with a deterministic safety keyword escalation rule (promotes `Routine -> Soon -> Immediate`, never lowers priority).
4. **Prioritized Action Queue**: Ranks complaints for municipal officers by urgency (`Immediate > Soon > Routine`) and age (oldest first), complete with plain-language explanations.
5. **Transparency & Citizen Feedback Loop**: Citizens track real-time grievance status and read notes added by inspecting officers.

---

## 2. System Architecture & Tech Stack

```
   ┌─────────────────────────────────────────────────────────────┐
   │             Modern Web Application (HTML5/CSS3/JS)          │
   │  ┌───────────────────────────┐ ┌──────────────────────────┐ │
   │  │    Citizen Portal         │ │    Officer Triage Queue  │ │
   │  │ (Submit & Track Receipts) │ │  (Ranked Queue, Filters) │ │
   │  └─────────────┬─────────────┘ └─────────────┬────────────┘ │
   └────────────────┼─────────────────────────────┼──────────────┘
                    │                             │
                    ▼                             ▼
   ┌─────────────────────────────────────────────────────────────┐
   │           FastAPI REST API Server (app.py)                  │
   │  ┌───────────────────────────┐ ┌──────────────────────────┐ │
   │  │  Session Auth & Endpoints │ │  Background Worker Pool  │ │
   │  └─────────────┬─────────────┘ └─────────────▲────────────┘ │
   └────────────────┼─────────────────────────────┼──────────────┘
                    │                             │
                    ▼                             ▼
   ┌─────────────────────────────────────────────────────────────┐
   │                        Core Logic                           │
   │  ┌───────────────────────────┐ ┌──────────────────────────┐ │
   │  │  langdetect (EN, HI, TE)  │ │  rules.py (Escalation)   │ │
   │  └─────────────┬─────────────┘ └─────────────▲────────────┘ │
   │                │                             │              │
   │                ▼                             │              │
   │  ┌───────────────────────────┐               │              │
   │  │ classifier.py / Ollama    ├───────────────┘              │
   │  │ (JSON mode, retry-once,   │                              │
   │  │  Needs Review fallback)   │                              │
   │  └───────────────────────────┘                              │
   └────────────────┬────────────────────────────────────────────┘
                    │
                    ▼
   ┌─────────────────────────────────────────────────────────────┐
   │             SQLite Database (civictriage.db)                │
   │  - Parameterised Queries (Zero SQL Injection)               │
   │  - Multi-Column Indexes (Sub-30ms Latency for 500+ records) │
   │  - Strict Role-Gated Citizen Data Isolation                 │
   └─────────────────────────────────────────────────────────────┘
```

- **Frontend**: Modern Vanilla HTML5, CSS3, JavaScript (responsive single-page application with role-based navigation)
- **App & API Server**: FastAPI + Uvicorn (RESTful architecture, asynchronous background workers)
- **Local LLM Engine**: Ollama serving `llama3.2:3b` (endpoint: `http://localhost:11434`)
- **Language Detection**: `langdetect` + Unicode script boundary verification
- **Database**: SQLite3 with WAL mode, composite indexes, and parameterised queries
- **Data Visualization**: Dynamic Responsive CSS Grid/Flex Analytics, Real-Time KPI Cards & CSV Export Engine
- **Authentication**: `bcrypt` salted password hashing with signed `itsdangerous` session tokens
- **Automated Testing**: `pytest`

---

## 3. Directory Structure

```
Shivaram/
├── app.py                      # Production FastAPI server, REST API endpoints & static router
├── requirements.txt            # Python dependencies
├── .env.example                # Sample environment configuration
├── config/
│   └── keywords.json           # Escalation safety keywords across EN, HI, TE
├── core/
│   ├── db.py                   # SQLite schema, migrations, connection pool & queries
│   ├── auth.py                 # Bcrypt hashing, citizen registration, authentication
│   ├── lang.py                 # Language detection wrapper
│   ├── prompts.py              # Strict few-shot multilingual prompts
│   ├── rules.py                # Keyword priority escalation logic
│   ├── classifier.py           # Ollama JSON caller, validator, retry-once, fallback
│   └── background.py           # Asynchronous threaded worker pool
├── static/
│   ├── index.html              # Modern responsive web application (Citizen, Officer, Insights)
│   ├── css/
│   │   └── style.css           # Glassmorphic responsive styling, dark/light design system
│   └── js/
│       └── app.js              # Vanilla JS state manager, REST API client & dynamic DOM router
├── scripts/
│   ├── create_officer.py       # Administrative CLI to provision officers
│   ├── seed_sample_data.py     # Seeds demo accounts & 60 gold-labelled records
│   ├── evaluate.py             # Evaluates accuracy, confusion matrix, fallback rate
│   └── demo_walkthrough.py     # End-to-end headless CLI demo script
├── data/
│   └── labelled_grievances.csv # 60 gold-labelled multilingual samples
├── Doc/
│   ├── PRD_CivicTriage.md      # Product Requirements Document
│   └── TECHNICAL_SPECIFICATION_AND_ALGORITHMS.md # Comprehensive Technology & Algorithms Guide
├── Docs/
│   ├── labelling_guide.md      # Ground-truth criteria for Immediate, Soon, Routine
│   └── PRD_CivicTriage.md      # Mirrored PRD specification
└── tests/
    ├── test_auth.py            # Password hashing & citizen isolation tests
    ├── test_classifier.py      # LLM JSON validation & retry-once tests
    ├── test_rules.py           # Keyword escalation tests (raise-only)
    ├── test_queue.py           # Queue ranking order (urgency + age) tests
    └── test_web_api.py         # FastAPI REST endpoints, auth, and static routing tests
```

---

## 4. Getting Started & Setup Guide

### Step 1: Install Python Dependencies
Ensure Python 3.10+ is installed:
```bash
pip install -r requirements.txt
```

### Step 2: Configure Environment Variables
Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```
Default configuration:
```ini
OLLAMA_URL=http://localhost:11434
OLLAMA_MODEL=llama3.2:3b
DATABASE_PATH=civictriage.db
```

### Step 3: Install & Start Ollama (Optional for AI classification)
1. Download Ollama from [https://ollama.com](https://ollama.com).
2. Pull the lightweight 3B model:
   ```bash
   ollama pull llama3.2:3b
   ```
3. Start the Ollama server:
   ```bash
   ollama serve
   ```
> **Fault Tolerance Note**: If Ollama is not running, CivicTriage gracefully marks records as **Needs Review** without crashing or dropping grievances. Deterministic safety keyword escalation continues to function normally.

### Step 4: Seed Demo Data & Initial Accounts
Run the seed script to create initial demo credentials and load the 60 gold-standard records:
```bash
python scripts/seed_sample_data.py
```
**Demo Credentials**:
- **Citizen**: `citizen@example.com` / `Citizen123`
- **Municipal Officer**: `officer@civictriage.gov.in` / `Officer123`

---

## 5. Running the Application

Launch the CivicTriage web application:
```bash
python app.py
```
Or run directly with Uvicorn:
```bash
uvicorn app:app --port 8000 --reload
```
Open your browser and navigate to: `http://localhost:8000`

### Provisioning New Municipal Officers
Citizens can self-register through the web interface, but **officers cannot self-register**. To provision a new officer:
```bash
python scripts/create_officer.py --name "Officer Sharma" --email "sharma@ward4.gov.in" --password "SecurePass123"
```

---

## 6. Testing & Evaluation

### Run Test Suite
Run the 24 automated unit and integration tests with `pytest`:
```bash
pytest -v
```
**Verified Behaviors**:
- Bcrypt password hashing and verification
- Citizen data isolation (Citizen A cannot access Citizen B's complaints)
- Officer role enforcement
- Strict JSON validation, case-normalization, and retry-once logic
- Graceful `Needs Review` fallback on network failure
- Keyword escalation (raise-only: `Routine -> Soon`, `Soon -> Immediate`, never lower)
- Queue sorting order (`Immediate > Soon > Routine`, oldest first)
- FastAPI REST endpoints, session cookies/tokens, static file routing, and insights telemetry

### Run Benchmark Evaluation
Run the automated benchmark across the 60 multilingual test samples:
```bash
# If Ollama is running live:
python scripts/evaluate.py

# If running in simulation/mock mode:
python scripts/evaluate.py --mock
```

**Benchmark Results**:
- **Overall Priority Agreement**: **98.3%** *(Target: >= 80%)*
- **Needs Review Rate**: **0.0%** *(Target: < 5%)*
- **Per-Language Agreement**:
  - English: **95.0%** (19/20)
  - Hindi: **100.0%** (20/20)
  - Telugu: **100.0%** (20/20)

### Run 500-Record Performance Latency Check
Verify that the officer queue loads in under 3 seconds with 500+ records:
```bash
python scripts/seed_sample_data.py --perf 500
```
**Benchmark Output**:
```
Total records in queue : 560
Query Execution Time   : 21.13 ms (0.0211 seconds)
PERFORMANCE TARGET MET : Officer queue loaded in < 3.0 seconds!
```

---

## 7. Headless End-to-End Walkthrough Script

To demonstrate the full lifecycle (`submit -> save -> classify -> rank -> update status -> view insights`) without a browser:
```bash
python scripts/demo_walkthrough.py
```

---

## 8. Academic Scope, Assumptions & Limitations

1. **Typed Text Input Only**: Voice/audio notes and photo attachments are excluded from this core prototype.
2. **Deterministic Fallbacks**: When LLM output fails schema validation twice or Ollama is offline, the status defaults to `Needs Review` and the reason explains the fallback. No records are ever deleted.
3. **Language Scope**: English, Hindi (Devanagari), and Telugu (Telugu script). Transliterated text is handled by rule keywords.
4. **Data Isolation**: Citizen isolation is enforced in SQL queries (`WHERE user_id = ?`), preventing client-side data leakage.
