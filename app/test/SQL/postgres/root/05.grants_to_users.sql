-- This is required on Postgres 15+
GRANT ALL ON SCHEMA northwind TO test_user;
GRANT ALL ON ALL TABLES IN SCHEMA northwind TO test_user;
GRANT ALL ON SCHEMA pagila TO test_user;
GRANT ALL ON ALL TABLES IN SCHEMA pagila TO test_user;
GRANT ALL ON SCHEMA sailors TO test_user;
GRANT ALL ON ALL TABLES IN SCHEMA sailors TO test_user;

GRANT ALL ON SCHEMA northwind TO northwind_user;
GRANT ALL ON ALL TABLES IN SCHEMA northwind TO northwind_user;

GRANT ALL ON SCHEMA pagila TO pagila_user;
GRANT ALL ON ALL TABLES IN SCHEMA pagila TO pagila_user;