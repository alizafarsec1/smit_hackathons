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