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