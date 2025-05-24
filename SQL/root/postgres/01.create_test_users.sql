-- The test user should have access to all test schemas
CREATE USER test_user WITH ENCRYPTED PASSWORD 'test';
-- The rest of the users who only have access to their own schema
CREATE USER northwind_user WITH ENCRYPTED PASSWORD 'northwind';
CREATE USER pagila_user WITH ENCRYPTED PASSWORD 'pagila';
CREATE USER no_access_user WITH ENCRYPTED PASSWORD 'no_access';
