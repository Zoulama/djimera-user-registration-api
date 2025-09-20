-- Initialize Dailymotion User Registration Database

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Create users table
CREATE TABLE IF NOT EXISTS users (
    user_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'PENDING',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    activated_at TIMESTAMP WITH TIME ZONE NULL,
    
    CONSTRAINT users_email_format CHECK (email ~ '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$'),
    CONSTRAINT users_status_valid CHECK (status IN ('PENDING', 'ACTIVE', 'INACTIVE', 'SUSPENDED'))
);

-- Create indexes for users table
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_users_status ON users(status);
CREATE INDEX IF NOT EXISTS idx_users_created_at ON users(created_at);

-- Create activation_codes table
CREATE TABLE IF NOT EXISTS activation_codes (
    user_id UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    code VARCHAR(4) NOT NULL,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    used_at TIMESTAMP WITH TIME ZONE NULL,
    is_used BOOLEAN DEFAULT FALSE,
    
    PRIMARY KEY (user_id, code),
    CONSTRAINT activation_codes_code_format CHECK (code ~ '^[0-9]{4}$')
);

-- Create indexes for activation_codes table
CREATE INDEX IF NOT EXISTS idx_activation_codes_expires_at ON activation_codes(expires_at);
CREATE INDEX IF NOT EXISTS idx_activation_codes_is_used ON activation_codes(is_used);
CREATE INDEX IF NOT EXISTS idx_activation_codes_created_at ON activation_codes(created_at);

-- Create function to automatically update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create trigger to automatically update updated_at on users table
DROP TRIGGER IF EXISTS update_users_updated_at ON users;
CREATE TRIGGER update_users_updated_at
    BEFORE UPDATE ON users
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Insert sample data (for development only - remove in production)
-- This will be skipped if users already exist
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM users LIMIT 1) THEN
        INSERT INTO users (email, password_hash, status) VALUES 
        ('test@example.com', '$2b$12$example.hash.here', 'PENDING');
        
        RAISE NOTICE 'Sample data inserted for development';
    END IF;
END $$;