
-- Create User table
CREATE TABLE IF NOT EXISTS "user" (
    id SERIAL PRIMARY KEY,
    username VARCHAR(80) UNIQUE NOT NULL,
    password_hash VARCHAR(256) NOT NULL,
    name VARCHAR(32),
    age INTEGER,
    gender VARCHAR(20),
    goal VARCHAR(64),
    streak INTEGER DEFAULT 0,
    last_date VARCHAR(10),
    completed_today BOOLEAN DEFAULT FALSE,
    last_login TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create User_Task table
CREATE TABLE IF NOT EXISTS "user_task" (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    task_id VARCHAR(50) NOT NULL,
    date VARCHAR(10) NOT NULL,
    done BOOLEAN DEFAULT FALSE,
    FOREIGN KEY (user_id) REFERENCES "user"(id) ON DELETE CASCADE,
    CONSTRAINT _user_task_date_uc UNIQUE (user_id, task_id, date)
);

CREATE INDEX IF NOT EXISTS idx_usertask_user_id ON "user_task"(user_id);
CREATE INDEX IF NOT EXISTS idx_usertask_date ON "user_task"(date);
CREATE INDEX IF NOT EXISTS idx_user_username ON "user"(username);

