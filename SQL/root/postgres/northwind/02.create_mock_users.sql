CREATE USER test_user WITH ENCRYPTED PASSWORD 'test';
-- This is required on Postgres 15+
GRANT ALL ON SCHEMA northwind TO test_user;
GRANT ALL ON ALL TABLES IN SCHEMA northwind TO test_user;