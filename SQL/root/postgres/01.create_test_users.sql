-- The test user should have access to all test schemas
CREATE USER test_user WITH ENCRYPTED PASSWORD 'test';
-- This is required on Postgres 15+
GRANT ALL ON SCHEMA northwind TO test_user;
GRANT ALL ON ALL TABLES IN SCHEMA northwind TO test_user;
GRANT ALL ON SCHEMA pagila TO test_user;
GRANT ALL ON ALL TABLES IN SCHEMA pagila TO test_user;
GRANT ALL ON SCHEMA sailors TO test_user;
GRANT ALL ON ALL TABLES IN SCHEMA sailors TO test_user;

-- The rest of the users who only have access to their own schema
CREATE USER northwind_user WITH ENCRYPTED PASSWORD 'northwind';
GRANT ALL ON SCHEMA northwind TO northwind_user;
GRANT ALL ON ALL TABLES IN SCHEMA northwind TO northwind_user;

CREATE USER pagila_user WITH ENCRYPTED PASSWORD 'pagila';
GRANT ALL ON SCHEMA pagila TO pagila_user;
GRANT ALL ON ALL TABLES IN SCHEMA pagila TO pagila_user;

CREATE USER no_access_user WITH ENCRYPTED PASSWORD 'no_access';