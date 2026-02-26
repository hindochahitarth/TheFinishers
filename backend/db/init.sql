-- GreenPulse AI — MySQL Database Initialization
-- This script runs on first startup of the MySQL container.

CREATE DATABASE IF NOT EXISTS greenpulse
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

USE greenpulse;

-- Ensure the app user has all privileges
GRANT ALL PRIVILEGES ON greenpulse.* TO 'gpuser'@'%';
FLUSH PRIVILEGES;
