# 🏢 PeopleOps Data Engineering Pipeline & Analytics Warehouse

An end-to-end, automated **HR & Attendance Data Pipeline** built using **Python** and **Microsoft SQL Server** (T-SQL). This project extracts raw organizational data (employees, biometric punch logs, leave requests, payroll, shift rosters, etc.), cleans and transforms it through a multi-stage ETL architecture, and loads it into a production-ready **Star Schema Data Warehouse** with **SCD Type 2** tracking and automated Data Quality (DQ) checks.

---

## 📂 Project Directory Structure

```text
First Hackathon/
├── data-hackathon-main/          # Raw Data Source Folder
│   ├── applications.csv
│   ├── biometric_punches.csv
│   ├── data_dictionary.md
│   ├── departments.csv
│   ├── device_mapping.csv
│   ├── employees.csv
│   ├── employment_history.csv
│   ├── holidays.csv
│   ├── leave_requests.json
│   ├── overtime_requests.csv
│   ├── payroll_lines.csv
│   ├── shift_roster.csv
│   └── shifts.json
├── ETL/                          # Core Python ETL Pipeline Modules
│   ├── attendance_logic.py       # Stage 3: Attendance Engine & Calculations
│   ├── dq_checks.py              # Stage 6: Data Quality Assertion Scripts
│   ├── extract.py                # Stage 1: Raw Ingestion to SQL Server
│   ├── run_stage5.py             # Stage 5: Executive CFO & BI Query Execution
│   ├── transform.py              # Stage 2: Data Cleaning & Staging Logic
│   └── warehouse_model.py        # Stage 4: Star Schema Warehouse & DDL Execution
├── Stage5_Outputs/               # Output CSV Reports for Management Queries
└── README.md                     # Project Documentation
```

---

## 📌 Table of Contents

1. [Project Overview](#-project-overview)
2. [Architecture & Pipeline Stages](#-architecture--pipeline-stages)
3. [Core Technical Concepts](#-core-technical-concepts)
4. [Data Warehouse Design (Star Schema)](#-data-warehouse-design-star-schema)
5. [CFO & Financial Leakage Queries](#-cfo--financial-leakage-queries)
6. [Data Quality & Validation](#-data-quality--validation)
7. [Tech Stack](#-tech-stack)
8. [How to Run](#-how-to-run)

---

## 🎯 Project Overview

The primary goal of this project is to eliminate manual data entry, automate attendance status calculations, and provide executive leadership (CFO/HR) with reliable, automated reports on attendance metrics and potential payroll leakages.

### **Key Achievements**
* Processed over **182,000+ daily attendance records**.
* Achieved **100% idempotent loading** via programmatic row hashing (`_row_hash`).
* Implemented **SCD Type 2** tracking for historical employee transfers and attribute changes.
* Automated **Financial Leakage Audits** (detecting payments to separated employees or zero-attendance payouts).
* Enforced **automated Data Quality assertions** across all warehouse layers.

---

## 🏗️ Architecture & Pipeline Stages

```text
[ data-hackathon-main/ ] ──► (CSV & JSON Source Files)
          │
          ▼
 [ Stage 1: extract.py ] ──► Ingests Raw Tables into SQL Server
          │
          ▼
[ Stage 2: transform.py ] ──► Data Cleaning & Rejection Table Audit
          │
          ▼
[ Stage 3: attendance_logic.py ] ──► Present/Late/Absent Rules Engine
          │
          ▼
[ Stage 4: warehouse_model.py ] ──► Fact Tables & Dimensions (SCD Type 2)
          │
          ▼
 [ Stage 5: run_stage5.py ] ──► CFO Analytical Reports (Saved to Stage5_Outputs/)
          │
          ▼
[ Stage 6: dq_checks.py ] ──► 100% Passed Automated DQ Assertions
```

### **Stage Breakdown**

#### **Stage 1: Raw Ingestion (`extract.py`)**
* Ingests unedited CSV and JSON files (`employees.csv`, `biometric_punches.csv`, `payroll_lines.csv`, `shift_roster.csv`, etc.) directly into SQL Server `raw_*` tables using Python (`pandas`, `pyodbc`).
* **Idempotency:** Generates row hashes (`_row_hash`) to prevent duplicate insertions on pipeline re-runs.

#### **Stage 2: Staging & Data Cleaning (`transform.py`)**
* Normalizes strings, cleans whitespace, and formats timestamps.
* Diverts orphaned or corrupt biometric punches (e.g., punches referencing non-existent employee IDs) to a dedicated `rejected_punches` table to maintain pipeline stability.

#### **Stage 3: Attendance Logic Engine (`attendance_logic.py`)**
* Compares raw biometric check-in and check-out timestamps against employee shift rosters.
* Evaluates rule-based status classifications: `Present`, `Late`, `Absent`, or `Missing Punch`.
* Outputs over 182,000+ processed daily attendance records.

#### **Stage 4: Data Warehouse Modeling (`warehouse_model.py`)**
* Builds T-SQL Schema (`warehouse`) containing dimensional models for optimized reporting.
* **Dimensions:** `dim_employee` (with **SCD Type 2** for history tracking), `dim_date`, `dim_shift`.
* **Fact Tables:** `fact_attendance_daily` and `fact_leave_day` containing core quantitative metrics.

#### **Stage 5: Business Intelligence & CFO Queries (`run_stage5.py`)**
* Executes advanced analytical SQL queries (utilizing `CTEs`, `Window Functions`, and `JOINs`) to answer executive business questions.
* Automatically exports analytical audit reports to the `Stage5_Outputs/` folder.

#### **Stage 6: Automated Data Quality Verification (`dq_checks.py`)**
* Runs automated Python/SQL test scripts to enforce core warehouse rules:
  1. **Primary Key Uniqueness** (Zero duplicate keys).
  2. **Referential Integrity** (Fact FKs correctly link to Dimension PKs).
  3. **Domain Constraints** (Valid values for categories like Gender, Attendance Status).
  4. **Business Logic Sanity** (No negative worked hours or invalid shift durations).

---

## 🔑 Core Technical Concepts

| Concept | Implementation in Project |
| :--- | :--- |
| **Idempotency** | Prevents duplicate data entry by computing `_row_hash` for every ingested record. Re-running scripts leaves the warehouse state consistent. |
| **SCD Type 2** | Preserves historical context for changing attributes (e.g., department transfers) in `dim_employee` by creating new versioned rows with effective dates. |
| **Star Schema** | Separates quantitative facts (`fact_attendance_daily`, `fact_leave_day`) from descriptive dimensions (`dim_employee`, `dim_date`, `dim_shift`). |
| **Audit Pattern** | Isolates bad/corrupt records into rejection tables (`rejected_punches`) without halting the main ETL execution. |

---

## 🗄️ Data Warehouse Design (Star Schema)

```text
                        ┌─────────────────────────────────┐
                        │      warehouse.dim_employee     │ (SCD Type 2)
                        ├─────────────────────────────────┤
                        │ PK   employee_key               │
                        │      employee_id                │
                        │      employee_name              │
                        │      effective_start_date       │
                        │      effective_end_date         │
                        │      is_current                 │
                        └────────────────┬────────────────┘
                                         │
                                         │ 1:N
┌──────────────────────┐                 ▼                 ┌─────────────────────┐
│  warehouse.dim_shift │ 1:N ┌───────────────────────────┐ 1:N │  warehouse.dim_date │
├──────────────────────┤ ──► │warehouse.fact_attendance_ │ ◄── ├─────────────────────┤
│ PK   shift_key       │     │          daily            │     │ PK   date_key       │
└──────────────────────┘     ├───────────────────────────┤     └─────────────────────┘
                             │ PK  attendance_fact_key   │
                             │ FK  employee_key          │
                             │ FK  date_key              │
                             │ FK  shift_key             │
                             │     first_check_in        │
                             │     last_check_out        │
                             │     worked_hours          │
                             │     attendance_status     │
                             └───────────────────────────┘
```

---

## 📊 Sample SQL Analytics (CFO Queries)

```sql
-- Query Example: Detect Pay After Separation
WITH SeparatedEmployees AS (
    SELECT 
        employee_id,
        resignation_date
    FROM warehouse.dim_employee
    WHERE resignation_date IS NOT NULL AND is_current = 1
)
SELECT 
    p.employee_id,
    p.pay_date,
    p.net_salary,
    e.resignation_date
FROM raw_payroll p
JOIN SeparatedEmployees e ON p.employee_id = e.employee_id
WHERE p.pay_date > e.resignation_date;
```

---

## 🛠️ Tech Stack

* **Language:** Python 3.x
* **Database / Warehouse:** Microsoft SQL Server (T-SQL)
* **Python Libraries:** `pandas`, `pyodbc`, `hashlib`, `datetime`, `json`
* **Modeling & Design:** Star Schema Dimensional Modeling, SCD Type 2

---

## 🚀 How to Run

1. **Prerequisites:**
   * Installed Python 3.10+
   * Installed Microsoft SQL Server instance & ODBC Driver.

2. **Environment Setup:**
   ```bash
   pip install pandas pyodbc
   ```

3. **Database Configuration:**
   * Ensure SQL Server is running and configure connection settings in the `ETL/` modules if needed.

4. **Execute ETL Stages in Order:**
   ```bash
   python ETL/extract.py
   python ETL/transform.py
   python ETL/attendance_logic.py
   python ETL/warehouse_model.py
   python ETL/run_stage5.py
   python ETL/dq_checks.py
   ```