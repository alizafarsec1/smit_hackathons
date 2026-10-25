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