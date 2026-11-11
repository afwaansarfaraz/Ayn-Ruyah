-- RetinaLens AI Multi-Tenant Diabetic Retinopathy Platform Database Schema
-- Enforces hospital-level tenant isolation, foreign keys, and indexes.

PRAGMA foreign_keys = ON;

-- 1. Tenants (Independent Hospitals & Screening Centers)
CREATE TABLE IF NOT EXISTS tenants (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    registration_number TEXT,
    logo_url TEXT,
    city TEXT NOT NULL,
    state TEXT NOT NULL,
    address TEXT NOT NULL,
    contact_email TEXT NOT NULL,
    contact_phone TEXT NOT NULL,
    tier TEXT DEFAULT 'Standard',
    created_at TEXT NOT NULL,
    is_active INTEGER DEFAULT 1
);

-- 2. Users (Hospital Staff with Role-Based Access)
-- Roles: 'hospital_admin', 'ophthalmologist', 'screening_operator'
CREATE TABLE IF NOT EXISTS users (
    id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    full_name TEXT NOT NULL,
    role TEXT NOT NULL,
    email TEXT NOT NULL,
    phone TEXT,
    qualification TEXT,
    created_at TEXT NOT NULL,
    is_active INTEGER DEFAULT 1,
    FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE
);

-- 3. Patients (Diabetic Retinopathy Screening Cohort)
CREATE TABLE IF NOT EXISTS patients (
    id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    first_name TEXT NOT NULL,
    last_name TEXT NOT NULL,
    gender TEXT NOT NULL,
    dob TEXT NOT NULL,
    age INTEGER NOT NULL,
    phone TEXT NOT NULL,
    email TEXT,
    address TEXT NOT NULL,
    city TEXT NOT NULL,
    state TEXT NOT NULL,
    pincode TEXT,
    avatar_url TEXT,
    diabetes_type TEXT NOT NULL, -- 'Type 1', 'Type 2', 'Gestational', 'Pre-diabetes'
    diabetes_duration_years REAL NOT NULL,
    hba1c REAL,
    insulin_dependent INTEGER DEFAULT 0,
    hypertension INTEGER DEFAULT 0,
    smoker INTEGER DEFAULT 0,
    assigned_doctor_id TEXT,
    is_minor INTEGER DEFAULT 0,
    guardian_name TEXT,
    guardian_relation TEXT,
    guardian_phone TEXT,
    clinical_notes TEXT,
    is_demo INTEGER DEFAULT 0,
    created_at TEXT NOT NULL,
    FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE,
    FOREIGN KEY (assigned_doctor_id) REFERENCES users(id) ON DELETE SET NULL
);

-- 4. Screenings (AI-Powered Retinal Fundus Screening Records)
CREATE TABLE IF NOT EXISTS screenings (
    id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    patient_id TEXT NOT NULL,
    operator_id TEXT,
    doctor_id TEXT,
    eye TEXT NOT NULL, -- 'Left Eye (OS)', 'Right Eye (OD)', 'Bilateral'
    grade INTEGER NOT NULL, -- 0: No DR, 1: Mild, 2: Moderate, 3: Severe, 4: Proliferative
    diagnosis TEXT NOT NULL,
    confidence REAL NOT NULL,
    severity TEXT NOT NULL,
    probabilities_json TEXT NOT NULL,
    recommendation TEXT NOT NULL,
    original_image_path TEXT,
    heatmap_image_path TEXT,
    notes TEXT,
    status TEXT DEFAULT 'Completed', -- 'Completed', 'Referred', 'Urgent Specialist Review', 'Follow-up'
    is_demo INTEGER DEFAULT 0,
    created_at TEXT NOT NULL,
    FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE,
    FOREIGN KEY (patient_id) REFERENCES patients(id) ON DELETE CASCADE,
    FOREIGN KEY (operator_id) REFERENCES users(id) ON DELETE SET NULL,
    FOREIGN KEY (doctor_id) REFERENCES users(id) ON DELETE SET NULL
);

-- 5. Audit Trail (Compliance & Operational Log)
CREATE TABLE IF NOT EXISTS audit_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tenant_id TEXT NOT NULL,
    user_id TEXT,
    action TEXT NOT NULL,
    details TEXT NOT NULL,
    ip_address TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE CASCADE
);

-- Indices for strict tenant-isolated query performance
CREATE INDEX IF NOT EXISTS idx_users_tenant ON users(tenant_id);
CREATE INDEX IF NOT EXISTS idx_patients_tenant ON patients(tenant_id);
CREATE INDEX IF NOT EXISTS idx_patients_name ON patients(first_name, last_name);
CREATE INDEX IF NOT EXISTS idx_screenings_tenant ON screenings(tenant_id);
CREATE INDEX IF NOT EXISTS idx_screenings_patient ON screenings(patient_id);
CREATE INDEX IF NOT EXISTS idx_screenings_grade ON screenings(grade);
CREATE INDEX IF NOT EXISTS idx_audit_tenant ON audit_logs(tenant_id);

