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