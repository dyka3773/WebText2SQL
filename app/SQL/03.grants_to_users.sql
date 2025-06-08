GRANT ALL PRIVILEGES ON DATABASE postgres TO webtext2sql_app;
-- This is required on Postgres 15+
GRANT ALL ON SCHEMA public TO webtext2sql_app;
GRANT ALL ON ALL TABLES IN SCHEMA public TO webtext2sql_app;
