DROP TABLE IF EXISTS "APP_USERS" CASCADE;
DROP TABLE IF EXISTS "USER_CONNECTIONS" CASCADE;

CREATE TABLE "APP_USERS" (
    "id" TEXT NOT NULL DEFAULT gen_random_uuid(),
    "created_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "email" TEXT NOT NULL,
    "username" TEXT NOT NULL,
    "hashed_password" TEXT NOT NULL,

    CONSTRAINT "APP_USERS_PK" PRIMARY KEY ("id")
);

CREATE TABLE "USER_CONNECTIONS" (
    "id" TEXT NOT NULL DEFAULT gen_random_uuid(),
    "created_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "user_email" TEXT NOT NULL,
    "server_name" TEXT NOT NULL,
    "ssh_connection_info" JSONB,
    "tcp_connection_info" JSONB,  -- I know this is not normalized properly, but using a whole different table for this would be an overkill
    "type_of_db" TEXT NOT NULL,  -- Added to store the type of database (e.g., 'mysql', 'postgres')

    CONSTRAINT "USER_CONNECTIONS_PK" PRIMARY KEY ("id")
);

CREATE INDEX "APP_USERS_email_idx" ON "APP_USERS"("email");
CREATE UNIQUE INDEX "APP_USERS_email_key" ON "APP_USERS"("email");

ALTER TABLE "USER_CONNECTIONS" ADD CONSTRAINT "USER_CONNECTIONS_user_email_FK" FOREIGN KEY ("user_email") REFERENCES "APP_USERS"("email") ON DELETE CASCADE ON UPDATE CASCADE;
