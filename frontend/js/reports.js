/**
 * AYN RUYAH — Clinical Screening Reports & PDF Generation Module
 */

let _reportsOffset = 0;
const _reportsLimit = 50;

async function loadReportsContent(token, offset = 0) {
    if (token === undefined) {
        token = getNavigationToken();
    }
    _reportsOffset = offset;
    const main = document.getElementById('main-viewport');
    if (!main) return;

    main.innerHTML = `
        <div class="flex items-center justify-center p-16">
            <div class="flex flex-col items-center gap-3">
                <i class="fas fa-spinner fa-spin text-3xl text-[#087E8B]"></i>
                <p class="text-xs font-semibold text-[#4B6584]">Loading Screening Audit Reports...</p>
            </div>
        </div>
    `;

    try {
        if (!State.patients || State.patients.length === 0) {
            try {
                const patData = await RetinaLensAPI.getPatients({ limit: 100 });
                State.patients = patData.patients || [];
            } catch (_) {}
        }
        const data = await RetinaLensAPI.getScreenings({ limit: _reportsLimit, offset: _reportsOffset });
        if (token !== undefined && token !== getNavigationToken()) return;
        State.screenings = data.screenings || [];
        State.screeningsTotal = data.total || State.screenings.length;
        renderReportsTable(State.screenings, '', _reportsOffset, State.screeningsTotal);
    } catch (err) {
        if (token !== undefined && token !== getNavigationToken()) return;
        showNotification(err.message, 'error');
    }
}

function renderReportsTable(screenings, selectedGrade = '', offset = 0, total = 0) {
    const main = document.getElementById('main-viewport');
    if (!main) return;

    const tenant = State.getActiveTenant();

    main.innerHTML = `
        <div class="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-6">
            <div>
                <h2 class="text-xl font-bold tracking-tight text-[#142D4E] flex items-center gap-2.5">
                    <i class="fas fa-file-medical text-[#087E8B]"></i>
                    Clinical Screening Reports & Audit Log
                </h2>
                <p class="text-xs text-[#4B6584] mt-0.5">
                    Workspace: <strong class="text-[#087E8B]">${tenant ? escapeHtml(tenant.name) : ''}</strong> • ${total || screenings.length} Evaluated Screenings Archive
                </p>
            </div>
            <div class="flex items-center gap-3">
                <select id="report-filter-grade" onchange="filterReportsTable(this.value)" class="form-select text-xs">
                    <option value="" ${selectedGrade === '' ? 'selected' : ''}>All DR Grades (0-4)</option>
                    <option value="0" ${selectedGrade === '0' ? 'selected' : ''}>Grade 0 — No DR</option>
                    <option value="1" ${selectedGrade === '1' ? 'selected' : ''}>Grade 1 — Mild NPDR</option>
                    <option value="2" ${selectedGrade === '2' ? 'selected' : ''}>Grade 2 — Moderate NPDR</option>
                    <option value="3" ${selectedGrade === '3' ? 'selected' : ''}>Grade 3 — Severe NPDR</option>
                    <option value="4" ${selectedGrade === '4' ? 'selected' : ''}>Grade 4 — Proliferative DR</option>
                </select>
            </div>
        </div>

        <div class="med-table-wrap">
            <table class="med-table">
                <thead>
                    <tr>
                        <th>Scan Preview</th>
                        <th>Patient ID & Name</th>
                        <th>DR Grade & Diagnosis</th>
                        <th>Examined Eye</th>
                        <th>Confidence</th>
                        <th>Screening Date</th>
                        <th class="text-right">Actions</th>
                    </tr>
                </thead>
                <tbody>
                    ${screenings.map(s => {
                        const gradeInfo = DR_GRADES[s.grade] || DR_GRADES[0];
                        const patient = State.patients.find(p => p.id === s.patient_id);
                        const patName = s.patient_name || (patient ? `${patient.first_name} ${patient.last_name}` : s.patient_id);

                        return `
                            <tr>
                                <td>
                                    <img src="${s.heatmap_image_path || s.original_image_path || '/sample_images/grade0_14197_left-600.jpg'}" onerror="this.src='/sample_images/grade0_14197_left-600.jpg'" class="scan-thumb" alt="Scan">
                                </td>
                                <td>
                                    <p class="font-bold text-[#142D4E] text-xs">${escapeHtml(patName)}</p>
                                    <p class="text-[11px] text-[#8395A7] font-mono">${escapeHtml(s.patient_id)}</p>
                                </td>
                                <td>
                                    <div class="flex items-center gap-1.5 flex-wrap">
                                        <span class="badge ${gradeInfo.badge} text-[11px]">
                                            Grade ${s.grade}
                                        </span>
                                        <span class="text-xs text-[#142D4E] font-medium">${escapeHtml(s.diagnosis)}</span>
                                        ${s.is_demo ? '<span class="badge badge-demo">DEMO</span>' : ''}
                                    </div>
                                </td>
                                <td class="text-xs text-[#4B6584]">${escapeHtml(s.eye)}</td>
                                <td>
                                    <span class="font-mono font-bold text-[#087E8B] text-xs">${parseFloat(s.confidence || 0).toFixed(1)}%</span>
                                </td>
                                <td class="text-xs text-[#8395A7]">
                                    ${new Date(s.created_at).toLocaleDateString()}
                                </td>
                                <td class="text-right">
                                    <button onclick="downloadScreeningPDFById('${escapeHtml(s.id)}')" class="btn btn-secondary btn-sm text-xs font-semibold" title="Download PDF Report">
                                        <i class="fas fa-file-pdf text-[#087E8B]"></i> PDF
                                    </button>
                                </td>
                            </tr>
                        `;
                    }).join('')}
                </tbody>
            </table>
            ${screenings.length === 0 ? '<p class="text-center py-12 text-[#8395A7]">No screenings recorded for the selected filter.</p>' : ''}
        </div>

        ${total > _reportsLimit ? `
            <div class="flex items-center justify-between px-4 py-3 bg-white border border-[#D0E3F3] rounded-xl mt-4">
                <span class="text-xs text-[#8395A7]">
                    Showing ${offset + 1} - ${Math.min(offset + screenings.length, total)} of ${total} records
                </span>
                <div class="flex items-center gap-2">
                    <button ${offset <= 0 ? 'disabled' : ''} onclick="loadReportsContent(undefined, Math.max(0, ${offset - _reportsLimit}))" class="btn btn-secondary text-xs px-3 py-1.5" ${offset <= 0 ? 'style=\"opacity:0.5;cursor:not-allowed\"' : ''}>
                        Previous
                    </button>
                    <button ${offset + screenings.length >= total ? 'disabled' : ''} onclick="loadReportsContent(undefined, ${offset + _reportsLimit})" class="btn btn-secondary text-xs px-3 py-1.5" ${offset + screenings.length >= total ? 'style=\"opacity:0.5;cursor:not-allowed\"' : ''}>
                        Next
                    </button>
                </div>
            </div>
        ` : ''}
    `;
}

function filterReportsTable(gradeVal) {
    const valStr = gradeVal !== undefined && gradeVal !== null ? String(gradeVal) : '';
    if (valStr === '') {
        renderReportsTable(State.screenings, '');
    } else {
        const gradeNum = parseInt(valStr, 10);
        const filtered = State.screenings.filter(s => s.grade === gradeNum);
        renderReportsTable(filtered, valStr);
    }
}

async function viewScreeningReportDetails(screeningId) {
    downloadScreeningPDFById(screeningId);
}

async function downloadScreeningPDFById(screeningId) {
    try {
        const activeTenant = State.getActiveTenant();
        if (!activeTenant || !activeTenant.id) {
            showNotification('No active hospital workspace.', 'error');
            return;
        }
        const activeTenantId = activeTenant.id;

        const screening = await RetinaLensAPI.getScreeningDetail(screeningId);
        const patient = await RetinaLensAPI.getPatient(screening.patient_id);
        
        // Verify tenant has not changed while awaiting responses
        const currentTenant = State.getActiveTenant();
        if (!currentTenant || currentTenant.id !== activeTenantId || screening.tenant_id !== activeTenantId) {
            showNotification('Hospital workspace mismatch: report generation aborted.', 'warning');
            return;
        }

        const user = State.getActiveUser();
        generateClinicalReportPDF(screening, patient, currentTenant, user);
    } catch (err) {
        showNotification(err.message, 'error');
    }
}

function safePdfText(txt) {
    if (txt === null || txt === undefined) return '';
    // Strip non-printable ASCII or replace non-Latin glyphs with closest ASCII representation
    return String(txt).normalize('NFKD').replace(/[^\x20-\x7E]/g, '').trim() || String(txt).replace(/[^a-zA-Z0-9\s.,_\-()#]/g, '');
}

function generateClinicalReportPDF(screening, patient, tenant, user) {
    if (!window.jspdf || !window.jspdf.jsPDF) {
        showNotification('jsPDF library not loaded', 'error');
        return;
    }

    try {
        const doc = new window.jspdf.jsPDF({
            orientation: 'portrait',
            unit: 'mm',
            format: 'a4',
        });

        const pageWidth = doc.internal.pageSize.getWidth();

        // 1. Hospital Header Bar
        doc.setFillColor(8, 126, 139); // Teal header
        doc.rect(0, 0, pageWidth, 40, 'F');

        doc.setTextColor(255, 255, 255);
        doc.setFontSize(16);
        doc.setFont('helvetica', 'bold');
        doc.text('AYN RUYAH — CLINICAL DIABETIC RETINOPATHY REPORT', 14, 15);

        doc.setFontSize(10);
        doc.setFont('helvetica', 'normal');
        doc.text('A New Vision for Eye Care • AI-Powered 5-Grade ICDR Tele-Screening', 14, 21);

        doc.setFontSize(9);
        doc.setTextColor(230, 246, 247);
        const tenantNameSafe = safePdfText(tenant ? tenant.name : 'Ophthalmic Facility');
        const tenantLocSafe = safePdfText(`${tenant ? tenant.city : ''}, ${tenant ? tenant.state : ''}`);
        const tenantPhoneSafe = safePdfText(tenant ? tenant.contact_phone : 'N/A');
        doc.text(`${tenantNameSafe} • ${tenantLocSafe} (Tel: ${tenantPhoneSafe})`, 14, 28);
        doc.text(`Generated: ${new Date().toLocaleString()} • Report ID: ${safePdfText(screening.id)}`, 14, 34);

        // 2. Patient Demographics & Diabetes Profile Box
        doc.setDrawColor(210, 227, 243);
        doc.setFillColor(245, 250, 255);
        doc.roundedRect(14, 46, pageWidth - 28, 42, 3, 3, 'FD');

        doc.setTextColor(20, 45, 78);
        doc.setFontSize(10);
        doc.setFont('helvetica', 'bold');
        doc.text('PATIENT DEMOGRAPHICS & CLINICAL DIABETES PROFILE', 18, 54);

        doc.setFont('helvetica', 'normal');
        doc.setFontSize(9);
        doc.setTextColor(75, 101, 132);

        const rawPatName = patient ? `${patient.first_name} ${patient.last_name}` : screening.patient_id;
        const patName = safePdfText(rawPatName) || (patient ? patient.id : screening.patient_id);
        const patId = safePdfText(patient ? patient.id : screening.patient_id);
        const patAgeGender = patient ? `${patient.age} yrs / ${patient.gender}` : 'N/A';
        const patDiabetes = patient ? `${safePdfText(patient.diabetes_type)} (${patient.diabetes_duration_years} yrs duration)` : 'N/A';
        const patHbA1c = patient && patient.hba1c ? `${patient.hba1c}%` : 'Not tested';
        const patContact = patient ? safePdfText(patient.phone) : 'N/A';

        doc.text(`Patient Name: ${patName}`, 18, 62);
        doc.text(`Patient ID: ${patId}`, 18, 68);
        doc.text(`Age / Gender: ${patAgeGender}`, 18, 74);
        doc.text(`Contact: ${patContact}`, 18, 80);

        doc.text(`Diabetes Type: ${patDiabetes}`, 110, 62);
        doc.text(`Recent HbA1c: ${patHbA1c}`, 110, 68);
        doc.text(`Examined Eye: ${safePdfText(screening.eye)}`, 110, 74);
        doc.text(`Screening Session ID: ${safePdfText(screening.id)}`, 110, 80);

        // 3. AI Screening Findings
        doc.setDrawColor(210, 227, 243);
        doc.setFillColor(255, 255, 255);
        doc.roundedRect(14, 94, pageWidth - 28, 48, 3, 3, 'FD');

        doc.setFont('helvetica', 'bold');
        doc.setFontSize(10);
        doc.setTextColor(20, 45, 78);
        doc.text('DEEP LEARNING MODEL FINDINGS (EfficientNet-B4)', 18, 102);

        doc.setFontSize(13);
        if (screening.grade >= 3) {
            doc.setTextColor(220, 38, 38); // red
        } else if (screening.grade === 1 || screening.grade === 2) {
            doc.setTextColor(217, 119, 6); // amber
        } else {
            doc.setTextColor(22, 167, 121); // green
        }
        doc.text(`Grade ${screening.grade}: ${screening.diagnosis}`, 18, 112);

        doc.setFontSize(9);
        doc.setTextColor(75, 101, 132);
        doc.setFont('helvetica', 'normal');
        doc.text(`Model Confidence Score: ${screening.confidence}%`, 18, 120);
        doc.text(`Clinical Severity Category: ${screening.severity}`, 18, 126);

        // ICDR Recommendation
        doc.setFont('helvetica', 'bold');
        doc.setTextColor(20, 45, 78);
        doc.text('Clinical Recommendation:', 18, 133);
        doc.setFont('helvetica', 'normal');
        doc.setTextColor(75, 101, 132);
        doc.text(screening.recommendation, 65, 133, { maxWidth: pageWidth - 85 });

        // 4. Probability Distribution Table
        doc.setFont('helvetica', 'bold');
        doc.setFontSize(10);
        doc.setTextColor(20, 45, 78);
        doc.text('5-CLASS SOFTMAX PROBABILITY BREAKDOWN', 14, 152);

        let tableY = 158;
        doc.setFillColor(240, 246, 252);
        doc.rect(14, tableY, pageWidth - 28, 7, 'F');
        doc.setFontSize(8);
        doc.setTextColor(75, 101, 132);
        doc.text('DR Severity Class', 18, tableY + 5);
        doc.text('Probability (%)', pageWidth - 50, tableY + 5);

        tableY += 8;
        if (screening.probabilities) {
            Object.entries(screening.probabilities).forEach(([label, prob]) => {
                doc.setFont('helvetica', 'normal');
                doc.text(label, 18, tableY + 4);
                doc.text(`${prob}%`, pageWidth - 50, tableY + 4);
                tableY += 6;
            });
        }

        // 5. Sign-off and Disclaimer
        const footerY = 245;
        doc.setDrawColor(203, 213, 225);
        doc.line(14, footerY, 90, footerY);
        doc.line(pageWidth - 90, footerY, pageWidth - 14, footerY);

        doc.setFontSize(8);
        doc.setTextColor(131, 149, 167);
        doc.text('Certified Screening Operator', 18, footerY + 5);
        doc.text('Reviewing Ophthalmologist / Specialist', pageWidth - 85, footerY + 5);

        // Medical Device Disclaimer
        doc.setFontSize(7);
        doc.setTextColor(131, 149, 167);
        const disclaimer = 'DISCLAIMER: AYN RUYAH is an artificial intelligence-assisted decision support system for diabetic retinopathy detection. It does not replace clinical evaluation by a certified ophthalmologist. All findings, Grad-CAM saliency heatmaps, and severity scores must be clinically validated before initiating treatment.';
        doc.text(disclaimer, 14, 275, { maxWidth: pageWidth - 28 });

        // Save PDF
        const filename = `AYN_RUYAH_Report_${patId}_${screening.id}.pdf`;
        doc.save(filename);
        showNotification(`Report downloaded: ${filename}`, 'success');

    } catch (err) {
        console.error('PDF generation error:', err);
        showNotification('Failed to generate PDF: ' + err.message, 'error');
    }
}
