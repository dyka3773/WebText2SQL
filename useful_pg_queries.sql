-- Get all tables in the northwind database
SELECT * 
FROM information_schema.tables 
WHERE table_schema = 'northwind'
AND table_type LIKE '%TABLE%'
;

SELECT *
FROM pg_tables
WHERE schemaname = 'northwind'
;

-- Get all tables the user has access to in a certain schema
SELECT *
FROM information_schema.role_table_grants 
WHERE privilege_type = 'SELECT' 
AND grantee = 'test_user'
AND table_schema = 'northwind'
;

-- Get all schemas the user has access to
SELECT DISTINCT table_schema
FROM information_schema.role_table_grants 
WHERE privilege_type = 'SELECT' 
AND grantee = 'test_user'
;