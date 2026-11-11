/**
 * AYN RUYAH — Multi-Tenant State Store & Clinical Constants
 * Manages active hospital workspace, authorized staff user, loaded cohorts,
 * and clinical scale constants.
 */

const DR_GRADES = {
    0: { name: 'No DR',            severity: 'Normal',        color: '#16A779', badge: 'badge-dr-0' },
    1: { name: 'Mild DR',          severity: 'Mild',          color: '#2563EB', badge: 'badge-dr-1' },
    2: { name: 'Moderate DR',      severity: 'Moderate',      color: '#D97706', badge: 'badge-dr-2' },
    3: { name: 'Severe DR',        severity: 'Severe',        color: '#EA580C', badge: 'badge-dr-3' },
    4: { name: 'Proliferative DR', severity: 'Proliferative', color: '#DC2626', badge: 'badge-dr-4' }
};

const DR_RECOMMENDATIONS = {
    0: 'No diabetic retinopathy detected. Continue annual screening and optimal glycemic control (target HbA1c < 7.0%).',
    1: 'Mild non-proliferative DR (microaneurysms only). Tight blood sugar and BP control. Repeat screening in 12 months.',
    2: 'Moderate non-proliferative DR (exudates/hemorrhages). Refer to ophthalmologist for dilated retinal exam within 3-6 months.',
    3: 'Severe non-proliferative DR detected (4-2-1 rule). High risk of progression. Urgent ophthalmology referral required within 4 weeks.',
    4: 'Proliferative diabetic retinopathy (neovascularization/vitreous hemorrhage). EMERGENCY referral for panretinal photocoagulation (PRP) or anti-VEGF.'
};

const State = {
    activeTenant: null,
    activeUser: null,
    hospitals: [],
    patients: [],
    screenings: [],
    analytics: null,
    selectedPatientForAI: null,
    currentAIImage: null,
    currentAIResult: null,
    gradcamEnabled: true,
    probabilityChart: null,

    resetCaches() {
        this.patients = [];
        this.screenings = [];
        this.analytics = null;
        this.selectedPatientForAI = null;
        this.currentAIImage = null;
        this.currentAIResult = null;
    },

    getActiveTenant() {
        if (!this.activeTenant) {
            const saved = localStorage.getItem('ayn_ruyah_tenant') || localStorage.getItem('retinalens_tenant');
            if (saved) {
                try { this.activeTenant = JSON.parse(saved); } catch (e) {}
            }
        }
        return this.activeTenant;
    },

    setActiveTenant(tenant) {
        const currentId = this.activeTenant ? this.activeTenant.id : null;
        const newId = tenant ? tenant.id : null;
        if (currentId !== newId) {
            this.resetCaches();
        }
        this.activeTenant = tenant;
        if (tenant) {
            localStorage.setItem('ayn_ruyah_tenant', JSON.stringify(tenant));
        } else {
            localStorage.removeItem('ayn_ruyah_tenant');
            localStorage.removeItem('retinalens_tenant');
        }
    },

    getActiveUser() {
        if (!this.activeUser) {
            const saved = localStorage.getItem('ayn_ruyah_user') || localStorage.getItem('retinalens_user');
            if (saved) {
                try { this.activeUser = JSON.parse(saved); } catch (e) {}
            }
        }
        return this.activeUser;
    },

    setActiveUser(user) {
        this.activeUser = user;
        if (user) {
            localStorage.setItem('ayn_ruyah_user', JSON.stringify(user));
        } else {
            localStorage.removeItem('ayn_ruyah_user');
            localStorage.removeItem('retinalens_user');
        }
    },

    clearSession() {
        this.resetCaches();
        this.activeUser = null;
        this.activeTenant = null;
        localStorage.removeItem('ayn_ruyah_user');
        localStorage.removeItem('ayn_ruyah_tenant');
        localStorage.removeItem('retinalens_user');
        localStorage.removeItem('retinalens_tenant');
    }
};

window.State = State;
window.DR_GRADES = DR_GRADES;
window.DR_RECOMMENDATIONS = DR_RECOMMENDATIONS;
