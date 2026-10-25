import pyodbc

# SQL Server Connection
conn = pyodbc.connect(
    'DRIVER={ODBC Driver 17 for SQL Server};'
    'SERVER=ALI-PC;'
    'DATABASE=indux_db;'
    'Trusted_Connection=yes;'
)
conn.autocommit = False
cursor = conn.cursor()

print("="*60)
print("STAGE 4: WAREHOUSE MODELING & STAR SCHEMA DDL STARTED")
print("="*60)

try:
    # 1. Create Warehouse Schema
    cursor.execute("IF NOT EXISTS (SELECT * FROM sys.schemas WHERE name = 'warehouse') EXEC('CREATE SCHEMA warehouse');")
    conn.commit()
    print("✅ Warehouse schema ready.")

    # 2. Create Dimension Tables
    cursor.execute("""
    -- Dim Date
    IF OBJECT_ID('warehouse.dim_date', 'U') IS NOT NULL DROP TABLE warehouse.dim_date;
    CREATE TABLE warehouse.dim_date (
        date_key INT PRIMARY KEY,
        full_date DATE UNIQUE,
        year INT,
        quarter INT,
        month INT,
        day INT,
        day_of_week VARCHAR(15),
        is_weekend BIT
    );

    -- Dim Department
    IF OBJECT_ID('warehouse.dim_department', 'U') IS NOT NULL DROP TABLE warehouse.dim_department;
    CREATE TABLE warehouse.dim_department (
        department_key INT IDENTITY(1,1) PRIMARY KEY,
        department_id VARCHAR(50) UNIQUE,
        department_name VARCHAR(100)
    );

    -- Dim Shift
    IF OBJECT_ID('warehouse.dim_shift', 'U') IS NOT NULL DROP TABLE warehouse.dim_shift;
    CREATE TABLE warehouse.dim_shift (
        shift_key INT IDENTITY(1,1) PRIMARY KEY,
        shift_id VARCHAR(50) UNIQUE,
        start_time TIME,
        end_time TIME,
        is_weekend BIT
    );

    -- Dim Employee (SCD Type 2 structure)
    IF OBJECT_ID('warehouse.dim_employee', 'U') IS NOT NULL DROP TABLE warehouse.dim_employee;
    CREATE TABLE warehouse.dim_employee (
        employee_key INT IDENTITY(1,1) PRIMARY KEY,
        employee_id VARCHAR(50),
        full_name VARCHAR(150),
        email VARCHAR(150),
        department_id VARCHAR(50),
        effective_start_date DATE,
        effective_end_date DATE,
        is_current BIT
    );
    """)
    conn.commit()
    print("✅ Dimension tables created successfully.")

    # 3. Create Fact Tables with Foreign Key Constraints
    cursor.execute("""
    -- Fact Attendance Daily
    IF OBJECT_ID('warehouse.fact_attendance_daily', 'U') IS NOT NULL DROP TABLE warehouse.fact_attendance_daily;
    CREATE TABLE warehouse.fact_attendance_daily (
        attendance_fact_key INT IDENTITY(1,1) PRIMARY KEY,
        employee_key INT FOREIGN KEY REFERENCES warehouse.dim_employee(employee_key),
        date_key INT FOREIGN KEY REFERENCES warehouse.dim_date(date_key),
        shift_key INT FOREIGN KEY REFERENCES warehouse.dim_shift(shift_key),
        first_check_in TIME,
        last_check_out TIME,
        worked_hours DECIMAL(5,2),
        attendance_status VARCHAR(50)
    );

    -- Fact Leave Day
    IF OBJECT_ID('warehouse.fact_leave_day', 'U') IS NOT NULL DROP TABLE warehouse.fact_leave_day;
    CREATE TABLE warehouse.fact_leave_day (
        leave_fact_key INT IDENTITY(1,1) PRIMARY KEY,
        employee_key INT FOREIGN KEY REFERENCES warehouse.dim_employee(employee_key),
        date_key INT FOREIGN KEY REFERENCES warehouse.dim_date(date_key),
        leave_type VARCHAR(50),
        status VARCHAR(50)
    );

    -- Fact Overtime Approved
    IF OBJECT_ID('warehouse.fact_overtime_approved', 'U') IS NOT NULL DROP TABLE warehouse.fact_overtime_approved;
    CREATE TABLE warehouse.fact_overtime_approved (
        overtime_fact_key INT IDENTITY(1,1) PRIMARY KEY,
        employee_key INT FOREIGN KEY REFERENCES warehouse.dim_employee(employee_key),
        date_key INT FOREIGN KEY REFERENCES warehouse.dim_date(date_key),
        overtime_hours DECIMAL(5,2)
    );

    -- Fact Payroll Line
    IF OBJECT_ID('warehouse.fact_payroll_line', 'U') IS NOT NULL DROP TABLE warehouse.fact_payroll_line;
    CREATE TABLE warehouse.fact_payroll_line (
        payroll_fact_key INT IDENTITY(1,1) PRIMARY KEY,
        employee_key INT FOREIGN KEY REFERENCES warehouse.dim_employee(employee_key),
        date_key INT FOREIGN KEY REFERENCES warehouse.dim_date(date_key),
        amount DECIMAL(10,2),
        component_type VARCHAR(100)
    );
    """)
    conn.commit()
    print("✅ Fact tables created with enforced Foreign Keys successfully.")

    print("="*60)
    print("STAGE 4 WAREHOUSE MODELING COMPLETED SUCCESSFULLY! 🎉")
    print("="*60)

except Exception as e:
    conn.rollback()
    print(f"\n[Error in Stage 4]: {e}")

finally:
    cursor.close()
    conn.close()