-- 9. Payroll cost per employee by department, with month-over-month change
        SELECT 
            department,
            COUNT(emp_id) AS active_employees
        FROM raw_employees
        GROUP BY department;