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
print("STAGE 3: BUSINESS LOGIC & ATTENDANCE DAILY STARTED")
print("="*60)

try:
    # Build staging.attendance_daily directly from biometric punches and shift roster week_start
    cursor.execute("""
    IF OBJECT_ID('staging.attendance_daily', 'U') IS NOT NULL DROP TABLE staging.attendance_daily;

    -- Step 1: Aggregate daily biometric punches per employee per day
    WITH DailyPunches AS (
        SELECT 
            employee_id,
            CAST(punch_time AS DATE) AS work_date,
            MIN(CAST(punch_time AS TIME)) AS first_check_in,
            MAX(CAST(punch_time AS TIME)) AS last_check_out
        FROM staging.biometric_punches
        GROUP BY employee_id, CAST(punch_time AS DATE)
    ),
    -- Step 2: Get Roster entries (handling week_start)
    RosterEntries AS (
        SELECT DISTINCT
            emp_id AS employee_id,
            TRY_CAST(week_start AS DATE) AS roster_date,
            shift_code
        FROM raw_shift_roster
        WHERE TRY_CAST(week_start AS DATE) IS NOT NULL
    ),
    -- Step 3: Combine and Evaluate Statuses
    EvaluatedAttendance AS (
        SELECT 
            COALESCE(r.employee_id, dp.employee_id) AS employee_id,
            COALESCE(r.roster_date, dp.work_date) AS work_date,
            r.shift_code AS shift_id,
            dp.first_check_in,
            dp.last_check_out,
            CASE 
                WHEN dp.first_check_in IS NULL AND dp.last_check_out IS NULL THEN 'Absent'
                WHEN dp.first_check_in IS NOT NULL AND dp.last_check_out IS NULL THEN 'Missing Punch'
                WHEN dp.first_check_in IS NULL AND dp.last_check_out IS NOT NULL THEN 'Missing Punch'
                ELSE 'Present'
            END AS attendance_status,
            CASE 
                WHEN dp.first_check_in IS NOT NULL AND dp.last_check_out IS NOT NULL 
                THEN DATEDIFF(minute, dp.first_check_in, dp.last_check_out) / 60.0
                ELSE 0.0
            END AS worked_hours
        FROM RosterEntries r
        FULL OUTER JOIN DailyPunches dp ON r.employee_id = dp.employee_id AND r.roster_date = dp.work_date
    )
    SELECT 
        employee_id,
        work_date,
        shift_id,
        first_check_in,
        last_check_out,
        attendance_status,
        worked_hours
    INTO staging.attendance_daily
    FROM EvaluatedAttendance
    WHERE employee_id IS NOT NULL AND work_date IS NOT NULL;
    """)
    conn.commit()
    print("✅ Successfully created `staging.attendance_daily` with robust roster & punch mapping!")

    # Verify row count
    cursor.execute("SELECT COUNT(*) FROM staging.attendance_daily;")
    count = cursor.fetchone()[0]
    print(f"📊 Total Rows in `staging.attendance_daily`: {count}")

    print("="*60)
    print("STAGE 3 COMPLETED SUCCESSFULLY! 🚀")
    print("="*60)

except Exception as e:
    conn.rollback()
    print(f"\n[Error in Stage 3]: {e}")

finally:
    cursor.close()
    conn.close()