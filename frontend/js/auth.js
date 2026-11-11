/**
 * AYN RUYAH — Multi-Tenant Authentication & Workspace Switcher Module
 */

async function loadHospitalsList() {
    try {
        const data = await RetinaLensAPI.getHospitals();
        State.hospitals = data.hospitals || [];
        
        // Populate hospital select in login form safely using DOM APIs
        const loginSelect = document.getElementById('login-hospital-select');
        if (loginSelect) {
            loginSelect.textContent = '';
            State.hospitals.forEach(h => {
                const opt = document.createElement('option');
                opt.value = h.id;
                opt.textContent = `${h.name} (${h.city})`;
                loginSelect.appendChild(opt);
            });
        }

        // Populate workspace switcher in main header safely using DOM APIs
        const switcher = document.getElementById('workspace-switcher');
        if (switcher) {
            switcher.textContent = '';
            State.hospitals.forEach(h => {
                const opt = document.createElement('option');
                opt.value = h.id;
                opt.textContent = `${h.name} • ${h.city}`;
                switcher.appendChild(opt);
            });
            const current = State.getActiveTenant();
            if (current) switcher.value = current.id;
        }

        // If no active tenant, default to first hospital
        if (!State.getActiveTenant() && State.hospitals.length > 0) {
            State.setActiveTenant(State.hospitals[0]);
        }

        // Check backend health for demo_mode signal to safely toggle demo quick-fill chips
        try {
            const healthRes = await fetch('/api/health');
            if (healthRes.ok) {
                const healthData = await healthRes.json();
                if (healthData.demo_mode) {
                    const demoChips = document.getElementById('demo-login-chips');
                    if (demoChips) demoChips.classList.remove('hidden');
                }
            }
        } catch (_) {}
    } catch (err) {
        console.error('Failed to load hospitals directory:', err);
    }
}

function fillDemoLogin(role) {
    const profiles = {
        admin: { tenant: 'apex-retina-lucknow', user: 'admin_lucknow', pass: 'admin123' },
        doctor: { tenant: 'shroff-eye-delhi', user: 'dr_batra', pass: 'doctor123' },
        screener: { tenant: 'sankara-eye-bengaluru', user: 'screener_karthik', pass: 'screener123' }
    };
    const prof = profiles[role] || profiles.admin;
    const hs = document.getElementById('login-hospital-select');
    const un = document.getElementById('login-username');
    const pw = document.getElementById('login-password');
    if (hs) hs.value = prof.tenant;
    if (un) un.value = prof.user;
    if (pw) pw.value = prof.pass;
}

async function handleLogin() {
    const hospitalSelect = document.getElementById('login-hospital-select');
    const usernameInput = document.getElementById('login-username');
    const passwordInput = document.getElementById('login-password');
    const loginBtn = document.getElementById('login-submit-btn');

    const tenantId = hospitalSelect ? hospitalSelect.value : null;
    const username = usernameInput.value.trim();
    const password = passwordInput.value.trim();

    if (!username || !password) {
        showNotification('Please enter username and password', 'error');
        return;
    }

    try {
        loginBtn.disabled = true;
        loginBtn.innerHTML = '<i class="fas fa-spinner fa-spin mr-2"></i> Authenticating...';

        const res = await RetinaLensAPI.login(username, password, tenantId);
        State.resetCaches();
        State.setActiveUser(res.user);
        State.setActiveTenant(res.hospital);

        showNotification(`Welcome, ${res.user.full_name}! Connected to ${res.hospital.name}`, 'success');
        
        updateWorkspaceUI();
        navigate('app-shell');
        switchNav('dashboard');
    } catch (err) {
        showNotification(err.message || 'Login failed', 'error');
    } finally {
        loginBtn.disabled = false;
        loginBtn.innerHTML = '<i class="fas fa-sign-in-alt mr-2"></i> Connect to Screening Workspace';
    }
}

async function switchWorkspace(newTenantId) {
    if (!newTenantId) return;
    const target = State.hospitals.find(h => h.id === newTenantId);
    if (!target) return;

    if (typeof invalidateNavigationToken === 'function') {
        invalidateNavigationToken();
    }
    State.setActiveTenant(target);
    updateWorkspaceUI();
    showNotification(`Switched hospital workspace: ${target.name}`, 'info');

    // Reload active page content for the new hospital
    const activeTab = document.querySelector('.nav-btn.active')?.dataset.tab || 'dashboard';
    switchNav(activeTab);
}

async function handleLogout() {
    if (confirm('Are you sure you want to sign out of AYN RUYAH?')) {
        try {
            await RetinaLensAPI.logout();
        } catch (e) {}
        State.clearSession();
        navigate('login-page');
        showNotification('Signed out successfully', 'info');
    }
}

function updateWorkspaceUI() {
    const tenant = State.getActiveTenant();
    const user = State.getActiveUser();

    if (tenant) {
        const nameEl = document.getElementById('header-hospital-name');
        if (nameEl) nameEl.textContent = tenant.name;

        const locEl = document.getElementById('header-hospital-location');
        if (locEl) locEl.textContent = `${tenant.city}, ${tenant.state}`;

        const badgeEl = document.getElementById('header-hospital-badge');
        if (badgeEl) badgeEl.textContent = tenant.tier || 'Hospital';

        const logoEl = document.getElementById('header-hospital-logo');
        if (logoEl && tenant.logo_url) logoEl.src = tenant.logo_url;

        const switcher = document.getElementById('workspace-switcher');
        if (switcher) switcher.value = tenant.id;
    }

    if (user) {
        const userNameEl = document.getElementById('user-profile-name');
        if (userNameEl) userNameEl.textContent = user.full_name;

        const userRoleEl = document.getElementById('user-profile-role');
        const roleNames = {
            'hospital_admin': 'Hospital Administrator',
            'ophthalmologist': 'Ophthalmologist',
            'screening_operator': 'Screening Operator'
        };
        if (userRoleEl) userRoleEl.textContent = roleNames[user.role] || user.role;

        const initialsEl = document.getElementById('user-profile-initials');
        if (initialsEl) {
            const parts = user.full_name.split(' ');
            const init = (parts[0][0] + (parts[1] ? parts[1][0] : '')).toUpperCase();
            initialsEl.textContent = init;
        }
    }
}
