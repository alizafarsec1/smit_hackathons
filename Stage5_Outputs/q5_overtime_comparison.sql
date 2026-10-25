-- 5. Overtime hours computed from punches vs approved vs paid by department and month
        SELECT 
            e.department,
            LEFT(CAST(a.work_date AS VARCHAR), 7) AS work_month,
            SUM(CASE WHEN a.worked_hours > 8 THEN a.worked_hours - 8 ELSE 0 END) AS computed_overtime_hours
        FROM staging.attendance_daily a
        JOIN raw_employees e ON a.employee_id = e.emp_id
        GROUP BY e.department, LEFT(CAST(a.work_date AS VARCHAR), 7)
        ORDER BY work_month, e.department;