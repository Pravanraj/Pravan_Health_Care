# Healthcare Patient Management System (Pravan_Healthcare)

[![Python Version](https://img.shields.io/badge/Python-3.12-blue.svg)](https://www.python.org/)
[![Framework](https://img.shields.io/badge/Backend-FastAPI-009688.svg)](https://fastapi.tiangolo.com/)
[![Frontend](https://img.shields.io/badge/Frontend-Streamlit-FF4B4B.svg)](https://streamlit.io/)
[![Database](https://img.shields.io/badge/Database-SQLite%20%2F%20PostgreSQL-336791.svg)](https://www.sqlite.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

An enterprise-grade, full-stack Healthcare Patient Management System designed for historical clinical data ingestion, relational persistence, role-governed REST APIs, and operational analytics. Developed for the Capstone Project based on the **Diabetes 130-US Hospitals (1999–2008)** clinical dataset.

---

## 1. Project Overview

Healthcare institutions manage massive volumes of inpatient admission records, clinical procedures, diagnostic findings, laboratory measurements, and medication regimens. Manual handling of tabular files leads to operational delays, reporting inconsistencies, and elevated risks of preventable hospital readmissions.

This application provides an automated end-to-end data processing and clinical management platform that:
1. Cleans, validates, and normalizes raw clinical datasets.
2. Persists curated data into a 3NF relational schema with indexing and audit logs.
3. Exposes high-throughput REST APIs secured with JWT-based Role-Based Access Control (RBAC).
4. Serves interactive executive dashboards and clinical analytics via a Streamlit web portal.
5. Supports incremental delta loading and scheduled operational reporting.

---

## 2. Problem Statement & Business Objectives

### Problem Statement
Healthcare executives, physicians, and clinical analysts face critical challenges in monitoring inpatient flows and preventing 30-day hospital readmissions:
- **Trend Identification**: Inability to quickly track admissions and readmission surges over time.
- **Length of Stay (LOS) Drivers**: Ambiguity regarding how clinical acuity and patient age influence inpatient duration.
- **High-Risk Categories**: Identifying which diagnostic groups and medication adjustments correlate with rapid hospital returns.
- **Data Governance & Security**: Enabling authorized staff to search, create, and update patient records while maintaining strict HIPAA-compliant audit trails.

### Business Objectives
- **Automate Ingestion**: Replace manual spreadsheet ingestion with an automated Python ETL pipeline enforcing data quality rules.
- **Drive Operational Insights**: Answer key clinical questions regarding admission volume, readmission rates, and length of stay variations.
- **Enforce Role-Based Governance**: Protect patient health information with role-based permissions (`Administrator`, `Clinical Operations`, `Analyst`).
- **Provide Actionable Reporting**: Enable one-click export of curated patient records to CSV and Excel, alongside automated executive summaries.

---

## 3. Technology Stack

- **Programming Language**: Python 3.12
- **Backend Framework**: FastAPI (Asynchronous REST microservice with OpenAPI/Swagger documentation)
- **ASGI Web Server**: Uvicorn
- **ORM & Data Layer**: SQLAlchemy 2.0 (with connection pooling and type hints)
- **Database**: SQLite (Default zero-configuration local engine) / PostgreSQL compatible
- **Data Engineering & ETL**: Pandas, NumPy
- **Frontend Portal**: Streamlit (Reactive clinical dashboards and forms)
- **Security & Cryptography**: Passlib (Bcrypt hashing), Python-Jose (JWT bearer tokens)
- **Reporting & Visualization**: OpenPyXL, ReportLab, Matplotlib, Seaborn, Python-PPTX
- **Testing Suite**: Pytest, HTTPX

---

## 4. Repository & Directory Structure

```
ProjectRepository/
├── architecture/
│   └── Architecture_Diagram.pdf       # High-level architecture diagram (PDF)
├── design/
│   └── Design_Document.pdf            # Comprehensive technical design document (PDF)
├── src/
│   ├── api/                           # FastAPI routers (auth, patients, encounters, analytics, reports, etl)
│   ├── services/                      # Domain business services (patient, encounter, analytics, report)
│   ├── utils/                         # Security helpers, structured logger, and auth utilities
│   ├── etl/                           # Cleaner, data quality engine, pipeline, and CLI runner
│   ├── database/                      # SQLAlchemy connection, seed users, and 3NF models
│   └── main.py                        # FastAPI application entrypoint
├── data/
│   ├── IDS_mapping.csv                # Complete reference lookup codes mapping
│   └── diabetic_data.csv              # Full real dataset (101,766 encounters, 71,520 patients)
├── docs/
│   ├── API_Documentation.pdf          # REST API specifications and curl samples (PDF)
│   ├── Dataset_Details.pdf            # Clinical attributes & HIPAA documentation (PDF)
│   └── Evaluation_Report.pdf          # Benchmark results & test coverage report (PDF)
├── tests/                             # Automated Pytest suite (ETL, DQ, API, RBAC, DB)
├── presentation/
│   └── Project_Presentation.pptx      # Capstone panel presentation deck (PPTX)
├── frontend.py                        # Streamlit Interactive Management Portal
├── requirements.txt                   # Locked Python dependencies
├── README.md                          # Project documentation
└── .gitignore                         # Standard git ignore definitions
```

---

## 5. Installation & Environment Setup

### Step 1: Clone or Navigate to Project Directory
```bash
cd "/Users/pravan/Downloads/capstone project"
```

### Step 2: Create and Activate Virtual Environment
```bash
python3 -m venv venv
source venv/bin/activate
```

### Step 3: Install Required Dependencies
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### Step 4: Configure Database (Optional)
By default, the application runs on high-performance local SQLite (`healthcare.db`). To connect to an external PostgreSQL instance, set the environment variable:
```bash
export DATABASE_URL="postgresql://user:password@localhost:5432/healthcare_db"
```

---

## 6. ETL Execution Instructions

### Ingest Full Historical Clinical Dataset (101,766 records)
```bash
python -m src.etl.run_etl --data data/diabetic_data.csv --mapping data/IDS_mapping.csv --type INITIAL
```
The ingestion cleans missing values (`?`), validates 5 healthcare data quality rules, classifies ICD-9 diagnosis codes into clinical categories, synthesizes chronological admission/discharge dates, and performs chunked bulk insertion into the normalized 3NF database schema.

### Execute Incremental Batch Loading
To ingest a newly arrived batch of clinical encounters:
```bash
python -m src.etl.run_etl --data path/to/incremental_batch.csv --mapping data/IDS_mapping.csv --type INCREMENTAL
```

---

## 7. Local Deployment Instructions

### 1. Launch FastAPI Backend Microservice
Run Uvicorn from the project root:
```bash
uvicorn src.main:app --host 127.0.0.1 --port 8000 --reload
```
- Interactive Swagger UI: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- ReDoc Documentation: [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)
- Health Probe: [http://127.0.0.1:8000/health](http://127.0.0.1:8000/health)

### 2. Launch Streamlit User Interface
In a new terminal window (with virtual environment active):
```bash
streamlit run frontend.py --server.port 8501
```
- Open your browser to [http://localhost:8501](http://localhost:8501) to explore the interactive dashboards and patient management portal.

---

## 8. Role-Based Access Control (RBAC) Accounts

Default pre-configured accounts:

| Username | Password | Role | Permissions |
| :--- | :--- | :--- | :--- |
| **`admin`** | `AdminPassword123!` | `administrator` | Full Access: Patient/Encounter CRUD, Deletion, Incremental ETL, Audit Log Inspection |
| **`clinician`** | `ClinicianPass123!` | `clinical_operations` | Patient & Encounter CRUD, Clinical Analytics, Report Downloads |
| **`analyst`** | `AnalystPass123!` | `analyst` | Read-Only on Clinical Records, Full Analytics, Dataset Exports |

---

## 9. Sample API Requests and Responses

### 1. User Authentication (Login)
**Request:**
```bash
curl -X POST "http://127.0.0.1:8000/api/v1/auth/login" \
     -H "Content-Type: application/x-www-form-urlencoded" \
     -d "username=clinician&password=ClinicianPass123!"
```
**Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "role": "clinical_operations",
  "username": "clinician",
  "full_name": "Dr. Sarah Adams (Operations)"
}
```

### 2. Hospital Operational KPIs
**Request:**
```bash
curl -X GET "http://127.0.0.1:8000/api/v1/analytics/summary-kpis"
```
**Response:**
```json
{
  "total_encounters": 101766,
  "total_patients": 71518,
  "avg_length_of_stay": 4.4,
  "readmission_rate_30d_pct": 11.16,
  "readmission_rate_total_pct": 46.09,
  "mortality_rate_pct": 2.25,
  "readmitted_30d_count": 11357,
  "mortality_count": 2289
}
```

### 3. Search Patients with Filters & Pagination
**Request:**
```bash
curl -X GET "http://127.0.0.1:8000/api/v1/patients?page=1&page_size=2&gender=Female&race=Caucasian"
```
**Response:**
```json
{
  "total": 39689,
  "page": 1,
  "page_size": 2,
  "items": [
    {
      "patient_nbr": 8222157,
      "race": "Caucasian",
      "gender": "Female",
      "age_bracket": "[0-10)",
      "created_at": "2026-10-11T10:00:00",
      "updated_at": "2026-10-11T10:00:00"
    },
    {
      "patient_nbr": 55629189,
      "race": "Caucasian",
      "gender": "Female",
      "age_bracket": "[10-20)",
      "created_at": "2026-10-11T10:00:00",
      "updated_at": "2026-10-11T10:00:00"
    }
  ]
}
```

### 4. Create New Patient Record (RBAC Protected)
**Request:**
```bash
curl -X POST "http://127.0.0.1:8000/api/v1/patients" \
     -H "Content-Type: application/json" \
     -H "Authorization: Bearer <ADMIN_OR_CLINICAL_TOKEN>" \
     -d '{
       "patient_nbr": 88888001,
       "race": "Hispanic",
       "gender": "Female",
       "age_bracket": "[50-60)"
     }'
```
**Response:**
```json
{
  "patient_nbr": 88888001,
  "race": "Hispanic",
  "gender": "Female",
  "age_bracket": "[50-60)",
  "created_at": "2026-10-11T10:15:00",
  "updated_at": "2026-10-11T10:15:00"
}
```

---

## 10. Sample SQL / User Queries & Expected Outputs

### Query 1: What is the 30-day readmission rate across primary clinical diagnosis categories?
```sql
SELECT 
    d.category_name AS diagnosis_category,
    COUNT(e.encounter_id) AS total_encounters,
    SUM(CASE WHEN o.readmitted_30d = 1 THEN 1 ELSE 0 END) AS readmitted_30d_count,
    ROUND(SUM(CASE WHEN o.readmitted_30d = 1 THEN 1.0 ELSE 0.0 END) / COUNT(e.encounter_id) * 100, 2) AS readmit_rate_pct
FROM encounters e
JOIN diagnoses d ON e.encounter_id = d.encounter_id AND d.diag_seq = 1
JOIN outcomes o ON e.encounter_id = o.encounter_id
GROUP BY d.category_name
ORDER BY total_encounters DESC;
```
**Expected Output:**
| diagnosis_category | total_encounters | readmitted_30d_count | readmit_rate_pct |
| :--- | :--- | :--- | :--- |
| Circulatory | 30,437 | 3,464 | 11.38% |
| Diabetes | 8,757 | 1,091 | 12.46% |
| Respiratory | 14,424 | 1,602 | 11.11% |
| Digestive | 9,475 | 988 | 10.43% |
| Genitourinary | 5,117 | 567 | 11.08% |

---

### Query 2: How does Length of Stay vary across patient age brackets?
```sql
SELECT 
    p.age_bracket,
    COUNT(e.encounter_id) AS total_admissions,
    ROUND(AVG(e.time_in_hospital), 2) AS avg_los_days,
    MIN(e.time_in_hospital) AS min_los,
    MAX(e.time_in_hospital) AS max_los
FROM patients p
JOIN encounters e ON p.patient_nbr = e.patient_nbr
GROUP BY p.age_bracket
ORDER BY p.age_bracket;
```
**Expected Output:**
| age_bracket | total_admissions | avg_los_days | min_los | max_los |
| :--- | :--- | :--- | :--- | :--- |
| [0-10) | 161 | 2.54 | 1 | 14 |
| [10-20) | 691 | 3.19 | 1 | 14 |
| [40-50) | 9,685 | 4.03 | 1 | 14 |
| [70-80) | 26,068 | 4.67 | 1 | 14 |
| [80-90) | 17,197 | 4.82 | 1 | 14 |

---

### Query 3: What is the impact of insulin dosage changes on rapid 30-day readmission?
```sql
SELECT 
    m.dosage_change AS insulin_status,
    COUNT(m.encounter_id) AS patient_count,
    SUM(CASE WHEN o.readmitted_30d = 1 THEN 1 ELSE 0 END) AS readmitted_30d,
    ROUND(SUM(CASE WHEN o.readmitted_30d = 1 THEN 1.0 ELSE 0.0 END) / COUNT(m.encounter_id) * 100, 2) AS readmit_rate_pct
FROM medications m
JOIN outcomes o ON m.encounter_id = o.encounter_id
WHERE m.medication_name = 'insulin'
GROUP BY m.dosage_change
ORDER BY readmit_rate_pct DESC;
```
**Expected Output:**
| insulin_status | patient_count | readmitted_30d | readmit_rate_pct |
| :--- | :--- | :--- | :--- |
| Down | 12,218 | 1,643 | 13.45% |
| Up | 11,316 | 1,489 | 13.16% |
| Steady | 30,849 | 3,365 | 10.91% |

---

## 11. Automated Testing Execution

To run the full suite of automated unit, integration, and security tests:
```bash
pytest tests/ -v
```

All 5 test suites evaluate data cleaning, duplicate detection, schema integrity, REST endpoints, and RBAC security rules.

---

## 12. Regenerating Capstone Submission Deliverables

All submission PDFs and the PowerPoint presentation can be programmatically regenerated at any time using:
```bash
python scripts/generate_artifacts.py
```
This produces:
- `architecture/Architecture_Diagram.pdf` & `architecture/architecture_diagram.png`
- `design/Design_Document.pdf`
- `docs/API_Documentation.pdf`
- `docs/Dataset_Details.pdf`
- `docs/Evaluation_Report.pdf`
- `presentation/Project_Presentation.pptx`
