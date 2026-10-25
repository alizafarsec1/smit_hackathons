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
print("STAGE 6: DATA QUALITY (DQ) CHECKS STARTED")
print("="*60)

try:
    # 1. Create dq_results logging table
    cursor.execute("""
    IF OBJECT_ID('dbo.dq_results', 'U') IS NOT NULL DROP TABLE dbo.dq_results;
    CREATE TABLE dbo.dq_results (
        check_id INT IDENTITY(1,1) PRIMARY KEY,
        check_category VARCHAR(50),
        check_name VARCHAR(150),
        status VARCHAR(20),
        failure_count INT,
        executed_at DATETIME DEFAULT GETDATE()
    );
    """)
    conn.commit()
    print("✅ `dq_results` logging table ready.")

    # Define DQ Checks as (Category, Name, SQL Query checking for FAILURES)
    # If the query returns > 0 rows/count, the check failed.
    checks = [
        # 1. Uniqueness & Not-Null on Primary Keys (Dim Employee)
        (
            "PK Integrity", 
            "dim_employee PK Not Null & Unique", 
            """
            SELECT COUNT(*) FROM (
                SELECT employee_key, COUNT(*) as cnt 
                FROM warehouse.dim_employee 
                WHERE employee_key IS NULL 
                GROUP BY employee_key
                HAVING COUNT(*) > 1 OR COUNT(*) = 0
            ) t
            """
        ),
        # 2. Referential Integrity: Fact Attendance -> Dim Employee
        (
            "Referential Integrity", 
            "fact_attendance_daily -> dim_employee linkage", 
            """
            SELECT COUNT(*) 
            FROM warehouse.fact_attendance_daily f
            LEFT JOIN warehouse.dim_employee d ON f.employee_key = d.employee_key
            WHERE d.employee_key IS NULL
            """
        ),
        # 3. Accepted Values: Attendance Status
        (
            "Accepted Values", 
            "Invalid attendance_status values check", 
            """
            SELECT COUNT(*) 
            FROM warehouse.fact_attendance_daily
            WHERE attendance_status NOT IN ('Present', 'Absent', 'Missing Punch', 'Weekly Off', 'Holiday', 'On Leave')
            """
        ),
        # 4. Business Sanity: No Negative Worked Hours
        (
            "Business Sanity", 
            "Negative worked hours check", 
            """
            SELECT COUNT(*) 
            FROM warehouse.fact_attendance_daily
            WHERE worked_hours < 0
            """
        ),
        # 5. Business Sanity: No Shift Longer Than 16 Hours
        (
            "Business Sanity", 
            "Shift duration exceeds 16 hours check", 
            """
            SELECT COUNT(*) 
            FROM warehouse.fact_attendance_daily
            WHERE worked_hours > 16.0
            """
        ),
        # 6. Business Sanity: No Overlapping SCD Type 2 Ranges in dim_employee
        (
            "Business Sanity", 
            "Overlapping SCD2 effective dates check", 
            """
            SELECT COUNT(*) 
            FROM warehouse.dim_employee e1
            JOIN warehouse.dim_employee e2 
                ON e1.employee_id = e2.employee_id 
                AND e1.employee_key <> e2.employee_key
            WHERE e1.effective_start_date <= ISNULL(e2.effective_end_date, '9999-12-31')
              AND ISNULL(e1.effective_end_date, '9999-12-31') >= e2.effective_start_date
              AND e1.effective_start_date < e2.effective_start_date
            """
        )
    ]

    # Execute each check and log to dq_results
    for category, name, query in checks:
        cursor.execute(query)
        result = cursor.fetchone()
        failure_count = result[0] if result else 0
        status = "PASS" if failure_count == 0 else "FAIL"

        # Insert into dq_results
        cursor.execute("""
            INSERT INTO dbo.dq_results (check_category, check_name, status, failure_count)
            VALUES (?, ?, ?, ?)
        """, (category, name, status, failure_count))
        conn.commit()

        print(f"[{status}] {category} -> {name} (Failures: {failure_count})")

    print("="*60)
    print("STAGE 6 DATA QUALITY CHECKS COMPLETED SUCCESSFULLY! 🎉")
    print("="*60)

except Exception as e:
    conn.rollback()
    print(f"\n[Error in Stage 6 DQ Checks]: {e}")

finally:
    cursor.close()
    conn.close()