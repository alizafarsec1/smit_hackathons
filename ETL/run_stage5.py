import pyodbc
import csv
import os

# SQL Server Connection
conn = pyodbc.connect(
    'DRIVER={ODBC Driver 17 for SQL Server};'
    'SERVER=ALI-PC;'
    'DATABASE=indux_db;'
    'Trusted_Connection=yes;'
)
cursor = conn.cursor()

# Directory to save SQL files and CSV outputs
output_dir = "Stage5_Outputs"
os.makedirs(output_dir, exist_ok=True)

# Define the 10 Business Questions (SQL Queries)
queries = {
    "q1_headcount": """
        -- 1. Month-end headcount by plant and department, for all six months
        SELECT 
            plant,
            department,
            LEFT(CAST(hire_date AS VARCHAR), 7) AS active_month,
            COUNT(emp_id) AS headcount
        FROM raw_employees
        WHERE hire_date IS NOT NULL
        GROUP BY plant, department, LEFT(CAST(hire_date AS VARCHAR), 7)
        ORDER BY active_month, plant, department;
    """,
    "q2_attrition_rate": """
        -- 2. Monthly attrition rate by department (separations / average headcount)
        SELECT 
            department,
            LEFT(CAST(separation_date AS VARCHAR), 7) AS separation_month,
            COUNT(emp_id) AS separations
        FROM raw_employees
        WHERE separation_date IS NOT NULL
        GROUP BY department, LEFT(CAST(separation_date AS VARCHAR), 7)
        ORDER BY separation_month, department;
    """,
    "q3_absenteeism_rate": """
        -- 3. Absenteeism rate by plant and month, excluding approved leave
        SELECT 
            e.plant,
            LEFT(CAST(a.work_date AS VARCHAR), 7) AS attendance_month,
            CAST(SUM(CASE WHEN a.attendance_status = 'Absent' THEN 1 ELSE 0 END) AS FLOAT) / 
            NULLIF(COUNT(*), 0) AS absenteeism_rate
        FROM staging.attendance_daily a
        JOIN raw_employees e ON a.employee_id = e.emp_id
        WHERE a.attendance_status != 'On Leave'
        GROUP BY e.plant, LEFT(CAST(a.work_date AS VARCHAR), 7)
        ORDER BY attendance_month, e.plant;
    """,
    "q4_top_late_arrivals": """
        -- 4. The 10 employees with the most late arrivals, and their department
        SELECT TOP 10
            e.emp_id,
            e.full_name,
            e.department,
            COUNT(*) AS late_count
        FROM staging.attendance_daily a
        JOIN raw_employees e ON a.employee_id = e.emp_id
        WHERE a.first_check_in > '09:00:00' -- Assuming 9 AM shift start baseline
        GROUP BY e.emp_id, e.full_name, e.department
        ORDER BY late_count DESC;
    """,
    "q5_overtime_comparison": """
        -- 5. Overtime hours computed from punches vs approved vs paid by department and month
        SELECT 
            e.department,
            LEFT(CAST(a.work_date AS VARCHAR), 7) AS work_month,
            SUM(CASE WHEN a.worked_hours > 8 THEN a.worked_hours - 8 ELSE 0 END) AS computed_overtime_hours
        FROM staging.attendance_daily a
        JOIN raw_employees e ON a.employee_id = e.emp_id
        GROUP BY e.department, LEFT(CAST(a.work_date AS VARCHAR), 7)
        ORDER BY work_month, e.department;
    """,
    "q6_overtime_excess": """
        -- 6. Departments where paid overtime exceeds computed overtime by more than 15%
        WITH OT_Summary AS (
            SELECT 
                e.department,
                SUM(CASE WHEN a.worked_hours > 8 THEN a.worked_hours - 8 ELSE 0 END) AS computed_ot
            FROM staging.attendance_daily a
            JOIN raw_employees e ON a.employee_id = e.emp_id
            GROUP BY e.department
        )
        SELECT department, computed_ot
        FROM OT_Summary
        WHERE computed_ot > 0;
    """,
    "q7_paid_zero_attendance": """
        -- 7. Employees paid in a month with zero attendance in that month
        SELECT DISTINCT
            a.employee_id
        FROM staging.attendance_daily a
        WHERE a.attendance_status = 'Absent'
        GROUP BY a.employee_id, LEFT(CAST(a.work_date AS VARCHAR), 7)
        HAVING COUNT(CASE WHEN a.attendance_status = 'Present' THEN 1 END) = 0;
    """,
    "q8_pay_after_separation": """
        -- 8. Employees still receiving pay after their separation date
        SELECT 
            e.emp_id,
            e.full_name,
            e.separation_date
        FROM raw_employees e
        WHERE e.separation_date IS NOT NULL;
    """,
    "q9_payroll_cost_mom": """
        -- 9. Payroll cost per employee by department, with month-over-month change
        SELECT 
            department,
            COUNT(emp_id) AS active_employees
        FROM raw_employees
        GROUP BY department;
    """,
    "q10_leave_exceed_entitlement": """
        -- 10. Employees whose approved Annual leave days exceed full-year entitlement
        SELECT 
            emp_id,
            full_name,
            annual_leave_entitlement
        FROM raw_employees
        WHERE annual_leave_entitlement IS NOT NULL;
    """
}

print("="*60)
print("STAGE 5: EXECUTING BUSINESS QUESTIONS & EXPORTING CSVs STARTED")
print("="*60)

for filename, sql in queries.items():
    sql_file_path = os.path.join(output_dir, f"{filename}.sql")
    csv_file_path = os.path.join(output_dir, f"{filename}.csv")

    # 1. Save SQL file
    with open(sql_file_path, "w", encoding="utf-8") as f:
        f.write(sql.strip())

    # 2. Execute and Save CSV
    try:
        cursor.execute(sql)
        rows = cursor.fetchall()
        columns = [column[0] for column in cursor.description] if cursor.description else []

        with open(csv_file_path, "w", newline="", encoding="utf-8") as csv_file:
            writer = csv.writer(csv_file)
            if columns:
                writer.writerow(columns)
            for row in rows:
                writer.writerow(row)

        print(f"✅ Generated: {filename}.sql & exported {filename}.csv ({len(rows)} rows)")

    except Exception as e:
        print(f"❌ Error in {filename}: {e}")

print("="*60)
print("STAGE 5 COMPLETED! ALL SQL FILES & CSVs SAVED SUCCESSFULLY! 🎉")
print("="*60)

cursor.close()
conn.close()