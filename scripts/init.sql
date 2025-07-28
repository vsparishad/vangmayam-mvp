-- Initialize Vangmayam database with extensions and basic schema

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";
CREATE EXTENSION IF NOT EXISTS "unaccent";

-- Create enum types
CREATE TYPE user_role AS ENUM ('admin', 'editor', 'reader', 'scholar');
CREATE TYPE book_status AS ENUM ('imported', 'processing', 'ocr_complete', 'proofread', 'published');
CREATE TYPE ocr_engine AS ENUM ('tesseract', 'google_vision', 'easyocr');

-- Users table
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email VARCHAR(255) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    role user_role DEFAULT 'reader',
    is_active BOOLEAN DEFAULT true,
    google_id VARCHAR(255) UNIQUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Books table
CREATE TABLE books (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    title VARCHAR(500) NOT NULL,
    author VARCHAR(255),
    language VARCHAR(50) DEFAULT 'sanskrit',
    manuscript_date DATE,
    archive_url TEXT,
    archive_id VARCHAR(255),
    total_pages INTEGER,
    status book_status DEFAULT 'imported',
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Pages table
CREATE TABLE pages (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    book_id UUID REFERENCES books(id) ON DELETE CASCADE,
    page_number INTEGER NOT NULL,
    image_path TEXT NOT NULL,
    image_width INTEGER,
    image_height INTEGER,
    ocr_confidence DECIMAL(5,2),
    is_proofread BOOLEAN DEFAULT false,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(book_id, page_number)
);

-- OCR results table
CREATE TABLE ocr_results (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    page_id UUID REFERENCES pages(id) ON DELETE CASCADE,
    engine ocr_engine NOT NULL,
    raw_text TEXT,
    alto_xml TEXT,
    confidence_data JSONB,
    word_count INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Tags table
CREATE TABLE tags (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(100) UNIQUE NOT NULL,
    description TEXT,
    category VARCHAR(50),
    is_approved BOOLEAN DEFAULT false,
    created_by UUID REFERENCES users(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Book tags junction table
CREATE TABLE book_tags (
    book_id UUID REFERENCES books(id) ON DELETE CASCADE,
    tag_id UUID REFERENCES tags(id) ON DELETE CASCADE,
    added_by UUID REFERENCES users(id),
    added_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    PRIMARY KEY (book_id, tag_id)
);

-- Glossary entries table
CREATE TABLE glossary_entries (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    word VARCHAR(255) NOT NULL,
    definition TEXT NOT NULL,
    etymology TEXT,
    pronunciation VARCHAR(255),
    language VARCHAR(50) DEFAULT 'sanskrit',
    source VARCHAR(255),
    created_by UUID REFERENCES users(id),
    is_verified BOOLEAN DEFAULT false,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- User sessions table
CREATE TABLE user_sessions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    token_hash VARCHAR(255) NOT NULL,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Audit log table
CREATE TABLE audit_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id),
    action VARCHAR(100) NOT NULL,
    resource_type VARCHAR(50),
    resource_id UUID,
    details JSONB,
    ip_address INET,
    user_agent TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes for performance
CREATE INDEX idx_books_status ON books(status);
CREATE INDEX idx_books_language ON books(language);
CREATE INDEX idx_books_metadata ON books USING GIN(metadata);
CREATE INDEX idx_pages_book_id ON pages(book_id);
CREATE INDEX idx_pages_book_page ON pages(book_id, page_number);
CREATE INDEX idx_ocr_results_page_id ON ocr_results(page_id);
CREATE INDEX idx_ocr_results_engine ON ocr_results(engine);
CREATE INDEX idx_tags_name ON tags(name);
CREATE INDEX idx_tags_category ON tags(category);
CREATE INDEX idx_glossary_word ON glossary_entries(word);
CREATE INDEX idx_glossary_language ON glossary_entries(language);
CREATE INDEX idx_user_sessions_user_id ON user_sessions(user_id);
CREATE INDEX idx_user_sessions_expires ON user_sessions(expires_at);
CREATE INDEX idx_audit_logs_user_id ON audit_logs(user_id);
CREATE INDEX idx_audit_logs_created_at ON audit_logs(created_at);

-- Full-text search indexes
CREATE INDEX idx_books_title_fts ON books USING GIN(to_tsvector('english', title));
CREATE INDEX idx_ocr_results_text_fts ON ocr_results USING GIN(to_tsvector('english', raw_text));
CREATE INDEX idx_glossary_definition_fts ON glossary_entries USING GIN(to_tsvector('english', definition));

-- Trigram indexes for fuzzy search
CREATE INDEX idx_books_title_trgm ON books USING GIN(title gin_trgm_ops);
CREATE INDEX idx_glossary_word_trgm ON glossary_entries USING GIN(word gin_trgm_ops);

-- Insert default admin user
INSERT INTO users (email, name, role, is_active) 
VALUES ('admin@vangmayam.org', 'System Administrator', 'admin', true);

-- Insert sample tags
INSERT INTO tags (name, description, category, is_approved) VALUES
('Vedas', 'Primary Vedic texts', 'scripture', true),
('Upanishads', 'Philosophical treatises', 'philosophy', true),
('Puranas', 'Ancient stories and legends', 'literature', true),
('Dharma Shastra', 'Legal and ethical texts', 'law', true),
('Ayurveda', 'Traditional medicine texts', 'medicine', true),
('Jyotisha', 'Astronomical and astrological texts', 'astronomy', true),
('Kavya', 'Classical poetry', 'poetry', true),
('Natya', 'Performing arts texts', 'arts', true);

COMMENT ON DATABASE vangmayam IS 'Vangmayam - Vedic Corpus Portal Database';
