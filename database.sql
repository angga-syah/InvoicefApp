-- ========================================================
-- INVOICE MANAGEMENT SYSTEM - COMPLETE DATABASE SCHEMA
-- Version: 1.0.0
-- Date: 2024-01-01
-- ========================================================

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- ========== MAIN SCHEMA CREATION ==========

-- Table: users
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    user_uuid UUID DEFAULT uuid_generate_v4() UNIQUE NOT NULL,
    username VARCHAR(50) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(20) CHECK (role IN ('admin', 'viewer')) NOT NULL DEFAULT 'viewer',
    full_name VARCHAR(100) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Table: companies
CREATE TABLE IF NOT EXISTS companies (
    id SERIAL PRIMARY KEY,
    company_uuid UUID DEFAULT uuid_generate_v4() UNIQUE NOT NULL,
    company_name VARCHAR(200) NOT NULL,
    npwp VARCHAR(20) NOT NULL,
    idtku VARCHAR(20) NOT NULL,
    address TEXT NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Table: tka_workers
CREATE TABLE IF NOT EXISTS tka_workers (
    id SERIAL PRIMARY KEY,
    tka_uuid UUID DEFAULT uuid_generate_v4() UNIQUE NOT NULL,
    nama VARCHAR(100) NOT NULL,
    passport VARCHAR(20) NOT NULL UNIQUE,
    divisi VARCHAR(100),
    jenis_kelamin VARCHAR(20) CHECK (jenis_kelamin IN ('Laki-laki', 'Perempuan')) NOT NULL DEFAULT 'Laki-laki',
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Table: tka_family_members
CREATE TABLE IF NOT EXISTS tka_family_members (
    id SERIAL PRIMARY KEY,
    family_uuid UUID DEFAULT uuid_generate_v4() UNIQUE NOT NULL,
    tka_id INTEGER NOT NULL,
    nama VARCHAR(100) NOT NULL,
    passport VARCHAR(20) NOT NULL,
    jenis_kelamin VARCHAR(20) CHECK (jenis_kelamin IN ('Laki-laki', 'Perempuan')) NOT NULL DEFAULT 'Laki-laki',
    relationship VARCHAR(20) CHECK (relationship IN ('spouse', 'parent', 'child')) NOT NULL DEFAULT 'spouse',
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (tka_id) REFERENCES tka_workers(id) ON DELETE CASCADE
);

-- Table: job_descriptions
CREATE TABLE IF NOT EXISTS job_descriptions (
    id SERIAL PRIMARY KEY,
    job_uuid UUID DEFAULT uuid_generate_v4() UNIQUE NOT NULL,
    company_id INTEGER NOT NULL,
    job_name VARCHAR(200) NOT NULL,
    job_description TEXT NOT NULL,
    price DECIMAL(15,2) NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    sort_order INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE,
    CHECK (price >= 0)
);

-- Table: bank_accounts
CREATE TABLE IF NOT EXISTS bank_accounts (
    id SERIAL PRIMARY KEY,
    bank_uuid UUID DEFAULT uuid_generate_v4() UNIQUE NOT NULL,
    bank_name VARCHAR(100) NOT NULL,
    account_number VARCHAR(50) NOT NULL,
    account_name VARCHAR(100) NOT NULL,
    is_default BOOLEAN DEFAULT FALSE,
    is_active BOOLEAN DEFAULT TRUE,
    sort_order INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Table: invoices
CREATE TABLE IF NOT EXISTS invoices (
    id SERIAL PRIMARY KEY,
    invoice_uuid UUID DEFAULT uuid_generate_v4() UNIQUE NOT NULL,
    invoice_number VARCHAR(50) NOT NULL UNIQUE,
    company_id INTEGER NOT NULL,
    invoice_date DATE NOT NULL,
    subtotal DECIMAL(15,2) NOT NULL DEFAULT 0,
    vat_percentage DECIMAL(5,2) NOT NULL DEFAULT 11.00,
    vat_amount DECIMAL(15,2) NOT NULL DEFAULT 0,
    total_amount DECIMAL(15,2) NOT NULL DEFAULT 0,
    status VARCHAR(20) CHECK (status IN ('draft', 'finalized', 'paid', 'cancelled')) DEFAULT 'draft',
    notes TEXT,
    bank_account_id INTEGER,
    printed_count INTEGER DEFAULT 0,
    last_printed_at TIMESTAMP,
    imported_from VARCHAR(100) NULL,
    import_batch_id VARCHAR(50) NULL,
    created_by INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE RESTRICT,
    FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE RESTRICT,
    FOREIGN KEY (bank_account_id) REFERENCES bank_accounts(id) ON DELETE SET NULL,
    CHECK (subtotal >= 0 AND vat_amount >= 0 AND total_amount >= 0)
);

-- Table: invoice_lines
CREATE TABLE IF NOT EXISTS invoice_lines (
    id SERIAL PRIMARY KEY,
    line_uuid UUID DEFAULT uuid_generate_v4() UNIQUE NOT NULL,
    invoice_id INTEGER NOT NULL,
    baris INTEGER NOT NULL,
    line_order INTEGER NOT NULL,
    tka_id INTEGER NOT NULL,
    job_description_id INTEGER NOT NULL,
    custom_job_name VARCHAR(200),
    custom_job_description TEXT,
    custom_price DECIMAL(15,2),
    quantity INTEGER DEFAULT 1,
    unit_price DECIMAL(15,2) NOT NULL,
    line_total DECIMAL(15,2) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (invoice_id) REFERENCES invoices(id) ON DELETE CASCADE,
    FOREIGN KEY (tka_id) REFERENCES tka_workers(id) ON DELETE RESTRICT,
    FOREIGN KEY (job_description_id) REFERENCES job_descriptions(id) ON DELETE RESTRICT,
    CHECK (unit_price >= 0 AND line_total >= 0 AND quantity > 0)
);

-- Table: settings
CREATE TABLE IF NOT EXISTS settings (
    id SERIAL PRIMARY KEY,
    setting_key VARCHAR(50) NOT NULL UNIQUE,
    setting_value TEXT NOT NULL,
    setting_type VARCHAR(20) DEFAULT 'string',
    description VARCHAR(200),
    is_system BOOLEAN DEFAULT FALSE,
    updated_by INTEGER,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (updated_by) REFERENCES users(id) ON DELETE SET NULL
);

-- Table: user_preferences
CREATE TABLE IF NOT EXISTS user_preferences (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    preference_key VARCHAR(100) NOT NULL,
    preference_value JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    UNIQUE (user_id, preference_key)
);

-- Table: invoice_number_sequences
CREATE TABLE IF NOT EXISTS invoice_number_sequences (
    id SERIAL PRIMARY KEY,
    year INTEGER NOT NULL,
    month INTEGER NOT NULL,
    current_number INTEGER NOT NULL DEFAULT 0,
    prefix VARCHAR(10) DEFAULT '',
    suffix VARCHAR(10) DEFAULT '',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (year, month),
    CHECK (month >= 1 AND month <= 12 AND current_number >= 0)
);

-- ========== UNIQUE CONSTRAINTS ==========

-- Critical business rules
ALTER TABLE companies ADD CONSTRAINT unique_companies_npwp UNIQUE (npwp);
ALTER TABLE companies ADD CONSTRAINT unique_companies_idtku UNIQUE (idtku);
ALTER TABLE tka_family_members ADD CONSTRAINT unique_family_passport UNIQUE (passport);

-- Ensure only one default bank account
CREATE UNIQUE INDEX unique_default_bank ON bank_accounts (is_default) WHERE is_default = true;

-- ========== BUSINESS LOGIC TRIGGERS ==========

-- Trigger function for auto-updating invoice totals
CREATE OR REPLACE FUNCTION update_invoice_totals()
RETURNS TRIGGER AS $$
BEGIN
    -- Update subtotal
    UPDATE invoices 
    SET 
        subtotal = (
            SELECT COALESCE(SUM(line_total), 0) 
            FROM invoice_lines 
            WHERE invoice_id = COALESCE(NEW.invoice_id, OLD.invoice_id)
        ),
        updated_at = CURRENT_TIMESTAMP
    WHERE id = COALESCE(NEW.invoice_id, OLD.invoice_id);
    
    -- Update VAT amount dengan business rule khusus
    -- Rule: .49 bulatkan ke bawah, .50 bulatkan ke atas
    UPDATE invoices 
    SET 
        vat_amount = CASE 
            WHEN (subtotal * vat_percentage / 100) - FLOOR(subtotal * vat_percentage / 100) = 0.49 
            THEN FLOOR(subtotal * vat_percentage / 100)
            WHEN (subtotal * vat_percentage / 100) - FLOOR(subtotal * vat_percentage / 100) >= 0.50 
            THEN CEIL(subtotal * vat_percentage / 100)
            ELSE ROUND(subtotal * vat_percentage / 100, 0)
        END,
        updated_at = CURRENT_TIMESTAMP
    WHERE id = COALESCE(NEW.invoice_id, OLD.invoice_id);
    
    -- Update total amount
    UPDATE invoices 
    SET 
        total_amount = subtotal + vat_amount,
        updated_at = CURRENT_TIMESTAMP
    WHERE id = COALESCE(NEW.invoice_id, OLD.invoice_id);
    
    RETURN COALESCE(NEW, OLD);
END;
$$ LANGUAGE plpgsql;

-- Attach trigger to invoice_lines table
CREATE TRIGGER trigger_update_invoice_totals
    AFTER INSERT OR UPDATE OR DELETE ON invoice_lines
    FOR EACH ROW
    EXECUTE FUNCTION update_invoice_totals();

-- Trigger function for auto-updating timestamps
CREATE OR REPLACE FUNCTION update_modified_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply timestamp triggers to all tables
CREATE TRIGGER update_users_modtime BEFORE UPDATE ON users 
    FOR EACH ROW EXECUTE FUNCTION update_modified_column();
CREATE TRIGGER update_companies_modtime BEFORE UPDATE ON companies 
    FOR EACH ROW EXECUTE FUNCTION update_modified_column();
CREATE TRIGGER update_tka_workers_modtime BEFORE UPDATE ON tka_workers 
    FOR EACH ROW EXECUTE FUNCTION update_modified_column();
CREATE TRIGGER update_job_descriptions_modtime BEFORE UPDATE ON job_descriptions 
    FOR EACH ROW EXECUTE FUNCTION update_modified_column();
CREATE TRIGGER update_bank_accounts_modtime BEFORE UPDATE ON bank_accounts 
    FOR EACH ROW EXECUTE FUNCTION update_modified_column();
CREATE TRIGGER update_invoices_modtime BEFORE UPDATE ON invoices 
    FOR EACH ROW EXECUTE FUNCTION update_modified_column();
CREATE TRIGGER update_settings_modtime BEFORE UPDATE ON settings 
    FOR EACH ROW EXECUTE FUNCTION update_modified_column();
CREATE TRIGGER update_user_preferences_modtime BEFORE UPDATE ON user_preferences 
    FOR EACH ROW EXECUTE FUNCTION update_modified_column();
CREATE TRIGGER update_invoice_sequences_modtime BEFORE UPDATE ON invoice_number_sequences 
    FOR EACH ROW EXECUTE FUNCTION update_modified_column();

-- ========== PERFORMANCE INDEXES ==========

-- User indexes
CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);
CREATE INDEX IF NOT EXISTS idx_users_role ON users(role);

-- Company indexes
CREATE INDEX IF NOT EXISTS idx_companies_name ON companies(company_name);
CREATE INDEX IF NOT EXISTS idx_companies_npwp ON companies(npwp);
CREATE INDEX IF NOT EXISTS idx_companies_active ON companies(is_active);
CREATE INDEX IF NOT EXISTS idx_companies_name_trgm ON companies USING gin(company_name gin_trgm_ops);

-- TKA worker indexes
CREATE INDEX IF NOT EXISTS idx_tka_name_trgm ON tka_workers USING gin(nama gin_trgm_ops);
CREATE INDEX IF NOT EXISTS idx_tka_passport ON tka_workers(passport);
CREATE INDEX IF NOT EXISTS idx_tka_divisi ON tka_workers(divisi);
CREATE INDEX IF NOT EXISTS idx_tka_active ON tka_workers(is_active);

-- TKA family member indexes
CREATE INDEX IF NOT EXISTS idx_family_tka_id ON tka_family_members(tka_id);
CREATE INDEX IF NOT EXISTS idx_family_name_trgm ON tka_family_members USING gin(nama gin_trgm_ops);
CREATE INDEX IF NOT EXISTS idx_family_passport ON tka_family_members(passport);

-- Job description indexes
CREATE INDEX IF NOT EXISTS idx_job_company_active ON job_descriptions(company_id, is_active);
CREATE INDEX IF NOT EXISTS idx_job_name_trgm ON job_descriptions USING gin(job_name gin_trgm_ops);

-- Invoice indexes
CREATE INDEX IF NOT EXISTS idx_invoice_number ON invoices(invoice_number);
CREATE INDEX IF NOT EXISTS idx_invoice_company_date ON invoices(company_id, invoice_date DESC);
CREATE INDEX IF NOT EXISTS idx_invoice_status ON invoices(status);
CREATE INDEX IF NOT EXISTS idx_invoice_date_range ON invoices(invoice_date DESC);

-- Invoice line indexes
CREATE INDEX IF NOT EXISTS idx_invoice_lines_invoice_id ON invoice_lines(invoice_id, line_order);
CREATE INDEX IF NOT EXISTS idx_invoice_lines_tka ON invoice_lines(tka_id);
CREATE INDEX IF NOT EXISTS idx_invoice_lines_job ON invoice_lines(job_description_id);

-- Other indexes
CREATE INDEX IF NOT EXISTS idx_settings_key ON settings(setting_key);
CREATE INDEX IF NOT EXISTS idx_user_prefs ON user_preferences(user_id, preference_key);
CREATE INDEX IF NOT EXISTS idx_bank_default ON bank_accounts(is_default, is_active);

-- Partial indexes untuk performance
CREATE INDEX IF NOT EXISTS idx_companies_active_only ON companies(company_name) WHERE is_active = true;
CREATE INDEX IF NOT EXISTS idx_tka_active_only ON tka_workers(nama) WHERE is_active = true;
CREATE INDEX IF NOT EXISTS idx_job_active_only ON job_descriptions(company_id, job_name) WHERE is_active = true;

-- ========== INITIAL DATA ==========

-- Default admin user (password: 'admin123')
INSERT INTO users (username, password_hash, role, full_name) 
VALUES (
    'admin', 
    '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewryaZnRdSgRHO2K',
    'admin', 
    'System Administrator'
) ON CONFLICT (username) DO NOTHING;

-- Default application settings
INSERT INTO settings (setting_key, setting_value, setting_type, description, is_system) VALUES
    ('app_name', 'Invoice Management System', 'string', 'Application display name', true),
    ('default_vat_percentage', '11.00', 'decimal', 'Default VAT/PPN percentage', false),
    ('invoice_number_format', 'INV-{YY}-{MM}-{NNN}', 'string', 'Invoice number format template', false),
    ('company_tagline', 'Spirit of Services', 'string', 'Company tagline for invoices', false),
    ('default_currency', 'IDR', 'string', 'Default currency code', false),
    ('office_address_line1', 'Jakarta Office', 'string', 'Office address line 1', false),
    ('office_address_line2', 'Indonesia', 'string', 'Office address line 2', false),
    ('office_phone', '+62-21-XXXXXXX', 'string', 'Office phone number', false),
    ('auto_save_interval', '30', 'integer', 'Auto-save interval in seconds', false),
    ('max_search_results', '50', 'integer', 'Maximum search results to display', false)
ON CONFLICT (setting_key) DO NOTHING;

-- Default bank account
INSERT INTO bank_accounts (bank_name, account_number, account_name, is_default, is_active, sort_order) 
VALUES (
    'Bank Central Asia', 
    '1234567890', 
    'PT Invoice Management', 
    true, 
    true, 
    1
) ON CONFLICT DO NOTHING;

-- Initialize invoice sequence for current year/month
INSERT INTO invoice_number_sequences (year, month, current_number, prefix, suffix)
VALUES (
    EXTRACT(YEAR FROM CURRENT_DATE)::INTEGER,
    EXTRACT(MONTH FROM CURRENT_DATE)::INTEGER,
    0,
    'INV',
    ''
) ON CONFLICT (year, month) DO NOTHING;

-- ========== HELPFUL VIEWS ==========

-- View untuk invoice summary
CREATE OR REPLACE VIEW invoice_summary AS
SELECT 
    i.id,
    i.invoice_uuid,
    i.invoice_number,
    i.invoice_date,
    c.company_name,
    c.npwp,
    i.subtotal,
    i.vat_amount,
    i.total_amount,
    i.status,
    i.created_at,
    u.full_name as created_by_name,
    (SELECT COUNT(*) FROM invoice_lines il WHERE il.invoice_id = i.id) as line_count
FROM invoices i
JOIN companies c ON i.company_id = c.id
JOIN users u ON i.created_by = u.id
WHERE c.is_active = true;

-- View untuk TKA dengan assignment info
CREATE OR REPLACE VIEW tka_with_assignments AS
SELECT DISTINCT
    t.id,
    t.tka_uuid,
    t.nama,
    t.passport,
    t.divisi,
    t.jenis_kelamin,
    t.is_active,
    c.company_name,
    c.id as company_id
FROM tka_workers t
JOIN invoice_lines il ON t.id = il.tka_id
JOIN invoices i ON il.invoice_id = i.id
JOIN companies c ON i.company_id = c.id
WHERE t.is_active = true AND c.is_active = true;

-- ========== FINALIZATION ==========

-- Update table statistics
ANALYZE users;
ANALYZE companies;
ANALYZE tka_workers;
ANALYZE tka_family_members;
ANALYZE job_descriptions;
ANALYZE invoices;
ANALYZE invoice_lines;
ANALYZE bank_accounts;
ANALYZE settings;
ANALYZE user_preferences;
ANALYZE invoice_number_sequences;

-- Add table comments
COMMENT ON TABLE users IS 'System users with role-based access control';
COMMENT ON TABLE companies IS 'Client companies that receive invoices';
COMMENT ON TABLE tka_workers IS 'TKA (Foreign Workers) and their basic information';
COMMENT ON TABLE tka_family_members IS 'Family members of TKA workers';
COMMENT ON TABLE job_descriptions IS 'Job descriptions and pricing for each company';
COMMENT ON TABLE invoices IS 'Invoice headers with company and financial information';
COMMENT ON TABLE invoice_lines IS 'Individual line items within invoices';
COMMENT ON TABLE bank_accounts IS 'Bank account information for payments';
COMMENT ON TABLE settings IS 'Application settings and configuration';
COMMENT ON TABLE user_preferences IS 'User-specific preferences and settings';
COMMENT ON TABLE invoice_number_sequences IS 'Auto-incrementing invoice number sequences';

SELECT 'Database schema setup completed successfully!' as status;