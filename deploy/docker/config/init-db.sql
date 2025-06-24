-- DroneSphere Database Initialization Script
-- This runs automatically when PostgreSQL container starts

-- Create the main database (if not exists)
CREATE DATABASE dronesphere;

-- Create application user with limited privileges (security best practice)
CREATE USER dronesphere WITH ENCRYPTED PASSWORD 'dronesphere_pass_dev';

-- Grant connection privilege
GRANT CONNECT ON DATABASE dronesphere TO dronesphere;

-- Connect to the dronesphere database for remaining setup
\c dronesphere;

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";     -- For UUID generation
CREATE EXTENSION IF NOT EXISTS "postgis";       -- For GPS/geospatial data
CREATE EXTENSION IF NOT EXISTS "btree_gist";    -- For temporal queries

-- Create schema for better organization
CREATE SCHEMA IF NOT EXISTS drone_control;

-- Grant all privileges on schema to application user
GRANT ALL ON SCHEMA drone_control TO dronesphere;
GRANT CREATE ON DATABASE dronesphere TO dronesphere;

-- Create initial tables for testing
CREATE TABLE IF NOT EXISTS drone_control.health_check (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    status VARCHAR(50),
    checked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Grant table permissions
ALTER TABLE drone_control.health_check OWNER TO dronesphere;

-- Insert test record
INSERT INTO drone_control.health_check (status) VALUES ('Database initialized successfully');

-- Log successful initialization
DO $$
BEGIN
    RAISE NOTICE 'DroneSphere database initialized successfully at %', NOW();
END
$$;
