-- 10. Employees whose approved Annual leave days exceed full-year entitlement
        SELECT 
            emp_id,
            full_name,
            annual_leave_entitlement
        FROM raw_employees
        WHERE annual_leave_entitlement IS NOT NULL;