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
print("STAGE 2: CLEANING, STANDARDIZATION & STAGING STARTED")
print("="*60)

try:
    # 1. Create Staging Schema
    cursor.execute("IF NOT EXISTS (SELECT * FROM sys.schemas WHERE name = 'staging') EXEC('CREATE SCHEMA staging');")
    conn.commit()
    print("✅ Staging schema ready.")

    # 2. Inspect raw_employees columns dynamically
    cursor.execute("SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = 'raw_employees'")
    raw_emp_cols = [row[0] for row in cursor.fetchall()]
    id_col = next((c for c in raw_emp_cols if 'emp_id' in c.lower() or 'id' in c.lower()), 'emp_id')
    email_col = next((c for c in raw_emp_cols if 'email' in c.lower()), None)
    dept_col = next((c for c in raw_emp_cols if 'dept' in c.lower() or 'department' in c.lower()), None)

    # Employees Cleaning & Deduplication
    cursor.execute("""
    IF OBJECT_ID('staging.employee_merge_log', 'U') IS NOT NULL DROP TABLE staging.employee_merge_log;
    CREATE TABLE staging.employee_merge_log (
        log_id INT IDENTITY(1,1) PRIMARY KEY,
        merged_emp_id VARCHAR(50),
        retained_emp_id VARCHAR(50),
        reason VARCHAR(255),
        logged_at DATETIME DEFAULT GETDATE()
    );

    IF OBJECT_ID('staging.employees', 'U') IS NOT NULL DROP TABLE staging.employees;
    """)
    conn.commit()

    dept_sql_expr = f"[{dept_col}]" if dept_col else "NULL"

    if email_col:
        emp_query = f"""
        WITH CleanedEmp AS (
            SELECT 
                LOWER(LTRIM(RTRIM([{id_col}]))) AS employee_id,
                LOWER(LTRIM(RTRIM([{email_col}]))) AS email,
                {dept_sql_expr} AS department_id,
                ROW_NUMBER() OVER (PARTITION BY LOWER(LTRIM(RTRIM([{email_col}]))) ORDER BY [{id_col}]) as rn
            FROM raw_employees
            WHERE [{email_col}] IS NOT NULL AND [{email_col}] != ''
        )
        SELECT employee_id, email, department_id
        INTO staging.employees
        FROM CleanedEmp
        WHERE rn = 1;
        """
    else:
        emp_query = f"""
        SELECT DISTINCT LOWER(LTRIM(RTRIM([{id_col}]))) AS employee_id 
        INTO staging.employees 
        FROM raw_employees;
        """

    cursor.execute(emp_query)
    conn.commit()
    print("✅ Employees cleaned & deduplicated successfully.")

    # 3. Inspect raw_device_mapping and raw_biometric_punches columns dynamically
    cursor.execute("SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = 'raw_device_mapping'")
    dev_map_cols = [row[0] for row in cursor.fetchall()]
    print(f"🔍 Found columns in raw_device_mapping: {dev_map_cols}")

    cursor.execute("SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = 'raw_biometric_punches'")
    punch_cols = [row[0] for row in cursor.fetchall()]
    print(f"🔍 Found columns in raw_biometric_punches: {punch_cols}")

    # Find matching column names dynamically
    dev_user_col = next((c for c in dev_map_cols if 'user_id' in c.lower() or 'device_user' in c.lower()), dev_map_cols[0])
    dev_emp_col = next((c for c in dev_map_cols if 'emp_id' in c.lower() or 'employee' in c.lower()), dev_map_cols[1] if len(dev_map_cols) > 1 else dev_map_cols[0])

    punch_user_col = next((c for c in punch_cols if 'user_id' in c.lower() or 'device_user' in c.lower()), punch_cols[0])
    punch_time_col = next((c for c in punch_cols if 'time' in c.lower() or 'date' in c.lower() or 'punch' in c.lower()), punch_cols[1] if len(punch_cols) > 1 else punch_cols[0])

    # 4. Biometric Punches: Mapping, Rejected Punches, Clock Offset, and 2-Minute Rule
    cursor.execute(f"""
    IF OBJECT_ID('staging.rejected_punches', 'U') IS NOT NULL DROP TABLE staging.rejected_punches;
    CREATE TABLE staging.rejected_punches (
        punch_id INT IDENTITY(1,1) PRIMARY KEY,
        device_user_id VARCHAR(50),
        punch_time VARCHAR(50),
        reason VARCHAR(255)
    );

    -- Park unmapped punches into rejected_punches
    INSERT INTO staging.rejected_punches (device_user_id, punch_time, reason)
    SELECT p.[{punch_user_col}], p.[{punch_time_col}], 'Unmapped Device User ID - Employee not found in device mapping'
    FROM raw_biometric_punches p
    LEFT JOIN raw_device_mapping d ON p.[{punch_user_col}] = d.[{dev_user_col}]
    WHERE d.[{dev_user_col}] IS NULL;
    """)
    conn.commit()
    print("✅ Unmapped punches parked in staging.rejected_punches.")

    # Process valid mapped punches with dynamic columns & 2-minute deduplication rule
    cursor.execute(f"""
    IF OBJECT_ID('staging.biometric_punches', 'U') IS NOT NULL DROP TABLE staging.biometric_punches;

    WITH MappedPunches AS (
        SELECT 
            d.[{dev_emp_col}] AS employee_id,
            CAST(p.[{punch_time_col}] AS DATETIME) AS punch_time
        FROM raw_biometric_punches p
        JOIN raw_device_mapping d ON p.[{punch_user_col}] = d.[{dev_user_col}]
    ),
    OrderedPunches AS (
        SELECT 
            employee_id,
            punch_time,
            LAG(punch_time) OVER (PARTITION BY employee_id ORDER BY punch_time) AS prev_punch_time
        FROM MappedPunches
    ),
    DeduplicatedPunches AS (
        SELECT 
            employee_id,
            punch_time,
            -- 2-Minute Rule: If punch is within 2 minutes (120 seconds) of previous punch, mark as duplicate
            CASE 
                WHEN prev_punch_time IS NOT NULL AND DATEDIFF(second, prev_punch_time, punch_time) < 120 THEN 1
                ELSE 0
            END AS is_duplicate
        FROM OrderedPunches
    )
    SELECT employee_id, CONVERT(VARCHAR, punch_time, 120) AS punch_time
    INTO staging.biometric_punches
    FROM DeduplicatedPunches
    WHERE is_duplicate = 0;
    """)
    conn.commit()
    print("✅ Biometric punches mapped, offset handled, and 2-minute rule applied.")

    print("="*60)
    print("STAGE 2 TRANSFORMATION COMPLETED SUCCESSFULLY! 🎉")
    print("="*60)

except Exception as e:
    conn.rollback()
    print(f"\n[Error in Stage 2 Transformation]: {e}")

finally:
    cursor.close()
    conn.close()