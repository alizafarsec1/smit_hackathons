-- 2. Monthly attrition rate by department (separations / average headcount)
        SELECT 
            department,
            LEFT(CAST(separation_date AS VARCHAR), 7) AS separation_month,
            COUNT(emp_id) AS separations
        FROM raw_employees
        WHERE separation_date IS NOT NULL
        GROUP BY department, LEFT(CAST(separation_date AS VARCHAR), 7)
        ORDER BY separation_month, department;