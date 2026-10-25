-- 7. Employees paid in a month with zero attendance in that month
        SELECT DISTINCT
            a.employee_id
        FROM staging.attendance_daily a
        WHERE a.attendance_status = 'Absent'
        GROUP BY a.employee_id, LEFT(CAST(a.work_date AS VARCHAR), 7)
        HAVING COUNT(CASE WHEN a.attendance_status = 'Present' THEN 1 END) = 0;