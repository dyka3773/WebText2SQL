-- DROP OWNED BY webtext2sql_app;
-- DROP USER webtext2sql_app;

CREATE USER webtext2sql_app WITH ENCRYPTED PASSWORD 'webtext2sql';
GRANT ALL PRIVILEGES ON DATABASE webtext2sql TO webtext2sql_app;