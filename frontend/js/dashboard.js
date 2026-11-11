/**
 * AYN RUYAH — Hospital Screening Dashboard Module
 */

async function loadDashboardContent(token) {
    if (token === undefined) {
        token = getNavigationToken();
    }
    const main = document.getElementById('main-viewport');
    if (!main) return;

    main.innerHTML = `
        <div class="flex items-center justify-center p-16">
            <div class="flex flex-col items-center gap-3">
                <i class="fas fa-spinner fa-spin text-3xl text-[#087E8B]"></i>
                <p class="text-xs font-semibold text-[#4B6584]">Loading Clinical Dashboard...</p>
            </div>
        </div>
    `;

    try {
        const stats = await RetinaLensAPI.getAnalytics();
        if (token !== undefined && token !== getNavigationToken()) return;
        State.analytics = stats;

        // Fetch recent screenings for the clinical stream
        const screeningsData = await RetinaLensAPI.getScreenings({ limit: 6 });
        if (token !== undefined && token !== getNavigationToken()) return;
        const recentScreenings = screeningsData.screenings || [];

        const tenant = State.getActiveTenant();

        main.innerHTML = `
            <!-- ==================== 1. DASHBOARD HERO BANNER ==================== -->
            <div class="hero-banner-card">
                <div class="hero-content">
                    <span class="hero-badge-tag">
                        <i class="fas fa-microscope"></i> AI-POWERED OPHTHALMOLOGY
                    </span>
                    <h1 class="hero-title">
                        AI-Powered Diabetic <span class="teal-text">Retinopathy</span> Screening
                    </h1>
                    <p class="hero-description">
                        Automated 5-grade ICDR retinal analysis powered by fine-tuned EfficientNet-B4 architecture and Grad-CAM lesion localization for tertiary and primary healthcare clinics.
                    </p>
                    <div class="hero-actions">
                        <button onclick="switchNav('screening')" class="btn btn-primary">
                            <i class="fas fa-eye"></i> Start New Screening
                        </button>
                        <button onclick="openModal('register-patient-modal')" class="btn btn-secondary">
                            <i class="fas fa-user-plus"></i> Register Patient
                        </button>
                    </div>
                    <div class="hero-features">
                        <span class="hero-feature-item">
                            <i class="fas fa-check-circle text-[#087E8B]"></i> 5-Grade DR Detection
                        </span>
                        <span class="hero-feature-item">
                            <i class="fas fa-eye text-[#087E8B]"></i> Grad-CAM Visualization
                        </span>
                        <span class="hero-feature-item">
                            <i class="fas fa-file-medical-alt text-[#087E8B]"></i> Clinical Reports
                        </span>
                    </div>
                </div>

                <div class="hero-image-frame">
                    <div class="hero-photo-wrap">
                        <img src="/assets/hero_ophthalmologist.jpg" alt="Ophthalmologist examining patient with retinal fundus scan" class="hero-photo">
                        <div class="hero-floating-badge">
                            <div class="floating-badge-icon">
                                <i class="fas fa-brain"></i>
                            </div>
                            <div>
                                <div class="floating-badge-text">EfficientNet-B4 Core</div>
                                <div class="floating-badge-sub">Fine-Tuned DR Model</div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Page Header Meta Bar -->
            <div class="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-6">
                <div>
                    <h2 class="text-xl font-bold tracking-tight text-[#142D4E] flex items-center gap-2.5">
                        <i class="fas fa-chart-line text-[#087E8B]"></i>
                        Clinical Epidemiology & Screening Performance
                    </h2>
                    <p class="text-xs text-[#4B6584] mt-0.5">
                        Active Workspace: <strong class="text-[#087E8B]">${tenant ? tenant.name : ''}</strong> • ${tenant ? tenant.city : ''}, ${tenant ? tenant.state : ''}
                    </p>
                </div>
                <div class="flex items-center gap-2">
                    <span class="text-xs font-semibold px-3 py-1 rounded-full bg-[#E6F6F7] text-[#087E8B] border border-teal-200">
                        <i class="fas fa-sync-alt mr-1"></i> Live Real-Time Feed
                    </span>
                </div>
            </div>

            <!-- ==================== 2. KPI METRIC CARDS ==================== -->
            <div class="stats-grid-4 mb-8">
                <!-- Total Screenings -->
                <div class="kpi-card">
                    <div class="kpi-icon-wrap kpi-icon-teal">
                        <i class="fas fa-camera-retro text-xl"></i>
                    </div>
                    <div class="kpi-data">
                        <div class="kpi-label">Total Screenings</div>
                        <div class="kpi-value text-[#142D4E]">${stats.total_screenings}</div>
                        <div class="kpi-subtext text-emerald-600 font-medium">
                            <i class="fas fa-check-circle mr-1"></i> AI Evaluated Across Cohort
                        </div>
                    </div>
                </div>

                <!-- DR Positivity Rate -->
                <div class="kpi-card">
                    <div class="kpi-icon-wrap kpi-icon-amber">
                        <i class="fas fa-percent text-xl"></i>
                    </div>
                    <div class="kpi-data">
                        <div class="kpi-label">Positivity Rate</div>
                        <div class="kpi-value text-amber-600">${stats.positivity_rate}%</div>
                        <div class="kpi-subtext text-[#8395A7]">
                            ${stats.positive_count} of ${stats.total_screenings} with Grade ≥ 1 signs
                        </div>
                    </div>
                </div>

                <!-- Urgent Referrals -->
                <div class="kpi-card">
                    <div class="kpi-icon-wrap kpi-icon-red">
                        <i class="fas fa-triangle-exclamation text-xl"></i>
                    </div>
                    <div class="kpi-data">
                        <div class="kpi-label">Urgent Referrals</div>
                        <div class="kpi-value text-rose-600">${stats.urgent_count}</div>
                        <div class="kpi-subtext text-rose-500 font-medium">
                            Severe (G3) & Proliferative (G4)
                        </div>
                    </div>
                </div>

                <!-- Registered Patients -->
                <div class="kpi-card">
                    <div class="kpi-icon-wrap kpi-icon-blue">
                        <i class="fas fa-users text-xl"></i>
                    </div>
                    <div class="kpi-data">
                        <div class="kpi-label">Diabetic Cohort</div>
                        <div class="kpi-value text-blue-600">${stats.total_patients}</div>
                        <div class="kpi-subtext text-[#8395A7]">
                            Registered Indian patients
                        </div>
                    </div>
                </div>
            </div>

            <!-- ==================== 3. TWO-COLUMN WORKSPACE GRID ==================== -->
            <div class="dashboard-main-grid mb-8">
                <!-- Left Column (2fr): Priority Referrals Queue & Screening Trends -->
                <div class="space-y-6">
                    <!-- Priority Ophthalmology Referrals -->
                    <div class="med-card">
                        <div class="card-header-flex">
                            <div>
                                <h3 class="card-title flex items-center gap-2">
                                    <i class="fas fa-bell text-rose-500"></i>
                                    Priority Ophthalmology Referrals
                                </h3>
                                <p class="card-subtitle">Immediate intervention recommended for severe and proliferative retinopathy</p>
                            </div>
                            <span class="text-xs font-bold px-2.5 py-1 rounded-full bg-rose-100 text-rose-700 border border-rose-200">
                                ${stats.urgent_cases ? stats.urgent_cases.length : 0} Critical Pending
                            </span>
                        </div>

                        <div class="space-y-2.5">
                            ${(stats.urgent_cases && stats.urgent_cases.length > 0) ? stats.urgent_cases.map(c => `
                                <div class="p-3.5 rounded-xl bg-white border border-rose-200 hover:border-rose-400 hover:shadow-xs transition-all flex items-center justify-between">
                                    <div class="flex items-center gap-3.5">
                                        <div class="w-10 h-10 rounded-xl bg-rose-50 text-rose-600 font-extrabold text-sm flex items-center justify-center border border-rose-200 shrink-0">
                                            G${c.grade}
                                        </div>
                                        <div>
                                            <h4 class="font-bold text-sm text-[#142D4E]">${escapeHtml(c.patient_name)}</h4>
                                            <p class="text-xs text-[#4B6584]">${escapeHtml(c.age)} yrs • ID: <span class="font-mono">${escapeHtml(c.patient_id)}</span> • Tel: ${escapeHtml(c.phone)}</p>
                                        </div>
                                    </div>
                                    <div class="text-right">
                                        <span class="badge ${c.grade === 4 ? 'badge-dr-4' : 'badge-dr-3'} font-bold">
                                            <span class="badge-dot"></span>
                                            ${escapeHtml(c.diagnosis)}
                                        </span>
                                        <p class="text-[11px] text-[#8395A7] mt-1">${new Date(c.date).toLocaleDateString()}</p>
                                    </div>
                                </div>
                            `).join('') : '<p class="text-sm text-[#8395A7] text-center py-8">No urgent referrals currently pending.</p>'}
                        </div>
                    </div>

                    <!-- Screening Trends Chart -->
                    <div class="med-card">
                        <div class="card-header-flex">
                            <div>
                                <h3 class="card-title flex items-center gap-2">
                                    <i class="fas fa-chart-area text-[#087E8B]"></i>
                                    Screening Trends & AI Grading Volume
                                </h3>
                                <p class="card-subtitle">Monthly distribution of normal vs. positive DR screening volume</p>
                            </div>
                        </div>
                        <div class="chart-container-card">
                            <canvas id="dashboard-trend-chart"></canvas>
                        </div>
                    </div>
                </div>

                <!-- Right Column (1fr): Severity Donut, Recent Screenings, Facility Info -->
                <div class="space-y-6">
                    <!-- DR Severity Distribution Donut -->
                    <div class="med-card">
                        <div class="card-header-flex">
                            <div>
                                <h3 class="card-title flex items-center gap-2 text-sm">
                                    <i class="fas fa-chart-pie text-[#087E8B]"></i>
                                    DR Severity Distribution
                                </h3>
                                <p class="card-subtitle">5-Grade ICDR Breakdown</p>
                            </div>
                        </div>
                        <div class="h-44 relative flex items-center justify-center">
                            <canvas id="dashboard-severity-donut"></canvas>
                        </div>
                        <div class="grid grid-cols-5 gap-1.5 mt-3 text-center text-[10px]">
                            ${stats.severity_distribution.map(d => `
                                <div class="p-1 rounded-lg bg-[#F8FBFF] border border-[#E2EEF8]">
                                    <span class="text-[#8395A7] font-semibold block">G${d.grade}</span>
                                    <strong class="text-[#142D4E] block">${d.count}</strong>
                                </div>
                            `).join('')}
                        </div>
                    </div>

                    <!-- Recent Screenings Feed -->
                    <div class="med-card">
                        <div class="card-header-flex">
                            <div>
                                <h3 class="card-title flex items-center gap-2 text-sm">
                                    <i class="fas fa-history text-[#087E8B]"></i>
                                    Recent Screenings
                                </h3>
                                <p class="card-subtitle">Latest AI evaluation stream</p>
                            </div>
                            <button onclick="switchNav('reports')" class="view-all-link text-[#087E8B] hover:text-[#066671]">
                                View All <i class="fas fa-arrow-right text-xs"></i>
                            </button>
                        </div>

                        <div class="space-y-2.5">
                            ${recentScreenings.map(s => {
                                const badgeClass = `badge-dr-${s.grade}`;
                                return `
                                    <div class="p-2.5 rounded-xl bg-[#F8FBFF] border border-[#E2EEF8] hover:border-[#D0E3F3] transition-all flex items-center justify-between">
                                        <div class="flex items-center gap-2.5">
                                            <img src="${s.heatmap_image_path || s.original_image_path || s.image_path || '/sample_images/grade0_14197_left-600.jpg'}" class="w-9 h-9 rounded-lg object-cover bg-black border border-slate-200 shrink-0" onerror="this.src='/sample_images/grade0_14197_left-600.jpg'" alt="Screening thumb">
                                            <div>
                                                <h4 class="font-bold text-xs text-[#142D4E] truncate max-w-[120px]">${escapeHtml(s.patient_name || s.patient_id)}</h4>
                                                <span class="badge ${badgeClass} text-[9px] mt-0.5">
                                                    Grade ${s.grade} • ${parseFloat(s.confidence || 0).toFixed(1)}%
                                                </span>
                                            </div>
                                        </div>
                                        <div class="text-right">
                                            <p class="text-[9px] text-[#8395A7]">${new Date(s.timestamp || s.created_at || Date.now()).toLocaleDateString()}</p>
                                            <button onclick="viewScreeningReportDetails('${s.id}')" class="text-[10px] font-semibold text-[#087E8B] hover:underline block mt-0.5">
                                                Report
                                            </button>
                                        </div>
                                    </div>
                                `;
                            }).join('')}
                            ${recentScreenings.length === 0 ? '<p class="text-xs text-[#8395A7] text-center py-6">No screenings recorded yet.</p>' : ''}
                        </div>
                    </div>

                    <!-- Facility Summary Card -->
                    <div class="med-card bg-gradient-to-br from-white to-[#F0F8FF]">
                        <h4 class="text-xs font-bold uppercase tracking-wider text-[#087E8B] mb-2 flex items-center gap-2">
                            <i class="fas fa-shield-alt"></i> Quality & Compliance
                        </h4>
                        <p class="text-xs text-[#4B6584] leading-relaxed">
                            AYN RUYAH ensures 100% tenant-isolated data partitions with AES-256 encrypted fundus archives. Complies with international clinical diabetic retinopathy grading standards.
                        </p>
                        <div class="mt-4 pt-3 border-t border-[#E2EEF8] flex items-center justify-between text-[11px]">
                            <span class="text-[#8395A7]">Ophthalmic Core:</span>
                            <span class="font-bold text-[#142D4E]">ICDR 2003 / NHS England</span>
                        </div>
                    </div>
                </div>
            </div>
        `;

        // Render Screening Trends Chart & Severity Donut
        initDashboardCharts(stats);

    } catch (err) {
        if (token !== undefined && token !== getNavigationToken()) return;
        console.error('Error loading dashboard:', err);
        main.innerHTML = `
            <div class="p-8 text-center text-rose-600 bg-white rounded-2xl border border-rose-200">
                <i class="fas fa-triangle-exclamation text-3xl mb-2"></i>
                <p class="font-bold">Failed to load dashboard data</p>
                <p class="text-xs text-[#4B6584] mt-1">${err.message}</p>
                <button onclick="loadDashboardContent()" class="btn btn-primary mt-4 text-xs">
                    Retry Loading
                </button>
            </div>
        `;
    }
}

function initDashboardCharts(stats) {
    // 1. Trends Bar Chart
    const trendCtx = document.getElementById('dashboard-trend-chart');
    if (trendCtx) {
        const trends = Array.isArray(stats.monthly_trends) ? stats.monthly_trends : (Array.isArray(stats.screening_trends) ? stats.screening_trends : []);
        const labels = trends.map(t => t.month);
        const totalData = trends.map(t => t.total);
        const positiveData = trends.map(t => t.positive);

        new Chart(trendCtx, {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [
                    {
                        label: 'Total Fundus Screenings',
                        data: totalData,
                        backgroundColor: 'rgba(8, 126, 139, 0.25)',
                        borderColor: '#087E8B',
                        borderWidth: 2,
                        borderRadius: 6,
                    },
                    {
                        label: 'DR Positive Cases (Grade ≥ 1)',
                        data: positiveData,
                        backgroundColor: 'rgba(217, 119, 6, 0.35)',
                        borderColor: '#D97706',
                        borderWidth: 2,
                        borderRadius: 6,
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'top',
                        labels: {
                            boxWidth: 12,
                            font: { family: 'Plus Jakarta Sans', size: 11, weight: '600' },
                            color: '#142D4E'
                        }
                    },
                    tooltip: {
                        backgroundColor: '#142D4E',
                        titleFont: { family: 'Plus Jakarta Sans', size: 12 },
                        bodyFont: { family: 'Plus Jakarta Sans', size: 11 },
                        padding: 10,
                        cornerRadius: 8
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        grid: { color: '#E2EEF8' },
                        ticks: { color: '#8395A7', font: { family: 'Plus Jakarta Sans', size: 10 } }
                    },
                    x: {
                        grid: { display: false },
                        ticks: { color: '#8395A7', font: { family: 'Plus Jakarta Sans', size: 10 } }
                    }
                }
            }
        });
    }

    // 2. Severity Donut
    const donutCtx = document.getElementById('dashboard-severity-donut');
    if (donutCtx && stats.severity_distribution) {
        const labels = stats.severity_distribution.map(d => `G${d.grade}`);
        const dataVals = stats.severity_distribution.map(d => d.count);
        const colors = ['#16A779', '#2563EB', '#D97706', '#EA580C', '#DC2626'];

        new Chart(donutCtx, {
            type: 'doughnut',
            data: {
                labels: labels,
                datasets: [{
                    data: dataVals,
                    backgroundColor: colors,
                    borderWidth: 2,
                    borderColor: '#FFFFFF'
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'right',
                        labels: {
                            boxWidth: 10,
                            font: { family: 'Plus Jakarta Sans', size: 10, weight: '600' },
                            color: '#142D4E',
                            padding: 6
                        }
                    },
                    tooltip: {
                        backgroundColor: '#142D4E'
                    }
                },
                cutout: '65%'
            }
        });
    }
}
