/**
 * AYN RUYAH — Indian Diabetic Retinopathy Patient Cohort Management Module
 */

let _patientsOffset = 0;
const _patientsLimit = 50;
let _patientSearchTimeout = null;
let _patientSearchGeneration = 0;

function renderPatientPaginationHtml(offset, fetchedCount, totalCount, visibleCount = null) {
    if (totalCount <= _patientsLimit && offset === 0) {
        return '';
    }
    const startRecord = totalCount > 0 ? offset + 1 : 0;
    const endRecord = Math.min(offset + fetchedCount, totalCount);
    const hasPrev = offset > 0;
    const prevOffset = Math.max(0, offset - _patientsLimit);
    const hasNext = offset + fetchedCount < totalCount;
    const nextOffset = offset + _patientsLimit;

    const countLabel = (visibleCount !== null && visibleCount !== fetchedCount)
        ? `Showing ${visibleCount} matching on page (${startRecord} - ${endRecord} of ${totalCount} records)`
        : `Showing ${startRecord} - ${endRecord} of ${totalCount} records`;

    return `
        <div class="flex items-center justify-between px-4 py-3 bg-white border border-[#D0E3F3] rounded-xl mt-4">
            <span class="text-xs text-[#8395A7]">
                ${countLabel}
            </span>
            <div class="flex items-center gap-2">
                <button type="button" ${!hasPrev ? 'disabled' : ''} onclick="loadPatientsContent(undefined, ${prevOffset})" class="btn btn-secondary text-xs px-3 py-1.5" ${!hasPrev ? 'style="opacity:0.5;cursor:not-allowed"' : ''}>
                    Previous
                </button>
                <button type="button" ${!hasNext ? 'disabled' : ''} onclick="loadPatientsContent(undefined, ${nextOffset})" class="btn btn-secondary text-xs px-3 py-1.5" ${!hasNext ? 'style="opacity:0.5;cursor:not-allowed"' : ''}>
                    Next
                </button>
            </div>
        </div>
    `;
}

function updatePatientsPaginationFooter(visibleCount = null) {
    const container = document.getElementById('patient-pagination-container');
    if (!container) return;
    const fetchedCount = State.patients ? State.patients.length : 0;
    const totalCount = State.patientsTotal !== undefined ? State.patientsTotal : fetchedCount;
    container.innerHTML = renderPatientPaginationHtml(_patientsOffset, fetchedCount, totalCount, visibleCount);
}

async function loadPatientsContent(token, offset = 0) {
    if (token === undefined) {
        token = getNavigationToken();
    }
    _patientsOffset = offset;
    const main = document.getElementById('main-viewport');
    if (!main) return;

    // Capture search, diabetes filter, age filter, and sort BEFORE replacing DOM
    const searchInput = document.getElementById('patient-search-input')?.value.trim() || '';
    const diabetesType = document.getElementById('filter-diabetes-type')?.value || '';
    const ageGroup = document.getElementById('filter-age-group')?.value || '';
    const sortBy = document.getElementById('sort-patients-by')?.value || 'id_desc';

    main.innerHTML = `
        <div class="flex items-center justify-center p-16">
            <div class="flex flex-col items-center gap-3">
                <i class="fas fa-spinner fa-spin text-3xl text-[#087E8B]"></i>
                <p class="text-xs font-semibold text-[#4B6584]">Loading Diabetic Patient Cohort...</p>
            </div>
        </div>
    `;

    try {
        const params = { 
            limit: _patientsLimit, 
            offset: _patientsOffset,
            search: searchInput || undefined,
            diabetes_type: diabetesType || undefined,
        };
        if (ageGroup === 'minor') {
            params.is_minor = true;
            params.max_age = 17;
        } else if (ageGroup === 'young') {
            params.min_age = 18;
            params.max_age = 40;
        } else if (ageGroup === 'middle') {
            params.min_age = 41;
            params.max_age = 60;
        } else if (ageGroup === 'senior') {
            params.min_age = 61;
        }

        const data = await RetinaLensAPI.getPatients(params);
        if (token !== undefined && token !== getNavigationToken()) return;
        State.patients = data.patients || [];
        State.patientsTotal = data.total !== undefined ? data.total : State.patients.length;
        renderPatientsUI();

        // Restore active search, filter and sort values into recreated controls
        const restoredSearch = document.getElementById('patient-search-input');
        if (restoredSearch && searchInput) restoredSearch.value = searchInput;
        const restoredDiabetes = document.getElementById('filter-diabetes-type');
        if (restoredDiabetes && diabetesType) restoredDiabetes.value = diabetesType;
        const restoredAge = document.getElementById('filter-age-group');
        if (restoredAge && ageGroup) restoredAge.value = ageGroup;
        const restoredSort = document.getElementById('sort-patients-by');
        if (restoredSort && sortBy) restoredSort.value = sortBy;

        if (searchInput || diabetesType || ageGroup || (sortBy && sortBy !== 'id_desc')) {
            filterPatients(false);
        }
    } catch (err) {
        if (token !== undefined && token !== getNavigationToken()) return;
        showNotification(err.message, 'error');
    }
}

function getPatientAvatarUrl(p) {
    if (p && p.avatar_url && !p.avatar_url.includes('dicebear')) {
        return p.avatar_url;
    }
    const g = (p && p.gender ? p.gender : '').toLowerCase();
    if (g === 'female') return '/assets/branding/avatar_female.svg';
    if (g === 'male') return '/assets/branding/avatar_male.svg';
    return '/assets/branding/avatar_placeholder.svg';
}

function renderPatientRows(patients) {
    if (!patients || patients.length === 0) return '';
    return patients.map(p => {
        const avatar = getPatientAvatarUrl(p);
        const hba1cHigh = p.hba1c && p.hba1c >= 8.0;
        return `
            <tr class="hover:bg-[#F5FAFF] transition-colors">
                <td class="py-3 px-4">
                    <div class="flex items-center gap-3">
                        <img src="${avatar}" class="w-9 h-9 rounded-full bg-[#EAF4FF] border border-[#D0E3F3] object-cover shrink-0" alt="Avatar">
                        <div class="min-w-0">
                            <div class="font-bold text-[#142D4E] flex items-center gap-1.5 flex-wrap">
                                <span>${escapeHtml(p.first_name)} ${escapeHtml(p.last_name)}</span>
                                ${p.is_minor ? '<span class="text-[9px] font-bold px-1.5 py-0.2 rounded bg-blue-100 text-blue-700">Minor</span>' : ''}
                                ${p.is_demo ? '<span class="badge badge-demo text-[9px] px-1 py-0.2">DEMO</span>' : ''}
                            </div>
                            <div class="text-[11px] text-[#8395A7] flex items-center gap-1 mt-0.5">
                                <i class="fas fa-phone text-[9px]"></i> ${escapeHtml(p.phone)}
                            </div>
                        </div>
                    </div>
                </td>
                <td class="py-3 px-4 whitespace-nowrap">
                    <span class="font-mono text-xs font-semibold text-[#087E8B] bg-[#EAF4FF] px-2 py-0.5 rounded border border-[#D0E3F3]">${escapeHtml(p.id)}</span>
                </td>
                <td class="py-3 px-4 whitespace-nowrap">
                    <div class="text-[#142D4E] font-medium">${escapeHtml(p.age)} yrs</div>
                    <div class="text-[11px] text-[#8395A7]">${escapeHtml(p.gender)}</div>
                </td>
                <td class="py-3 px-4 whitespace-nowrap">
                    <div class="text-[#142D4E]">${escapeHtml(p.city)}</div>
                    <div class="text-[11px] text-[#8395A7]">${escapeHtml(p.state)}</div>
                </td>
                <td class="py-3 px-4">
                    <div class="font-semibold text-[#142D4E]">${escapeHtml(p.diabetes_type)}</div>
                    <div class="text-[11px] text-[#8395A7]">${escapeHtml(p.diabetes_duration_years)} yrs duration</div>
                </td>
                <td class="py-3 px-4 text-center whitespace-nowrap">
                    <span class="inline-block px-2.5 py-0.5 rounded-full font-bold text-xs ${hba1cHigh ? 'bg-rose-50 text-rose-700 border border-rose-200' : 'bg-emerald-50 text-emerald-700 border border-emerald-200'}">
                        ${p.hba1c ? escapeHtml(p.hba1c) + '%' : 'Pending'}
                    </span>
                </td>
                <td class="py-3 px-4 text-right whitespace-nowrap">
                    <div class="flex items-center justify-end gap-1.5">
                        <button type="button" data-action="view-patient-profile" data-patient-id="${escapeHtml(p.id)}" class="btn btn-secondary text-xs py-1 px-2.5 h-8" title="View Patient Profile">
                            <i class="fas fa-user-circle text-[#087E8B]"></i> <span class="hidden sm:inline">Profile</span>
                        </button>
                        <button type="button" data-action="start-patient-screening" data-patient-id="${escapeHtml(p.id)}" class="btn btn-primary text-xs py-1 px-2.5 h-8 shadow-xs" title="Start Retinal Screening">
                            <i class="fas fa-eye"></i> <span class="hidden sm:inline">Scan</span>
                        </button>
                    </div>
                </td>
            </tr>
        `;
    }).join('');
}

function bindPatientActionButtons(container) {
    container.querySelectorAll('[data-action="view-patient-profile"]').forEach(btn => {
        btn.addEventListener('click', () => viewPatientProfile(btn.dataset.patientId));
    });
    container.querySelectorAll('[data-action="start-patient-screening"]').forEach(btn => {
        btn.addEventListener('click', () => startScreeningForPatient(btn.dataset.patientId));
    });
}

function renderPatientsUI(filteredPatients = null) {
    const main = document.getElementById('main-viewport');
    if (!main) return;

    const patients = filteredPatients !== null ? filteredPatients : State.patients;
    const tenant = State.getActiveTenant();
    const totalCount = State.patientsTotal !== undefined ? State.patientsTotal : State.patients.length;

    main.innerHTML = `
        <div class="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-6">
            <div>
                <h2 class="text-xl font-bold tracking-tight text-[#142D4E] flex items-center gap-2.5">
                    <i class="fas fa-users text-[#087E8B]"></i>
                    Diabetic Patient Cohort Registry
                </h2>
                <p id="patient-count-text" class="text-xs text-[#4B6584] mt-0.5">
                    Workspace: <strong class="text-[#087E8B]">${tenant ? escapeHtml(tenant.name) : ''}</strong> • Showing ${patients.length} of ${totalCount} Registered Patients
                </p>
            </div>
            <button onclick="openModal('register-patient-modal')" class="btn btn-primary self-start md:self-auto text-xs font-bold shadow-teal">
                <i class="fas fa-user-plus"></i> Register Indian Patient
            </button>
        </div>

        <!-- Search, Filter & Sort Toolbar -->
        <div class="filter-toolbar mb-6">
            <div class="search-input-wrap flex-1 min-w-[240px]">
                <i class="fas fa-search text-xs"></i>
                <input type="text" id="patient-search-input" oninput="filterPatients()" placeholder="Search by patient name, ID, phone, city..." class="form-input text-xs" aria-label="Search patients">
            </div>
            <div class="flex items-center gap-2.5 flex-wrap w-full md:w-auto">
                <select id="filter-diabetes-type" onchange="filterPatients()" class="form-select text-xs" aria-label="Filter by diabetes type">
                    <option value="">All Diabetes Types</option>
                    <option value="Type 2">Type 2 Diabetes</option>
                    <option value="Type 1">Type 1 Diabetes</option>
                    <option value="Gestational">Gestational Diabetes</option>
                    <option value="Pre-diabetes">Pre-diabetes</option>
                </select>
                <select id="filter-age-group" onchange="filterPatients()" class="form-select text-xs" aria-label="Filter by age group">
                    <option value="">All Age Groups</option>
                    <option value="minor">Adolescent / Pediatric (< 18)</option>
                    <option value="young">Young Adults (18-40)</option>
                    <option value="middle">Middle-aged (41-60)</option>
                    <option value="senior">Elderly (60+)</option>
                </select>
                <select id="sort-patients-by" onchange="filterPatients()" class="form-select text-xs" aria-label="Sort patients by">
                    <option value="id_desc">Sort: Newest First</option>
                    <option value="name_asc">Sort: Name (A-Z)</option>
                    <option value="age_asc">Sort: Age (Youngest)</option>
                    <option value="age_desc">Sort: Age (Oldest)</option>
                    <option value="hba1c_desc">Sort: Highest HbA1c</option>
                </select>
            </div>
        </div>

        <!-- Patient Registry Table Layout -->
        <div class="med-card p-0 overflow-hidden shadow-sm border border-[#E2EEF8] bg-white rounded-2xl">
            <div class="overflow-x-auto">
                <table class="w-full text-left border-collapse">
                    <thead>
                        <tr class="bg-[#F8FBFF] border-b border-[#E2EEF8] text-[11px] font-bold text-[#4B6584] uppercase tracking-wider">
                            <th class="py-3.5 px-4">Patient</th>
                            <th class="py-3.5 px-4">Patient ID</th>
                            <th class="py-3.5 px-4">Demographics</th>
                            <th class="py-3.5 px-4">Location</th>
                            <th class="py-3.5 px-4">Clinical Profile</th>
                            <th class="py-3.5 px-4 text-center">HbA1c</th>
                            <th class="py-3.5 px-4 text-right">Actions</th>
                        </tr>
                    </thead>
                    <tbody id="patient-table-tbody" class="divide-y divide-[#F0F4F8] text-xs">
                        ${renderPatientRows(patients)}
                    </tbody>
                </table>
            </div>
            <div id="patient-empty-message" class="${patients.length === 0 ? '' : 'hidden'} text-center py-16 text-[#8395A7] bg-white">
                No patients found matching the selected criteria.
            </div>
        </div>

        <div id="patient-pagination-container">
            ${renderPatientPaginationHtml(_patientsOffset, State.patients.length, totalCount, patients.length)}
        </div>
    `;

    bindPatientActionButtons(main);
}

function filterPatients(isServerSearch = true) {
    const query = document.getElementById('patient-search-input')?.value.trim() || '';
    const diabetesType = document.getElementById('filter-diabetes-type')?.value || '';
    const ageGroup = document.getElementById('filter-age-group')?.value || '';
    const sortBy = document.getElementById('sort-patients-by')?.value || 'id_desc';

    const applyFilterAndSort = (patientList) => {
        let filtered = patientList.filter(p => {
            const q = query.toLowerCase();
            const matchesQuery = !query || 
                p.first_name.toLowerCase().includes(q) ||
                p.last_name.toLowerCase().includes(q) ||
                p.id.toLowerCase().includes(q) ||
                (p.phone && p.phone.includes(query)) ||
                (p.city && p.city.toLowerCase().includes(q));

            const matchesDiabetes = !diabetesType || p.diabetes_type === diabetesType;

            let matchesAge = true;
            if (ageGroup === 'minor') matchesAge = p.age < 18;
            else if (ageGroup === 'young') matchesAge = p.age >= 18 && p.age <= 40;
            else if (ageGroup === 'middle') matchesAge = p.age > 40 && p.age <= 60;
            else if (ageGroup === 'senior') matchesAge = p.age > 60;

            return matchesQuery && matchesDiabetes && matchesAge;
        });

        filtered.sort((a, b) => {
            if (sortBy === 'name_asc') return `${a.first_name} ${a.last_name}`.localeCompare(`${b.first_name} ${b.last_name}`);
            if (sortBy === 'age_asc') return a.age - b.age;
            if (sortBy === 'age_desc') return b.age - a.age;
            if (sortBy === 'hba1c_desc') return (b.hba1c || 0) - (a.hba1c || 0);
            return b.id.localeCompare(a.id);
        });

        const tbody = document.getElementById('patient-table-tbody');
        const emptyMsg = document.getElementById('patient-empty-message');
        const countText = document.getElementById('patient-count-text');

        if (tbody) {
            tbody.innerHTML = renderPatientRows(filtered);
            bindPatientActionButtons(tbody);
            if (emptyMsg) {
                if (filtered.length === 0) emptyMsg.classList.remove('hidden');
                else emptyMsg.classList.add('hidden');
            }
            if (countText) {
                const tenant = State.getActiveTenant();
                const total = State.patientsTotal !== undefined ? State.patientsTotal : State.patients.length;
                countText.innerHTML = `Workspace: <strong class="text-[#087E8B]">${tenant ? escapeHtml(tenant.name) : ''}</strong> • Showing ${filtered.length} of ${total} Registered Patients`;
            }
            updatePatientsPaginationFooter(filtered.length);
        }
    };

    applyFilterAndSort(State.patients);

    // Debounced server search across the full registry
    if (isServerSearch) {
        if (_patientSearchTimeout) clearTimeout(_patientSearchTimeout);
        const currentGen = ++_patientSearchGeneration;
        _patientSearchTimeout = setTimeout(async () => {
            try {
                const params = {
                    search: query || undefined,
                    diabetes_type: diabetesType || undefined,
                    limit: _patientsLimit,
                    offset: 0
                };
                if (ageGroup === 'minor') {
                    params.is_minor = true;
                    params.max_age = 17;
                } else if (ageGroup === 'young') {
                    params.min_age = 18;
                    params.max_age = 40;
                } else if (ageGroup === 'middle') {
                    params.min_age = 41;
                    params.max_age = 60;
                } else if (ageGroup === 'senior') {
                    params.min_age = 61;
                }
                const data = await RetinaLensAPI.getPatients(params);
                if (currentGen !== _patientSearchGeneration) return;

                State.patients = data.patients || [];
                State.patientsTotal = data.total !== undefined ? data.total : State.patients.length;
                _patientsOffset = 0;
                applyFilterAndSort(State.patients);
            } catch (err) {
                if (currentGen !== _patientSearchGeneration) return;
                console.error('Failed server-side patient search:', err);
            }
        }, 300);
    }
}

async function viewPatientProfile(patientId) {
    try {
        const patient = await RetinaLensAPI.getPatient(patientId);
        const screeningsData = await RetinaLensAPI.getPatientScreenings(patientId);
        const pastScreenings = screeningsData.screenings || [];

        const modal = document.getElementById('view-patient-modal');
        const modalBody = document.getElementById('view-patient-modal-content');
        if (!modal || !modalBody) return;

        modalBody.innerHTML = `
            <div class="flex flex-col sm:flex-row items-start justify-between border-b border-[#E2EEF8] pb-6 mb-6 gap-4">
                <div class="flex items-center gap-4">
                    <img src="${getPatientAvatarUrl(patient)}" class="w-16 h-16 rounded-2xl bg-[#EAF4FF] border border-[#D0E3F3] object-cover" alt="Patient">
                    <div>
                        <div class="flex items-center gap-2">
                            <h3 class="text-xl font-bold text-[#142D4E]">${escapeHtml(patient.first_name)} ${escapeHtml(patient.last_name)}</h3>
                            ${patient.is_minor ? '<span class="px-2 py-0.5 rounded bg-blue-100 text-blue-700 text-xs font-bold">Adolescent</span>' : ''}
                        </div>
                        <p class="text-xs text-[#8395A7] font-mono mt-0.5">Patient ID: ${escapeHtml(patient.id)} • Registered under ${escapeHtml(State.getActiveTenant().name)}</p>
                        <p class="text-xs text-[#4B6584] mt-1.5">
                            <i class="fas fa-map-marker-alt text-[#087E8B] mr-1"></i> ${escapeHtml(patient.address)}, ${escapeHtml(patient.city)}, ${escapeHtml(patient.state)} - ${escapeHtml(patient.pincode || '')}
                        </p>
                    </div>
                </div>
                <button onclick="startScreeningForPatient('${escapeHtml(patient.id)}'); closeModal('view-patient-modal');" class="btn btn-primary text-xs shadow-teal">
                    <i class="fas fa-eye"></i> Launch Retinal Scan
                </button>
            </div>

            <!-- Clinical Demographics & Diabetes Profile Grid -->
            <div class="grid grid-cols-1 md:grid-cols-2 gap-5 mb-6">
                <div class="p-4 rounded-xl bg-[#F8FBFF] border border-[#E2EEF8] space-y-2.5">
                    <h4 class="text-xs font-bold text-[#142D4E] uppercase tracking-wider mb-2">Demographic Profile</h4>
                    <div class="flex justify-between text-xs"><span class="text-[#8395A7]">Age / Gender:</span> <span class="font-semibold text-[#142D4E]">${escapeHtml(patient.age)} years • ${escapeHtml(patient.gender)}</span></div>
                    <div class="flex justify-between text-xs"><span class="text-[#8395A7]">Date of Birth:</span> <span class="text-[#142D4E]">${escapeHtml(patient.dob)}</span></div>
                    <div class="flex justify-between text-xs"><span class="text-[#8395A7]">Phone:</span> <span class="text-[#142D4E] font-medium">${escapeHtml(patient.phone)}</span></div>
                    <div class="flex justify-between text-xs"><span class="text-[#8395A7]">Email:</span> <span class="text-[#142D4E]">${patient.email ? escapeHtml(patient.email) : 'N/A'}</span></div>
                    ${patient.is_minor ? `
                        <div class="mt-3 pt-3 border-t border-[#E2EEF8] bg-blue-50/60 p-2.5 rounded-lg border border-blue-200">
                            <p class="text-xs font-bold text-blue-700 uppercase mb-0.5">Guardian Information (Pediatric)</p>
                            <p class="text-xs text-[#4B6584]">${escapeHtml(patient.guardian_name || '')} (${escapeHtml(patient.guardian_relation || '')}) • Tel: ${escapeHtml(patient.guardian_phone || '')}</p>
                        </div>
                    ` : ''}
                </div>

                <div class="p-4 rounded-xl bg-[#F8FBFF] border border-[#E2EEF8] space-y-2.5">
                    <h4 class="text-xs font-bold text-[#142D4E] uppercase tracking-wider mb-2">Diabetes & Clinical History</h4>
                    <div class="flex justify-between text-xs"><span class="text-[#8395A7]">Diabetes Classification:</span> <span class="font-bold text-[#087E8B]">${escapeHtml(patient.diabetes_type)}</span></div>
                    <div class="flex justify-between text-xs"><span class="text-[#8395A7]">Duration of Diabetes:</span> <span class="font-semibold text-[#142D4E]">${escapeHtml(patient.diabetes_duration_years)} years</span></div>
                    <div class="flex justify-between text-xs"><span class="text-[#8395A7]">Recent HbA1c:</span> <span class="font-bold ${patient.hba1c >= 8 ? 'text-rose-600' : 'text-emerald-600'}">${patient.hba1c ? escapeHtml(patient.hba1c) + '%' : 'Pending'}</span></div>
                    <div class="flex justify-between text-xs"><span class="text-[#8395A7]">Insulin Regimen:</span> <span class="text-[#142D4E]">${patient.insulin_dependent ? 'Yes (Insulin Dependent)' : 'Oral Hypoglycemics'}</span></div>
                    <div class="flex justify-between text-xs"><span class="text-[#8395A7]">Hypertension:</span> <span class="text-[#142D4E]">${patient.hypertension ? 'Documented (+)' : 'Normotensive'}</span></div>
                    <p class="text-[11px] text-[#4B6584] mt-2 bg-white p-2 rounded-lg border border-[#E2EEF8]">
                        <strong>Clinical Notes:</strong> ${patient.clinical_notes ? escapeHtml(patient.clinical_notes) : 'None recorded.'}
                    </p>
                </div>
            </div>

            <!-- Historical Screening Timeline -->
            <div>
                <h4 class="text-sm font-bold text-[#142D4E] mb-3 flex items-center gap-2">
                    <i class="fas fa-history text-[#087E8B]"></i> Retinal Screening Audit History (${pastScreenings.length})
                </h4>

                <div class="space-y-3">
                    ${pastScreenings.map(s => {
                        const gradeInfo = DR_GRADES[s.grade] || DR_GRADES[0];
                        return `
                            <div class="p-4 rounded-xl bg-white border border-[#E2EEF8] flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
                                <div class="flex items-center gap-3.5">
                                    <div class="w-14 h-14 rounded-xl overflow-hidden bg-black border border-slate-200 shrink-0">
                                        <img src="${s.heatmap_image_path || s.original_image_path || '/sample_images/grade0_14197_left-600.jpg'}" onerror="this.src='/sample_images/grade0_14197_left-600.jpg'" class="w-full h-full object-cover" alt="Thumbnail">
                                    </div>
                                    <div>
                                        <div class="flex items-center gap-2">
                                            <span class="font-bold text-[#142D4E] text-sm">${escapeHtml(s.diagnosis)}</span>
                                            <span class="badge ${gradeInfo.badge} text-xs">
                                                Grade ${s.grade}
                                            </span>
                                            ${s.is_demo ? '<span class="badge badge-demo">DEMO</span>' : ''}
                                        </div>
                                        <p class="text-xs text-[#8395A7] mt-0.5">${escapeHtml(s.eye)} • Screened on ${new Date(s.created_at).toLocaleString()}</p>
                                        <p class="text-xs text-[#087E8B] mt-1 font-medium">${escapeHtml(s.recommendation)}</p>
                                    </div>
                                </div>
                                <div class="text-right">
                                    <p class="text-xs font-bold text-[#087E8B]">${parseFloat(s.confidence || 0).toFixed(1)}% Confidence</p>
                                    <p class="text-[11px] text-[#8395A7] mt-0.5">Status: <span class="font-semibold text-[#142D4E]">${escapeHtml(s.status)}</span></p>
                                </div>
                            </div>
                        `;
                    }).join('')}
                    ${pastScreenings.length === 0 ? '<p class="text-xs text-[#8395A7] text-center py-6 bg-[#F8FBFF] rounded-xl border border-[#E2EEF8]">No previous AI retinal screenings recorded for this patient.</p>' : ''}
                </div>
            </div>
        `;

        openModal('view-patient-modal');
    } catch (err) {
        showNotification(err.message, 'error');
    }
}

async function handleRegisterPatientSubmit(event) {
    event.preventDefault();
    const form = event.target;
    const btn = form.querySelector('button[type="submit"]');

    const payload = {
        first_name: form.first_name.value.trim(),
        last_name: form.last_name.value.trim(),
        gender: form.gender.value,
        dob: form.dob.value,
        age: parseInt(form.age.value, 10),
        phone: form.phone.value.trim(),
        email: form.email.value.trim() || null,
        address: form.address.value.trim(),
        city: form.city.value.trim(),
        state: form.state.value.trim(),
        pincode: form.pincode.value.trim() || null,
        diabetes_type: form.diabetes_type.value,
        diabetes_duration_years: parseFloat(form.diabetes_duration.value),
        hba1c: form.hba1c.value ? parseFloat(form.hba1c.value) : null,
        insulin_dependent: form.insulin.checked ? 1 : 0,
        hypertension: form.hypertension.checked ? 1 : 0,
        clinical_notes: form.notes.value.trim() || null,
        guardian_name: form.guardian_name?.value.trim() || null,
        guardian_relation: form.guardian_relation?.value.trim() || null,
        guardian_phone: form.guardian_phone?.value.trim() || null,
    };

    try {
        btn.disabled = true;
        btn.innerHTML = '<i class="fas fa-spinner fa-spin mr-2"></i> Registering...';

        const res = await RetinaLensAPI.registerPatient(payload);
        showNotification(`Patient ${res.patient.first_name} ${res.patient.last_name} registered successfully!`, 'success');
        closeModal('register-patient-modal');
        form.reset();
        await loadPatientsContent();
    } catch (err) {
        showNotification(err.message || 'Registration failed', 'error');
    } finally {
        btn.disabled = false;
        btn.innerHTML = '<i class="fas fa-check-circle mr-2"></i> Complete Patient Registration';
    }
}

function startScreeningForPatient(patientId) {
    const patient = State.patients.find(p => p.id === patientId);
    if (patient) {
        State.selectedPatientForAI = patient;
    }
    switchNav('screening');
}
