/**
 * AYN RUYAH — AI Retinal Screening & Explainability Workflow Module
 */

let _imageGeneration = 0;
let _isImageLoading = false;

async function loadScreeningContent(token) {
    const main = document.getElementById('main-viewport');
    if (!main) return;

    if (token === undefined && typeof getNavigationToken === 'function') {
        token = getNavigationToken();
    }
    const currentTenant = State.getActiveTenant();
    if (!currentTenant) return;
    const currentTenantId = currentTenant.id;

    // Ensure patients list is loaded for dropdown
    if (!State.patients || State.patients.length === 0) {
        try {
            const data = await RetinaLensAPI.getPatients({ limit: 100 });
            if (token !== undefined && typeof getNavigationToken === 'function' && token !== getNavigationToken()) return;
            if (State.getActiveTenant()?.id !== currentTenantId) return;
            State.patients = data.patients || [];
        } catch (e) {
            if (token !== undefined && typeof getNavigationToken === 'function' && token !== getNavigationToken()) return;
        }
    }

    const tenant = State.getActiveTenant();
    const selectedPatient = State.selectedPatientForAI || (State.patients.length > 0 ? State.patients[0] : null);

    main.innerHTML = `
        <div class="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-6">
            <div>
                <h2 class="text-xl font-bold tracking-tight text-[#142D4E] flex items-center gap-2.5">
                    <i class="fas fa-eye text-[#087E8B]"></i>
                    AI Retinal Screening Suite
                </h2>
                <p class="text-xs text-[#4B6584] mt-0.5">
                    Workspace: <strong class="text-[#087E8B]">${tenant ? escapeHtml(tenant.name) : ''}</strong> • EfficientNet-B4 5-Class Deep Learning Diagnostic Engine
                </p>
            </div>
            <div class="flex items-center gap-2">
                <span class="text-xs px-3 py-1 rounded-full bg-[#E6FBF2] text-[#0E8558] border border-[#B4F0D4] font-semibold flex items-center gap-2">
                    <span class="w-2 h-2 rounded-full bg-[#10B981] animate-pulse"></span>
                    Model Online • 380×380 Ben Graham Preprocessing
                </span>
            </div>
        </div>

        <div class="grid grid-cols-1 lg:grid-cols-12 gap-6">
            <!-- Left Column: Acquisition & Controls (5 cols) -->
            <div class="lg:col-span-5 space-y-6">
                <!-- Patient & Session Selection Card -->
                <div class="med-card">
                    <h3 class="text-xs uppercase tracking-wider font-bold text-[#142D4E] flex items-center gap-2 mb-4">
                        <i class="fas fa-user-circle text-[#087E8B]"></i> 1. Select Patient & Eye
                    </h3>

                    <div class="space-y-4">
                        <div>
                            <label for="screening-patient-select" class="text-xs font-semibold text-[#142D4E] block mb-1">Registered Patient</label>
                            <select id="screening-patient-select" onchange="onScreeningPatientChange(this.value)" class="form-select text-xs sm:text-sm font-medium w-full">
                            </select>
                        </div>

                        <div id="selected-patient-badge" class="p-3.5 rounded-xl bg-[#F8FBFF] border border-[#E2EEF8] text-xs space-y-1.5">
                            ${renderSelectedPatientMiniCard(selectedPatient)}
                        </div>

                        <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
                            <div>
                                <label for="screening-eye-select" class="text-xs font-semibold text-[#142D4E] block mb-1">Eye Examined</label>
                                <select id="screening-eye-select" class="form-select text-xs w-full">
                                    <option value="Left Eye (OS)">Left Eye (OS)</option>
                                    <option value="Right Eye (OD)">Right Eye (OD)</option>
                                    <option value="Bilateral">Bilateral</option>
                                </select>
                            </div>
                            <div>
                                <label for="screening-notes-input" class="text-xs font-semibold text-[#142D4E] block mb-1">Clinical Notes</label>
                                <input type="text" id="screening-notes-input" placeholder="e.g. Visual haze, floaters" class="form-input text-xs w-full">
                            </div>
                        </div>
                    </div>
                </div>

                <!-- Fundus Image Acquisition Card -->
                <div class="med-card space-y-4">
                    <div class="flex items-center justify-between">
                        <h3 class="text-xs uppercase tracking-wider font-bold text-[#142D4E] flex items-center gap-2">
                            <i class="fas fa-upload text-[#087E8B]"></i> 2. Fundus Image Acquisition
                        </h3>
                        <span class="text-[10px] text-[#8395A7]">JPG, PNG, TIFF</span>
                    </div>

                    <!-- Dropzone -->
                    <div id="screening-drop-zone" class="dropzone-card cursor-pointer focus:outline-none focus:ring-2 focus:ring-[#087E8B] p-4 sm:p-6" tabindex="0" role="button" aria-label="Upload retinal fundus scan" onkeydown="if(event.key==='Enter'||event.key===' '){event.preventDefault(); document.getElementById('screening-file-input').click();}">
                        <input type="file" id="screening-file-input" accept="image/*" class="sr-only" onchange="handleScreeningFileSelect(this)">
                        <div class="dropzone-icon-circle w-12 h-12 sm:w-14 sm:h-14 mb-2 sm:mb-3">
                            <i class="fas fa-cloud-arrow-up text-xl sm:text-2xl"></i>
                        </div>
                        <div class="dropzone-prompt-text text-xs sm:text-sm font-bold text-[#142D4E] mb-1">Click or drag & drop retinal fundus scan</div>
                        <div class="dropzone-subtext text-[10px] sm:text-xs text-[#8395A7]">Automatic quality check for optic disc & macula visualization</div>
                    </div>

                    <!-- Quick Reference Sample Images -->
                    <div>
                        <p class="text-[11px] font-bold text-[#4B6584] uppercase tracking-wider mb-2">Quick Reference Test Samples:</p>
                        <div class="grid grid-cols-1 sm:grid-cols-2 gap-2">
                            <button type="button" onclick="loadSampleImage('grade0_14197_left-600.jpg')" class="p-2.5 rounded-xl bg-[#F8FBFF] hover:bg-[#EAF4FF] border border-[#E2EEF8] hover:border-emerald-300 text-left text-xs flex items-center gap-2.5 transition-all min-w-0">
                                <span class="w-3 h-3 rounded-full bg-emerald-500 shrink-0"></span>
                                <div class="min-w-0">
                                    <p class="font-bold text-[#142D4E] text-xs truncate">Grade 0 Sample</p>
                                    <p class="text-[10px] text-[#8395A7] truncate">Normal Retina</p>
                                </div>
                            </button>
                            <button type="button" onclick="loadSampleImage('grade3_6b128e648646-600-FS.jpg')" class="p-2.5 rounded-xl bg-[#F8FBFF] hover:bg-[#EAF4FF] border border-[#E2EEF8] hover:border-rose-300 text-left text-xs flex items-center gap-2.5 transition-all min-w-0">
                                <span class="w-3 h-3 rounded-full bg-rose-500 shrink-0"></span>
                                <div class="min-w-0">
                                    <p class="font-bold text-[#142D4E] text-xs truncate">Grade 3 Sample</p>
                                    <p class="text-[10px] text-[#8395A7] truncate">Severe NPDR</p>
                                </div>
                            </button>
                        </div>
                    </div>

                    <button id="run-screening-btn" onclick="executeRetinalScreening()" class="btn btn-primary w-full py-3 sm:py-3.5 text-xs sm:text-sm font-bold shadow-teal flex items-center justify-center gap-2">
                        <i class="fas fa-microchip"></i> Execute Deep Learning Screening
                    </button>
                </div>
            </div>

            <!-- Right Column: Visualization & Explainability (7 cols) -->
            <div class="lg:col-span-7 space-y-6">
                <!-- Heatmap & Scan Viewer Card -->
                <div class="med-card">
                    <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-4">
                        <div class="min-w-0">
                            <h3 class="font-bold text-[#142D4E] text-sm sm:text-base flex items-center gap-2">
                                <i class="fas fa-eye text-[#087E8B] shrink-0"></i>
                                <span class="truncate">Visualization & Grad-CAM Saliency</span>
                            </h3>
                            <p class="text-[11px] text-[#8395A7] mt-0.5">High-resolution fundus scan with class activation mapping</p>
                        </div>
                        <div class="grid grid-cols-2 sm:flex sm:items-center gap-2 w-full sm:w-auto shrink-0">
                            <button id="btn-view-overlay" type="button" onclick="setViewMode('overlay')" class="btn btn-primary btn-sm text-[11px] sm:text-xs py-1.5 px-3 flex items-center justify-center gap-1.5 w-full sm:w-auto font-semibold">
                                <i class="fas fa-layer-group"></i> <span>Overlay Mode</span>
                            </button>
                            <button id="btn-view-split" type="button" onclick="setViewMode('split')" class="btn btn-secondary btn-sm text-[11px] sm:text-xs py-1.5 px-3 flex items-center justify-center gap-1.5 w-full sm:w-auto font-semibold">
                                <i class="fas fa-columns"></i> <span>Side-by-Side</span>
                            </button>
                        </div>
                    </div>

                    <!-- Single / Overlay Container -->
                    <div id="viewer-overlay-container" class="relative w-full h-64 sm:h-80 md:h-96 rounded-2xl bg-[#0B1728] border border-[#CBD5E1] overflow-hidden flex items-center justify-center shadow-inner">
                        <!-- Base Fundus Image Layer -->
                        <img id="screening-base-img" class="absolute inset-0 w-full h-full object-contain hidden" alt="Original fundus scan">

                        <!-- Heatmap Overlay Layer -->
                        <img id="screening-preview-img" class="absolute inset-0 w-full h-full object-contain hidden transition-opacity duration-150" alt="Grad-CAM Heatmap" onerror="handleHeatmapLoadError(this)">

                        <!-- Active Mode Indicator Badge -->
                        <div id="viewer-active-badge" class="hidden absolute top-2.5 left-2.5 z-10 text-[10px] font-bold px-2.5 py-1 rounded-full bg-[#142D4E]/85 text-[#38BDF8] border border-[#38BDF8]/30 backdrop-blur-xs flex items-center gap-1.5 shadow-sm">
                            <i class="fas fa-camera"></i> <span id="viewer-active-badge-text">Original Retinal Scan</span>
                        </div>

                        <!-- Quick Heatmap Toggle -->
                        <button id="btn-quick-toggle-gradcam" type="button" onclick="toggleScreeningGradCAM()" class="hidden absolute top-2.5 right-2.5 z-10 text-[10px] font-bold px-2.5 py-1 rounded-full bg-[#142D4E]/85 hover:bg-[#142D4E] text-white border border-white/20 backdrop-blur-xs flex items-center gap-1.5 transition-all shadow-sm">
                            <i class="fas fa-layer-group text-[#38BDF8]"></i> <span id="btn-quick-toggle-text">Hide Heatmap</span>
                        </button>

                        <!-- Clean Clinical Empty State -->
                        <div id="screening-empty-state" class="text-center p-6 sm:p-8 flex flex-col items-center justify-center">
                            <div class="w-14 h-14 sm:w-16 sm:h-16 rounded-2xl bg-[#087E8B]/15 border border-[#087E8B]/30 flex items-center justify-center mb-3 text-[#38BDF8] text-2xl shadow-inner">
                                <i class="fas fa-eye"></i>
                            </div>
                            <p class="text-sm font-bold text-white">No Retinal Scan Loaded</p>
                            <p class="text-xs text-slate-400 mt-1 max-w-xs text-center leading-relaxed">
                                Upload a fundus image or pick a test sample from the left panel to begin AI screening
                            </p>
                        </div>

                        <!-- Scanning Progress Indicator -->
                        <div id="screening-scanning-indicator" class="hidden absolute inset-0 bg-[#0A1C33]/90 backdrop-blur-xs flex flex-col items-center justify-center text-teal-300 z-20 p-4 text-center">
                            <i class="fas fa-circle-notch fa-spin text-4xl mb-3 text-[#38BDF8]"></i>
                            <p class="font-bold text-sm tracking-wide text-white">Running EfficientNet-B4 Forward Pass...</p>
                            <p class="text-xs text-teal-200 mt-1">Extracting features & computing Grad-CAM saliency map</p>
                        </div>
                    </div>

                    <!-- Side-by-Side Split Container (Hidden by default, stacks on mobile) -->
                    <div id="viewer-split-container" class="hidden flex flex-col sm:grid sm:grid-cols-2 gap-3 w-full min-h-[340px] sm:h-80 md:h-96">
                        <!-- Left: Original Scan -->
                        <div class="relative h-56 sm:h-full rounded-2xl bg-[#0B1728] overflow-hidden border border-[#CBD5E1] flex flex-col items-center justify-center shadow-inner">
                            <span class="absolute top-2.5 left-2.5 z-10 text-[9px] sm:text-[10px] uppercase font-bold px-2.5 py-0.5 rounded-full bg-[#142D4E]/85 text-white backdrop-blur-xs border border-white/10 flex items-center gap-1">
                                <i class="fas fa-camera text-[#38BDF8]"></i> Original Scan
                            </span>
                            <img id="split-original-img" class="w-full h-full object-contain" alt="Original fundus scan">
                        </div>

                        <!-- Right: Grad-CAM Heatmap with pending fallback state -->
                        <div id="split-heatmap-pane" class="relative h-56 sm:h-full rounded-2xl bg-[#0B1728] overflow-hidden border border-[#CBD5E1] flex flex-col items-center justify-center shadow-inner">
                            <span id="split-heatmap-badge" class="absolute top-2.5 left-2.5 z-10 text-[9px] sm:text-[10px] uppercase font-bold px-2.5 py-0.5 rounded-full bg-[#087E8B]/90 text-white backdrop-blur-xs flex items-center gap-1">
                                <i class="fas fa-fire"></i> Grad-CAM Heatmap
                            </span>
                            <!-- Actual heatmap image -->
                            <img id="split-heatmap-img" class="w-full h-full object-contain hidden" alt="Grad-CAM Heatmap" onerror="handleHeatmapLoadError(this)">

                            <!-- Clean fallback placeholder when heatmap is pending -->
                            <div id="split-heatmap-placeholder" class="text-center p-4 flex flex-col items-center justify-center">
                                <div class="w-12 h-12 rounded-xl bg-white/5 border border-white/10 flex items-center justify-center mb-2.5 text-slate-400 text-xl">
                                    <i class="fas fa-microchip"></i>
                                </div>
                                <p class="text-xs font-bold text-white">Heatmap Pending</p>
                                <p class="text-[10px] text-slate-400 mt-0.5 max-w-[190px] leading-relaxed">
                                    Execute deep learning screening to generate class-activation Grad-CAM saliency
                                </p>
                            </div>
                        </div>
                    </div>

                    <!-- Opacity Slider -->
                    <div id="gradcam-slider-box" class="hidden mt-3 p-3 rounded-xl bg-[#F8FBFF] border border-[#E2EEF8] flex items-center gap-3">
                        <span class="text-xs font-semibold text-[#142D4E] whitespace-nowrap flex items-center gap-1.5 shrink-0">
                            <i class="fas fa-sliders text-[#087E8B]"></i> Heatmap Opacity:
                        </span>
                        <input type="range" id="gradcam-opacity-range" min="10" max="100" value="85" oninput="updateGradCAMOpacity(this.value)" class="w-full accent-[#087E8B] cursor-pointer" aria-label="Heatmap intensity slider">
                        <span id="gradcam-opacity-val" class="text-xs font-mono font-bold text-[#087E8B] w-10 text-right shrink-0">85%</span>
                    </div>
                </div>

                <!-- AI Diagnostic Findings Panel -->
                <div id="screening-results-box" class="hidden med-card space-y-5 sm:space-y-6">
                    <div class="flex flex-col sm:flex-row sm:items-start justify-between gap-3 border-b border-[#E2EEF8] pb-4">
                        <div>
                            <span class="text-[10px] uppercase font-bold tracking-widest text-[#8395A7]">AI Severity Grading</span>
                            <h3 id="result-diagnosis-title" class="text-xl sm:text-2xl font-black text-[#142D4E] mt-0.5">-</h3>
                            <span id="result-severity-badge" class="badge mt-1">-</span>
                        </div>
                        <div class="text-left sm:text-right">
                            <span class="text-[10px] uppercase font-bold tracking-widest text-[#8395A7]">Confidence</span>
                            <div id="result-confidence-val" class="text-xl sm:text-2xl font-black text-[#087E8B]">-</div>
                            <span class="text-[10px] text-[#8395A7]">Softmax Score</span>
                        </div>
                    </div>

                    <!-- Clinical Recommendation Box -->
                    <div id="result-recommendation-box" class="p-4 rounded-xl border-l-4 bg-[#F8FBFF] space-y-1" style="border-color: #087E8B">
                        <h4 class="text-xs font-bold text-[#142D4E] uppercase tracking-wider flex items-center gap-1.5">
                            <i class="fas fa-stethoscope text-[#087E8B]"></i> International Clinical DR Recommendation
                        </h4>
                        <p id="result-recommendation-text" class="text-xs text-[#4B6584] leading-relaxed font-medium">-</p>
                    </div>

                    <!-- Probability Distribution Bar Chart -->
                    <div>
                        <h4 class="text-xs font-bold text-[#142D4E] uppercase tracking-wider mb-3">
                            Class Probability Distribution (5-Class Softmax)
                        </h4>
                        <div class="h-44 w-full min-w-0">
                            <canvas id="screening-prob-chart"></canvas>
                        </div>
                    </div>

                    <!-- Action Buttons -->
                    <div class="flex flex-col sm:flex-row gap-2.5 pt-2">
                        <button onclick="downloadCurrentScreeningReport()" class="btn btn-primary w-full sm:flex-1 py-3 text-xs shadow-md">
                            <i class="fas fa-file-pdf"></i> Download Ophthalmology Report (PDF)
                        </button>
                        <button onclick="switchNav('reports')" class="btn btn-secondary w-full sm:w-auto py-3 text-xs">
                            <i class="fas fa-list-check text-[#087E8B]"></i> View All Hospital Screenings
                        </button>
                    </div>

                    <!-- Medical Disclaimer -->
                    <div class="p-3.5 rounded-xl border border-rose-200 bg-rose-50 text-[11px] text-rose-800 leading-relaxed">
                        <strong>Medical Device Disclaimer:</strong> AYN RUYAH DR Screening Platform is an ophthalmologist decision support system. All AI findings must be verified by a certified retinal specialist before commencing laser photocoagulation, anti-VEGF therapy, or vitrectomy.
                    </div>
                </div>
            </div>
        </div>
    `;

    // Safely populate patient select using DOM APIs
    const pSelect = document.getElementById('screening-patient-select');
    if (pSelect) {
        pSelect.textContent = '';
        State.patients.forEach(p => {
            const opt = document.createElement('option');
            opt.value = p.id;
            opt.textContent = `${p.first_name} ${p.last_name} (${p.id}) • ${p.age}y ${p.gender}`;
            if (selectedPatient && selectedPatient.id === p.id) {
                opt.selected = true;
            }
            pSelect.appendChild(opt);
        });
    }

    initScreeningDropZone();
}

function renderSelectedPatientMiniCard(p) {
    if (!p) return '<p class="text-[#8395A7] text-xs">No patient selected</p>';
    return `
        <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-1 text-xs">
            <span class="text-[#8395A7] text-[11px]">Selected Patient:</span>
            <span class="font-bold text-[#142D4E] truncate">${escapeHtml(p.first_name)} ${escapeHtml(p.last_name)} <span class="font-mono text-[#8395A7]">(${escapeHtml(p.id)})</span></span>
        </div>
        <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-1 text-xs">
            <span class="text-[#8395A7] text-[11px]">Condition:</span>
            <span class="text-[#087E8B] font-semibold">${escapeHtml(p.diabetes_type)} • ${escapeHtml(p.diabetes_duration_years)} yrs</span>
        </div>
        <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-1 text-xs">
            <span class="text-[#8395A7] text-[11px]">Location:</span>
            <span class="text-[#4B6584]">${escapeHtml(p.city)}, ${escapeHtml(p.state)}</span>
        </div>
    `;
}

function onScreeningPatientChange(patientId) {
    const patient = State.patients.find(p => p.id === patientId);
    if (patient) {
        State.selectedPatientForAI = patient;
        State.currentAIResult = null;
        State.gradcamEnabled = false;

        // Restore original scan in screening viewer and clear heatmap overlay
        const previewImg = document.getElementById('screening-preview-img');
        if (previewImg) {
            previewImg.src = '';
            previewImg.classList.add('hidden');
        }
        const quickToggleBtn = document.getElementById('btn-quick-toggle-gradcam');
        if (quickToggleBtn) quickToggleBtn.classList.add('hidden');

        const activeBadgeText = document.getElementById('viewer-active-badge-text');
        if (activeBadgeText) activeBadgeText.innerHTML = `<i class="fas fa-camera mr-1"></i> Original Retinal Scan`;

        if (!State.currentAIImage) {
            const baseImg = document.getElementById('screening-base-img');
            const emptyState = document.getElementById('screening-empty-state');
            const activeBadge = document.getElementById('viewer-active-badge');
            if (baseImg) {
                baseImg.src = '';
                baseImg.classList.add('hidden');
            }
            if (activeBadge) activeBadge.classList.add('hidden');
            if (emptyState) emptyState.classList.remove('hidden');
        }

        // Clear split heatmap and restore placeholder
        const heatImg = document.getElementById('split-heatmap-img');
        if (heatImg) {
            heatImg.src = '';
            heatImg.classList.add('hidden');
        }
        const splitPlaceholder = document.getElementById('split-heatmap-placeholder');
        if (splitPlaceholder) splitPlaceholder.classList.remove('hidden');

        // Reset Grad-CAM slider
        const opacitySlider = document.getElementById('gradcam-opacity-range');
        if (opacitySlider) opacitySlider.value = 85;
        const opacityVal = document.getElementById('gradcam-opacity-val');
        if (opacityVal) opacityVal.textContent = '85%';

        // Hide findings and slider
        const resultsBox = document.getElementById('screening-results-box');
        if (resultsBox) resultsBox.classList.add('hidden');
        const sliderBox = document.getElementById('gradcam-slider-box');
        if (sliderBox) sliderBox.classList.add('hidden');
        const badge = document.getElementById('selected-patient-badge');
        if (badge) badge.innerHTML = renderSelectedPatientMiniCard(patient);
    }
}

function initScreeningDropZone() {
    const dropZone = document.getElementById('screening-drop-zone');
    const input = document.getElementById('screening-file-input');
    if (!dropZone || !input) return;

    dropZone.onclick = () => input.click();

    ['dragenter', 'dragover'].forEach(name => {
        dropZone.addEventListener(name, (e) => {
            e.preventDefault();
            e.stopPropagation();
            dropZone.classList.add('drag-over');
        });
    });

    ['dragleave', 'drop'].forEach(name => {
        dropZone.addEventListener(name, (e) => {
            e.preventDefault();
            e.stopPropagation();
            dropZone.classList.remove('drag-over');
        });
    });

    dropZone.addEventListener('drop', (e) => {
        const files = e.dataTransfer?.files;
        if (files && files.length > 0) {
            handleScreeningImageFile(files[0]);
        }
    });
}

function handleScreeningFileSelect(input) {
    if (input.files && input.files[0]) {
        handleScreeningImageFile(input.files[0]);
    }
}

function handleScreeningImageFile(file) {
    _imageGeneration++;
    const currentGen = _imageGeneration;
    _isImageLoading = true;

    State.currentAIResult = null;
    const resultsBox = document.getElementById('screening-results-box');
    if (resultsBox) resultsBox.classList.add('hidden');
    const sliderBox = document.getElementById('gradcam-slider-box');
    if (sliderBox) sliderBox.classList.add('hidden');

    const reader = new FileReader();
    reader.onload = (e) => {
        if (_imageGeneration !== currentGen) return;
        _isImageLoading = false;
        State.currentAIImage = e.target.result;
        displayScreeningPreview(State.currentAIImage);
        showNotification('Retinal fundus image loaded', 'info');
    };
    reader.onerror = () => {
        if (_imageGeneration === currentGen) _isImageLoading = false;
        showNotification('Failed to read image file', 'error');
    };
    reader.readAsDataURL(file);
}

async function loadSampleImage(filename) {
    _imageGeneration++;
    const currentGen = _imageGeneration;
    _isImageLoading = true;

    try {
        State.currentAIResult = null;
        const resultsBox = document.getElementById('screening-results-box');
        if (resultsBox) resultsBox.classList.add('hidden');
        const sliderBox = document.getElementById('gradcam-slider-box');
        if (sliderBox) sliderBox.classList.add('hidden');

        const res = await fetch(`/${filename}`);
        if (!res.ok) throw new Error('Sample image not found on server');
        const blob = await res.blob();
        if (_imageGeneration !== currentGen) return;

        const reader = new FileReader();
        reader.onload = (e) => {
            if (_imageGeneration !== currentGen) return;
            _isImageLoading = false;
            State.currentAIImage = e.target.result;
            displayScreeningPreview(State.currentAIImage);
            showNotification(`Loaded sample: ${filename}`, 'info');
        };
        reader.onerror = () => {
            if (_imageGeneration === currentGen) _isImageLoading = false;
            showNotification('Failed to process sample image', 'error');
        };
        reader.readAsDataURL(blob);
    } catch (err) {
        if (_imageGeneration === currentGen) _isImageLoading = false;
        showNotification(err.message, 'error');
    }
}

function displayScreeningPreview(imageSrc) {
    const baseImg = document.getElementById('screening-base-img');
    const empty = document.getElementById('screening-empty-state');
    const activeBadge = document.getElementById('viewer-active-badge');
    const activeBadgeText = document.getElementById('viewer-active-badge-text');
    const previewImg = document.getElementById('screening-preview-img');
    const quickToggleBtn = document.getElementById('btn-quick-toggle-gradcam');

    if (baseImg && empty) {
        baseImg.src = imageSrc;
        baseImg.classList.remove('hidden');
        empty.classList.add('hidden');
    }
    if (activeBadge) activeBadge.classList.remove('hidden');
    if (activeBadgeText) activeBadgeText.innerHTML = `<i class="fas fa-camera mr-1"></i> Original Retinal Scan`;
    if (quickToggleBtn) quickToggleBtn.classList.add('hidden');
    if (previewImg) {
        previewImg.src = '';
        previewImg.classList.add('hidden');
    }

    const splitOrig = document.getElementById('split-original-img');
    if (splitOrig) splitOrig.src = imageSrc;
    const splitHeatmap = document.getElementById('split-heatmap-img');
    const splitPlaceholder = document.getElementById('split-heatmap-placeholder');
    if (splitHeatmap) {
        splitHeatmap.src = '';
        splitHeatmap.classList.add('hidden');
    }
    if (splitPlaceholder) splitPlaceholder.classList.remove('hidden');
}

function setViewMode(mode) {
    const overlayCont = document.getElementById('viewer-overlay-container');
    const splitCont = document.getElementById('viewer-split-container');
    const btnOverlay = document.getElementById('btn-view-overlay');
    const btnSplit = document.getElementById('btn-view-split');

    if (mode === 'split') {
        overlayCont?.classList.add('hidden');
        splitCont?.classList.remove('hidden');
        btnSplit?.classList.add('btn-primary');
        btnSplit?.classList.remove('btn-secondary');
        btnOverlay?.classList.remove('btn-primary');
        btnOverlay?.classList.add('btn-secondary');

        // Populate split images
        const origImg = document.getElementById('split-original-img');
        const heatImg = document.getElementById('split-heatmap-img');
        const splitPlaceholder = document.getElementById('split-heatmap-placeholder');
        if (origImg) origImg.src = State.currentAIImage || '';
        if (State.currentAIResult && State.currentAIResult.heatmap_image_path) {
            if (heatImg) {
                heatImg.src = State.currentAIResult.heatmap_image_path;
                heatImg.classList.remove('hidden');
            }
            if (splitPlaceholder) splitPlaceholder.classList.add('hidden');
        } else {
            if (heatImg) {
                heatImg.src = '';
                heatImg.classList.add('hidden');
            }
            if (splitPlaceholder) splitPlaceholder.classList.remove('hidden');
        }
    } else {
        splitCont?.classList.add('hidden');
        overlayCont?.classList.remove('hidden');
        btnOverlay?.classList.add('btn-primary');
        btnOverlay?.classList.remove('btn-secondary');
        btnSplit?.classList.remove('btn-primary');
        btnSplit?.classList.add('btn-secondary');
    }
}

async function executeRetinalScreening() {
    if (_isImageLoading) {
        showNotification('Please wait until image loading completes.', 'warning');
        return;
    }

    if (!State.currentAIImage) {
        showNotification('Please upload or select a retinal fundus scan first.', 'warning');
        return;
    }

    const patientSelect = document.getElementById('screening-patient-select');
    const patientId = patientSelect ? patientSelect.value : (State.selectedPatientForAI ? State.selectedPatientForAI.id : null);
    if (!patientId) {
        showNotification('Please select a registered patient.', 'warning');
        return;
    }

    const eye = document.getElementById('screening-eye-select')?.value || 'Left Eye (OS)';
    const notes = document.getElementById('screening-notes-input')?.value || '';

    const activeTenantId = State.getActiveTenant()?.id;
    const activeToken = typeof getNavigationToken === 'function' ? getNavigationToken() : null;
    const requestImage = State.currentAIImage;
    const requestPatientId = patientId;
    const requestGeneration = _imageGeneration;

    const indicator = document.getElementById('screening-scanning-indicator');
    const runBtn = document.getElementById('run-screening-btn');

    try {
        indicator?.classList.remove('hidden');
        if (runBtn) {
            runBtn.disabled = true;
            runBtn.innerHTML = '<i class="fas fa-spinner fa-spin mr-2"></i> Analyzing Fundus Scan...';
        }

        // Convert data URL to binary blob
        const res = await fetch(State.currentAIImage);
        const blob = await res.blob();

        // Call backend multi-tenant screening endpoint
        const data = await RetinaLensAPI.executeScreening(patientId, blob, eye, notes);

        // Verify active context and image generation upon response to prevent stale race conditions
        if (_imageGeneration !== requestGeneration) return;
        if (activeToken !== null && typeof getNavigationToken === 'function' && activeToken !== getNavigationToken()) return;
        if (State.getActiveTenant()?.id !== activeTenantId) return;
        if (State.currentAIImage !== requestImage) return;
        const currentPatient = document.getElementById('screening-patient-select')?.value;
        if (currentPatient && currentPatient !== requestPatientId) return;

        State.currentAIResult = data.screening;

        showNotification(`Screening Complete: ${data.screening.diagnosis} (${data.screening.confidence}%)`, 'success');
        renderScreeningResults(data.screening);

    } catch (err) {
        console.error('Screening execution error:', err);
        showNotification(err.message || 'Screening failed', 'error');
    } finally {
        indicator?.classList.add('hidden');
        if (runBtn) {
            runBtn.disabled = false;
            runBtn.innerHTML = '<i class="fas fa-microchip mr-2"></i> Execute Deep Learning Screening';
        }
    }
}

function renderScreeningResults(screening) {
    const resultsBox = document.getElementById('screening-results-box');
    const sliderBox = document.getElementById('gradcam-slider-box');
    if (!resultsBox) return;

    resultsBox.classList.remove('hidden');
    sliderBox?.classList.remove('hidden');

    const gradeInfo = DR_GRADES[screening.grade] || DR_GRADES[0];

    document.getElementById('result-diagnosis-title').textContent = screening.diagnosis;
    const badge = document.getElementById('result-severity-badge');
    badge.textContent = `Grade ${screening.grade} — ${screening.severity}`;
    badge.className = `badge ${gradeInfo.badge} font-bold text-xs`;

    document.getElementById('result-confidence-val').textContent = `${parseFloat(screening.confidence || 0).toFixed(1)}%`;
    document.getElementById('result-recommendation-text').textContent = screening.recommendation;
    document.getElementById('result-recommendation-box').style.borderColor = gradeInfo.color;

    // Dual-layer overlay setup
    const baseImg = document.getElementById('screening-base-img');
    const previewImg = document.getElementById('screening-preview-img');
    const activeBadge = document.getElementById('viewer-active-badge');
    const activeBadgeText = document.getElementById('viewer-active-badge-text');
    const quickToggleBtn = document.getElementById('btn-quick-toggle-gradcam');
    const quickToggleText = document.getElementById('btn-quick-toggle-text');

    if (baseImg && (State.currentAIImage || screening.original_image_path)) {
        baseImg.src = State.currentAIImage || screening.original_image_path;
        baseImg.classList.remove('hidden');
    }

    if (screening.heatmap_image_path) {
        State.gradcamEnabled = true;
        if (previewImg) {
            previewImg.src = screening.heatmap_image_path;
            const currentOpacity = document.getElementById('gradcam-opacity-range')?.value || 85;
            previewImg.style.opacity = currentOpacity / 100;
            previewImg.classList.remove('hidden');
        }
        if (activeBadge) activeBadge.classList.remove('hidden');
        if (activeBadgeText) activeBadgeText.innerHTML = `<i class="fas fa-fire mr-1 text-[#EF6461]"></i> Grad-CAM Heatmap Overlay`;
        if (quickToggleBtn) quickToggleBtn.classList.remove('hidden');
        if (quickToggleText) quickToggleText.textContent = 'Hide Heatmap';
    }

    // Populate split view
    const origImg = document.getElementById('split-original-img');
    const heatImg = document.getElementById('split-heatmap-img');
    const splitPlaceholder = document.getElementById('split-heatmap-placeholder');
    if (origImg) origImg.src = State.currentAIImage || screening.original_image_path || '';
    if (screening.heatmap_image_path && heatImg) {
        heatImg.src = screening.heatmap_image_path;
        heatImg.classList.remove('hidden');
        if (splitPlaceholder) splitPlaceholder.classList.add('hidden');
    }

    // Render probability chart
    renderProbabilityBarChart(screening.probabilities);
}

function renderProbabilityBarChart(probabilities) {
    const canvas = document.getElementById('screening-prob-chart');
    if (!canvas) return;

    const existing = Chart.getChart(canvas);
    if (existing) existing.destroy();

    const labels = Object.keys(probabilities);
    const dataVals = Object.values(probabilities);
    const colors = ['#16A779', '#2563EB', '#D97706', '#EA580C', '#DC2626'];

    new Chart(canvas, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                label: 'Softmax Probability (%)',
                data: dataVals,
                backgroundColor: colors,
                borderRadius: 6,
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false },
                tooltip: {
                    backgroundColor: '#142D4E',
                    callbacks: {
                        label: (ctx) => `${ctx.raw}% confidence`
                    }
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    max: 100,
                    ticks: { color: '#8395A7', font: { family: 'Plus Jakarta Sans', size: 10 } },
                    grid: { color: '#E2EEF8' }
                },
                x: {
                    ticks: { color: '#142D4E', font: { family: 'Plus Jakarta Sans', size: 10, weight: '600' } },
                    grid: { display: false }
                }
            }
        }
    });
}

function toggleScreeningGradCAM() {
    if (!State.currentAIResult || !State.currentAIResult.heatmap_image_path) return;
    State.gradcamEnabled = !State.gradcamEnabled;

    const previewImg = document.getElementById('screening-preview-img');
    const activeBadgeText = document.getElementById('viewer-active-badge-text');
    const quickToggleText = document.getElementById('btn-quick-toggle-text');

    if (State.gradcamEnabled) {
        if (previewImg) {
            const currentOpacity = document.getElementById('gradcam-opacity-range')?.value || 85;
            previewImg.style.opacity = currentOpacity / 100;
            previewImg.classList.remove('hidden');
        }
        if (activeBadgeText) activeBadgeText.innerHTML = `<i class="fas fa-fire mr-1 text-[#EF6461]"></i> Grad-CAM Heatmap Overlay`;
        if (quickToggleText) quickToggleText.textContent = 'Hide Heatmap';
    } else {
        if (previewImg) previewImg.classList.add('hidden');
        if (activeBadgeText) activeBadgeText.innerHTML = `<i class="fas fa-camera mr-1"></i> Original Retinal Scan`;
        if (quickToggleText) quickToggleText.textContent = 'Show Heatmap';
    }
}

function updateGradCAMOpacity(val) {
    const label = document.getElementById('gradcam-opacity-val');
    if (label) label.textContent = `${val}%`;
    const previewImg = document.getElementById('screening-preview-img');
    if (previewImg) {
        previewImg.style.opacity = val / 100;
        if (val > 0 && State.gradcamEnabled) {
            previewImg.classList.remove('hidden');
        }
    }
}

function handleHeatmapLoadError(imgEl) {
    console.warn('Heatmap image failed to load:', imgEl?.src);
    if (imgEl) imgEl.classList.add('hidden');
    if (imgEl?.id === 'split-heatmap-img') {
        const placeholder = document.getElementById('split-heatmap-placeholder');
        if (placeholder) placeholder.classList.remove('hidden');
    }
    const quickToggleBtn = document.getElementById('btn-quick-toggle-gradcam');
    if (quickToggleBtn) quickToggleBtn.classList.add('hidden');
}

function downloadCurrentScreeningReport() {
    if (!State.currentAIResult) {
        showNotification('No screening result available to export', 'warning');
        return;
    }
    const patient = State.patients.find(p => p.id === State.currentAIResult.patient_id) || State.selectedPatientForAI;
    generateClinicalReportPDF(State.currentAIResult, patient, State.getActiveTenant(), State.getActiveUser());
}
