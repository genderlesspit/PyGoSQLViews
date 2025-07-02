-- Schema definitions
-- Add your CREATE TABLE statements here

-- Example:
-- CREATE TABLE users (
--     id INTEGER PRIMARY KEY AUTOINCREMENT,
--     name TEXT NOT NULL,
--     email TEXT UNIQUE NOT NULL,
--     created_at DATETIME DEFAULT CURRENT_TIMESTAMP
-- );

 CREATE TABLE users (
     id INTEGER PRIMARY KEY AUTOINCREMENT,
     name TEXT NOT NULL,
     email TEXT UNIQUE NOT NULL,
     created_at DATETIME DEFAULT CURRENT_TIMESTAMP
 );
