-- MySQL Permission Fix Script
-- Run this as MySQL root user to fix permission issues

-- Connect as root user first:
-- mysql -u root -p

-- Fix permissions for bookuser
GRANT SELECT, INSERT, UPDATE, DELETE ON db_book.* TO 'bookuser'@'localhost';
GRANT LOCK TABLES ON db_book.* TO 'bookuser'@'localhost';
GRANT PROCESS ON *.* TO 'bookuser'@'localhost';
GRANT RELOAD ON *.* TO 'bookuser'@'localhost';

-- Alternative: Create a new user with more privileges for migration
CREATE USER 'migrationuser'@'localhost' IDENTIFIED BY 'MigrationPass123!';
GRANT SELECT, LOCK TABLES, PROCESS, RELOAD ON *.* TO 'migrationuser'@'localhost';
GRANT ALL PRIVILEGES ON db_book.* TO 'migrationuser'@'localhost';

-- Apply changes
FLUSH PRIVILEGES;

-- Verify permissions
SHOW GRANTS FOR 'bookuser'@'localhost';
SHOW GRANTS FOR 'migrationuser'@'localhost';

-- Test the export command with new user:
-- mysqldump -u migrationuser -p --single-transaction --no-tablespaces db_book > mysql_export.sql
