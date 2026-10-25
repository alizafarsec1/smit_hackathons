-- 8. Employees still receiving pay after their separation date
        SELECT 
            e.emp_id,
            e.full_name,
            e.separation_date
        FROM raw_employees e
        WHERE e.separation_date IS NOT NULL;