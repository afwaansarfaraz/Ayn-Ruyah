/**
 * RetinaLens AI - Multi-Tenant API Client Module
 * Provides typed asynchronous communication with backend services,
 * enforcing hospital-level tenant context in every request.
 */

const RetinaLensAPI = {
    getBaseUrl() {
        return window.location.origin;
    },

    getHeaders() {
        const headers = {
            'Accept': 'application/json',
        };
        const currentTenant = State.getActiveTenant();
        if (currentTenant && currentTenant.id) {
            headers['X-Tenant-ID'] = currentTenant.id;
        }
        return headers;
    },

    // --- Authentication & Workspaces ---
    async getHospitals() {
        const res = await fetch(`${this.getBaseUrl()}/api/auth/hospitals`);
        if (!res.ok) throw new Error('Failed to fetch hospitals directory');
        return await res.json();
    },

    async login(username, password, tenantId) {
        const res = await fetch(`${this.getBaseUrl()}/api/auth/login`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                username: username,
                password: password,
                tenant_id: tenantId,
            }),
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.error || 'Login failed');
        return data;
    },

    async logout() {
        await fetch(`${this.getBaseUrl()}/api/auth/logout`, { method: 'POST' });
    },

    async getCurrentUser() {
        const res = await fetch(`${this.getBaseUrl()}/api/auth/me`, {
            headers: this.getHeaders(),
        });
        if (res.status === 401 || res.status === 403) {
            try {
                return await res.json();
            } catch (_) {
                return { authenticated: false, user: null, hospital: null };
            }
        }
        if (!res.ok) {
            const errData = await res.json().catch(() => ({}));
            throw new Error(errData.error || `Server error (${res.status})`);
        }
        return await res.json();
    },

    // --- Hospital Tenants ---
    async getHospitalProfile(tenantId) {
        const res = await fetch(`${this.getBaseUrl()}/api/tenants/${tenantId}`, {
            headers: this.getHeaders(),
        });
        if (!res.ok) throw new Error('Failed to fetch hospital profile');
        return await res.json();
    },

    async updateHospitalProfile(tenantId, updates) {
        const res = await fetch(`${this.getBaseUrl()}/api/tenants/${tenantId}`, {
            method: 'PUT',
            headers: { ...this.getHeaders(), 'Content-Type': 'application/json' },
            body: JSON.stringify(updates),
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.error || 'Failed to update hospital');
        return data;
    },

    async getHospitalStaff(tenantId) {
        const res = await fetch(`${this.getBaseUrl()}/api/tenants/${tenantId}/users`, {
            headers: this.getHeaders(),
        });
        if (!res.ok) throw new Error('Failed to fetch hospital staff');
        return await res.json();
    },

    async addHospitalStaff(tenantId, staffData) {
        const res = await fetch(`${this.getBaseUrl()}/api/tenants/${tenantId}/users`, {
            method: 'POST',
            headers: { ...this.getHeaders(), 'Content-Type': 'application/json' },
            body: JSON.stringify(staffData),
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.error || 'Failed to add staff member');
        return data;
    },

    async registerHospital(hospitalData) {
        const res = await fetch(`${this.getBaseUrl()}/api/tenants`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(hospitalData),
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.error || 'Failed to register hospital');
        return data;
    },

    // --- Patients ---
    async getPatients(params = {}) {
        const url = new URL(`${this.getBaseUrl()}/api/patients`);
        Object.entries(params).forEach(([k, v]) => {
            if (v !== undefined && v !== null && v !== '') {
                url.searchParams.append(k, v);
            }
        });
        const res = await fetch(url.toString(), { headers: this.getHeaders() });
        const data = await res.json();
        if (!res.ok) throw new Error(data.error || 'Failed to load patients');
        return data;
    },

    async getPatient(patientId) {
        const res = await fetch(`${this.getBaseUrl()}/api/patients/${patientId}`, {
            headers: this.getHeaders(),
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.error || 'Patient not found');
        return data;
    },

    async registerPatient(patientData) {
        const res = await fetch(`${this.getBaseUrl()}/api/patients`, {
            method: 'POST',
            headers: { ...this.getHeaders(), 'Content-Type': 'application/json' },
            body: JSON.stringify(patientData),
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.error || 'Failed to register patient');
        return data;
    },

    async getPatientScreenings(patientId) {
        const res = await fetch(`${this.getBaseUrl()}/api/patients/${patientId}/screenings`, {
            headers: this.getHeaders(),
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.error || 'Failed to load patient screenings');
        return data;
    },

    // --- AI Screenings ---
    async getScreenings(params = {}) {
        const url = new URL(`${this.getBaseUrl()}/api/screenings`);
        Object.entries(params).forEach(([k, v]) => {
            if (v !== undefined && v !== null && v !== '') {
                url.searchParams.append(k, v);
            }
        });
        const res = await fetch(url.toString(), { headers: this.getHeaders() });
        const data = await res.json();
        if (!res.ok) throw new Error(data.error || 'Failed to fetch screenings');
        return data;
    },

    async executeScreening(patientId, imageBlob, eye = 'Left Eye (OS)', notes = '') {
        const formData = new FormData();
        formData.append('patient_id', patientId);
        formData.append('eye', eye);
        formData.append('notes', notes);
        formData.append('image', imageBlob, 'fundus_scan.png');

        const res = await fetch(`${this.getBaseUrl()}/api/screenings`, {
            method: 'POST',
            headers: this.getHeaders(),
            body: formData,
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.error || 'AI screening failed');
        return data;
    },

    async getScreeningDetail(screeningId) {
        const res = await fetch(`${this.getBaseUrl()}/api/screenings/${screeningId}`, {
            headers: this.getHeaders(),
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.error || 'Screening not found');
        return data;
    },

    // --- Analytics ---
    async getAnalytics() {
        const res = await fetch(`${this.getBaseUrl()}/api/analytics`, {
            headers: this.getHeaders(),
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.error || 'Failed to load analytics');
        return data;
    },

    // --- Health Check ---
    async checkHealth() {
        const res = await fetch(`${this.getBaseUrl()}/api/health`);
        if (!res.ok) throw new Error('Health check failed');
        return await res.json();
    }
};

window.RetinaLensAPI = RetinaLensAPI;
