/**
 * AYN RUYAH — Hospital Settings & Multi-Tenant User Management Module
 */

async function loadSettingsContent(token) {
    if (token === undefined) {
        token = getNavigationToken();
    }
    const main = document.getElementById('main-viewport');
    if (!main) return;

    main.innerHTML = `
        <div class="flex items-center justify-center p-16">
            <div class="flex flex-col items-center gap-3">
                <i class="fas fa-spinner fa-spin text-3xl text-[#087E8B]"></i>
                <p class="text-xs font-semibold text-[#4B6584]">Loading Hospital Settings...</p>
            </div>
        </div>
    `;

    try {
        const tenant = State.getActiveTenant();
        if (!tenant) throw new Error('No active hospital workspace');

        const staff = await RetinaLensAPI.getHospitalStaff(tenant.id);
        if (token !== undefined && token !== getNavigationToken()) return;

        main.innerHTML = `
            <div class="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-6">
                <div>
                    <h2 class="text-xl font-bold tracking-tight text-[#142D4E] flex items-center gap-2.5">
                        <i class="fas fa-hospital text-[#087E8B]"></i>
                        Hospital Configuration & Staff Management
                    </h2>
                    <p class="text-xs text-[#4B6584] mt-0.5">
                        Workspace: <strong class="text-[#087E8B]">${escapeHtml(tenant.name)}</strong> • Tenant ID: <span class="font-mono text-xs text-[#8395A7]">${escapeHtml(tenant.id)}</span>
                    </p>
                </div>
                <div class="flex gap-2.5">
                    <button onclick="openModal('onboard-hospital-modal')" class="btn btn-secondary text-xs font-semibold">
                        <i class="fas fa-plus-circle text-[#087E8B]"></i> Onboard New Hospital
                    </button>
                    <button onclick="openModal('add-staff-modal')" class="btn btn-primary text-xs font-bold shadow-teal">
                        <i class="fas fa-user-plus"></i> Add Medical Staff
                    </button>
                </div>
            </div>

            <div class="grid grid-cols-1 lg:grid-cols-12 gap-6">
                <!-- Hospital Profile Form (5 cols) -->
                <div class="lg:col-span-5 med-card space-y-4">
                    <h3 class="text-xs uppercase tracking-wider font-bold text-[#142D4E] flex items-center gap-2">
                        <i class="fas fa-building text-[#087E8B]"></i> Hospital Profile & Branding
                    </h3>

                    <form onsubmit="handleUpdateHospitalProfile(event)" class="space-y-3.5">
                        <div>
                            <label class="text-xs font-semibold text-[#142D4E] block mb-1">Hospital / Institute Name</label>
                            <input type="text" name="name" value="${escapeHtml(tenant.name)}" class="form-input text-xs" required>
                        </div>

                        <div class="grid grid-cols-2 gap-3">
                            <div>
                                <label class="text-xs font-semibold text-[#142D4E] block mb-1">Registration #</label>
                                <input type="text" name="registration_number" value="${escapeHtml(tenant.registration_number || '')}" class="form-input text-xs">
                            </div>
                            <div>
                                <label class="text-xs font-semibold text-[#142D4E] block mb-1">Facility Tier</label>
                                <input type="text" name="tier" value="${escapeHtml(tenant.tier || 'Tertiary Eye Care')}" class="form-input text-xs">
                            </div>
                        </div>

                        <div>
                            <label class="text-xs font-semibold text-[#142D4E] block mb-1">Address</label>
                            <input type="text" name="address" value="${escapeHtml(tenant.address)}" class="form-input text-xs" required>
                        </div>

                        <div class="grid grid-cols-2 gap-3">
                            <div>
                                <label class="text-xs font-semibold text-[#142D4E] block mb-1">City</label>
                                <input type="text" name="city" value="${escapeHtml(tenant.city)}" class="form-input text-xs" required>
                            </div>
                            <div>
                                <label class="text-xs font-semibold text-[#142D4E] block mb-1">State</label>
                                <input type="text" name="state" value="${escapeHtml(tenant.state)}" class="form-input text-xs" required>
                            </div>
                        </div>

                        <div class="grid grid-cols-2 gap-3">
                            <div>
                                <label class="text-xs font-semibold text-[#142D4E] block mb-1">Contact Email</label>
                                <input type="email" name="contact_email" value="${escapeHtml(tenant.contact_email)}" class="form-input text-xs" required>
                            </div>
                            <div>
                                <label class="text-xs font-semibold text-[#142D4E] block mb-1">Contact Phone</label>
                                <input type="text" name="contact_phone" value="${escapeHtml(tenant.contact_phone)}" class="form-input text-xs" required>
                            </div>
                        </div>

                        <div>
                            <label class="text-xs font-semibold text-[#142D4E] block mb-1">Logo URL (SVG / PNG)</label>
                            <input type="url" name="logo_url" value="${escapeHtml(tenant.logo_url || '')}" class="form-input text-xs">
                        </div>

                        <button type="submit" class="btn btn-primary w-full py-2.5 text-xs font-bold shadow-teal mt-2">
                            <i class="fas fa-save mr-1"></i> Save Hospital Profile
                        </button>
                    </form>
                </div>

                <!-- Authorized Medical Staff (7 cols) -->
                <div class="lg:col-span-7 med-card space-y-4">
                    <div class="flex items-center justify-between">
                        <h3 class="text-xs uppercase tracking-wider font-bold text-[#142D4E] flex items-center gap-2">
                            <i class="fas fa-user-shield text-[#087E8B]"></i> Authorized Medical Personnel (${staff.length})
                        </h3>
                        <span class="text-[10px] text-[#8395A7]">Role-Based Access Control</span>
                    </div>

                    <div class="space-y-3">
                        ${staff.map(u => {
                            const roleBadges = {
                                'hospital_admin': 'bg-purple-100 text-purple-700 border-purple-200',
                                'ophthalmologist': 'bg-teal-100 text-[#087E8B] border-teal-200',
                                'screening_operator': 'bg-blue-100 text-blue-700 border-blue-200',
                            };
                            const roleTitles = {
                                'hospital_admin': 'Hospital Admin',
                                'ophthalmologist': 'Ophthalmologist',
                                'screening_operator': 'Screening Operator',
                            };

                            return `
                                <div class="p-3.5 rounded-xl bg-[#F8FBFF] border border-[#E2EEF8] flex items-center justify-between">
                                    <div class="flex items-center gap-3.5">
                                        <div class="w-10 h-10 rounded-xl bg-[#E6F6F7] border border-teal-200 flex items-center justify-center text-xs font-bold text-[#087E8B]">
                                            ${escapeHtml(u.full_name.split(' ').map(n=>n[0]).slice(0,2).join(''))}
                                        </div>
                                        <div>
                                            <h4 class="font-bold text-xs text-[#142D4E]">${escapeHtml(u.full_name)}</h4>
                                            <p class="text-[11px] text-[#8395A7]">@${escapeHtml(u.username)} • ${escapeHtml(u.email)}</p>
                                            <p class="text-[10px] text-[#4B6584] mt-0.5">${escapeHtml(u.qualification || 'Certified Practitioner')}</p>
                                        </div>
                                    </div>
                                    <span class="text-xs font-bold px-2.5 py-0.5 rounded-full border ${roleBadges[u.role] || 'bg-slate-100 text-slate-700'}">
                                        ${escapeHtml(roleTitles[u.role] || u.role)}
                                    </span>
                                </div>
                            `;
                        }).join('')}
                    </div>
                </div>
            </div>
        `;
    } catch (err) {
        if (token !== undefined && token !== getNavigationToken()) return;
        showNotification(err.message, 'error');
    }
}

async function handleUpdateHospitalProfile(event) {
    event.preventDefault();
    const form = event.target;
    const tenant = State.getActiveTenant();
    if (!tenant) return;

    const updates = {
        name: form.name.value.trim(),
        registration_number: form.registration_number.value.trim() || null,
        tier: form.tier.value.trim() || null,
        address: form.address.value.trim(),
        city: form.city.value.trim(),
        state: form.state.value.trim(),
        contact_email: form.contact_email.value.trim(),
        contact_phone: form.contact_phone.value.trim(),
        logo_url: form.logo_url.value.trim() || null,
    };

    try {
        const res = await RetinaLensAPI.updateHospitalProfile(tenant.id, updates);
        State.setActiveTenant(res.hospital);
        updateWorkspaceUI();
        showNotification('Hospital profile updated successfully', 'success');
        await loadSettingsContent();
    } catch (err) {
        showNotification(err.message || 'Failed to update profile', 'error');
    }
}

async function handleAddStaffSubmit(event) {
    event.preventDefault();
    const form = event.target;
    const tenant = State.getActiveTenant();
    if (!tenant) return;

    const payload = {
        username: form.username.value.trim(),
        password: form.password.value.trim(),
        full_name: form.full_name.value.trim(),
        role: form.role.value,
        email: form.email.value.trim(),
        phone: (form.phone && form.phone.value) ? (form.phone.value.trim() || null) : null,
        qualification: (form.qualification && form.qualification.value) ? (form.qualification.value.trim() || null) : null,
    };

    try {
        await RetinaLensAPI.addHospitalStaff(tenant.id, payload);
        showNotification(`Staff member ${payload.full_name} added to workspace!`, 'success');
        closeModal('add-staff-modal');
        form.reset();
        await loadSettingsContent();
    } catch (err) {
        showNotification(err.message || 'Failed to add staff', 'error');
    }
}

async function handleOnboardHospitalSubmit(event) {
    event.preventDefault();
    const form = event.target;

    const payload = {
        id: form.hospital_id.value.trim().toLowerCase().replace(/\s+/g, '-'),
        name: form.name.value.trim(),
        city: form.city.value.trim(),
        state: form.state.value.trim(),
        address: form.address.value.trim(),
        contact_email: form.contact_email.value.trim(),
        contact_phone: form.contact_phone.value.trim(),
        registration_number: form.registration_number.value.trim() || null,
        tier: 'Hospital',
        admin: {
            username: form.admin_username.value.trim(),
            password: form.admin_password.value.trim(),
            full_name: form.admin_name.value.trim(),
            email: form.contact_email.value.trim(),
            phone: form.contact_phone.value.trim(),
            qualification: 'Chief Medical Administrator',
        }
    };

    try {
        const res = await RetinaLensAPI.registerHospital(payload);
        showNotification(`Hospital ${res.hospital.name} registered successfully!`, 'success');
        closeModal('onboard-hospital-modal');
        form.reset();
        await loadHospitalsList();
        switchWorkspace(res.hospital.id);
    } catch (err) {
        showNotification(err.message || 'Hospital onboarding failed', 'error');
    }
}
