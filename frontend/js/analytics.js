/**
 * AYN RUYAH — Hospital Screening Analytics & DR Epidemiology Module
 */

async function loadAnalyticsContent(token) {
    if (token === undefined) {
        token = getNavigationToken();
    }
    const main = document.getElementById('main-viewport');
    if (!main) return;

    main.innerHTML = `
        <div class="flex items-center justify-center p-16">
            <div class="flex flex-col items-center gap-3">
                <i class="fas fa-spinner fa-spin text-3xl text-[#087E8B]"></i>
                <p class="text-xs font-semibold text-[#4B6584]">Loading Clinical Epidemiology Analytics...</p>
            </div>
        </div>
    `;

    try {
        const stats = await RetinaLensAPI.getAnalytics();
        if (token !== getNavigationToken()) return;
        State.analytics = stats;
        const tenant = State.getActiveTenant();

        main.innerHTML = `
            <div class="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-6">
                <div>
                    <h2 class="text-xl font-bold tracking-tight text-[#142D4E] flex items-center gap-2.5">
                        <i class="fas fa-chart-pie text-[#087E8B]"></i>
                        Hospital Clinical Analytics & DR Epidemiology
                    </h2>
                    <p class="text-xs text-[#4B6584] mt-0.5">
                        Screening Cohort: <strong class="text-[#087E8B]">${tenant ? escapeHtml(tenant.name) : ''}</strong> • ${stats.total_screenings} Evaluated Fundus Exams
                    </p>
                </div>
                <button onclick="loadAnalyticsContent()" class="btn btn-secondary self-start md:self-auto text-xs font-semibold">
                    <i class="fas fa-rotate text-[#087E8B]"></i> Refresh Metrics
                </button>
            </div>

            <!-- Analytics Key Indicators -->
            <div class="stats-grid-4 mb-8">
                <div class="kpi-card">
                    <div class="kpi-icon-wrap kpi-icon-amber">
                        <i class="fas fa-percent text-xl"></i>
                    </div>
                    <div class="kpi-data">
                        <div class="kpi-label">Screening Positivity</div>
                        <div class="kpi-value text-amber-600">${stats.positivity_rate}%</div>
                        <div class="kpi-subtext text-[#8395A7]">${stats.positive_count} with detected DR features</div>
                    </div>
                </div>

                <div class="kpi-card">
                    <div class="kpi-icon-wrap kpi-icon-red">
                        <i class="fas fa-triangle-exclamation text-xl"></i>
                    </div>
                    <div class="kpi-data">
                        <div class="kpi-label">Urgent Intervention</div>
                        <div class="kpi-value text-rose-600">${stats.urgent_rate}%</div>
                        <div class="kpi-subtext text-rose-500 font-medium">${stats.urgent_count} Severe or Proliferative cases</div>
                    </div>
                </div>

                <div class="kpi-card">
                    <div class="kpi-icon-wrap kpi-icon-teal">
                        <i class="fas fa-check-double text-xl"></i>
                    </div>
                    <div class="kpi-data">
                        <div class="kpi-label">Normal Fundus (No DR)</div>
                        <div class="kpi-value text-emerald-600">
                            ${stats.severity_distribution[0] ? stats.severity_distribution[0].percentage : 0}%
                        </div>
                        <div class="kpi-subtext text-[#8395A7]">${stats.severity_distribution[0] ? stats.severity_distribution[0].count : 0} negative screenings</div>
                    </div>
                </div>

                <div class="kpi-card">
                    <div class="kpi-icon-wrap kpi-icon-blue">
                        <i class="fas fa-users text-xl"></i>
                    </div>
                    <div class="kpi-data">
                        <div class="kpi-label">Cohort Coverage</div>
                        <div class="kpi-value text-blue-600">${stats.total_patients}</div>
                        <div class="kpi-subtext text-[#8395A7]">Total registered diabetic patients</div>
                    </div>
                </div>
            </div>

            <!-- Charts Grid: DR Stage Distribution & Monthly Screening Trend -->
            <div class="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
                <!-- Severity Doughnut Chart -->
                <div class="med-card">
                    <h3 class="card-title flex items-center gap-2 mb-1">
                        <i class="fas fa-chart-pie text-[#087E8B]"></i> DR Stage Distribution (ICDR Scale)
                    </h3>
                    <p class="card-subtitle mb-4">Categorization of examined retinas across Grades 0 through 4</p>
                    <div class="h-64 relative flex items-center justify-center">
                        <canvas id="analytics-stage-chart"></canvas>
                    </div>
                    <div class="grid grid-cols-5 gap-2 mt-4 text-center text-xs">
                        ${stats.severity_distribution.map(d => `
                            <div class="p-2 rounded-xl bg-[#F8FBFF] border border-[#E2EEF8]">
                                <p class="text-[#8395A7] font-semibold text-[10px]">G${d.grade}</p>
                                <p class="font-extrabold text-[#142D4E] text-sm">${d.count}</p>
                                <p class="text-[#087E8B] font-bold text-[10px]">${d.percentage}%</p>
                            </div>
                        `).join('')}
                    </div>
                </div>

                <!-- Monthly Screening Volume Line Chart -->
                <div class="med-card">
                    <h3 class="card-title flex items-center gap-2 mb-1">
                        <i class="fas fa-chart-line text-[#087E8B]"></i> Screening Volumes & Positivity Trends
                    </h3>
                    <p class="card-subtitle mb-4">Chronological screening activity and positive detection rate</p>
                    <div class="h-72 relative">
                        <canvas id="analytics-trend-chart"></canvas>
                    </div>
                </div>
            </div>
        `;

        setTimeout(() => {
            renderAnalyticsCharts(stats);
        }, 50);

    } catch (err) {
        if (token !== getNavigationToken()) return;
        showNotification(err.message, 'error');
    }
}

function renderAnalyticsCharts(stats) {
    // 1. Stage Distribution Doughnut
    const stageCanvas = document.getElementById('analytics-stage-chart');
    if (stageCanvas) {
        const existingStage = Chart.getChart(stageCanvas);
        if (existingStage) existingStage.destroy();

        const labels = stats.severity_distribution.map(d => `${d.label} (${d.count})`);
        const dataVals = stats.severity_distribution.map(d => d.count);
        const colors = ['#16A779', '#2563EB', '#D97706', '#EA580C', '#DC2626'];

        new Chart(stageCanvas, {
            type: 'doughnut',
            data: {
                labels: labels,
                datasets: [{
                    data: dataVals,
                    backgroundColor: colors,
                    borderWidth: 2,
                    borderColor: '#FFFFFF',
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'right',
                        labels: {
                            color: '#142D4E',
                            font: { family: 'Plus Jakarta Sans', size: 11, weight: '600' },
                            padding: 10
                        }
                    },
                    tooltip: {
                        backgroundColor: '#142D4E',
                        titleFont: { family: 'Plus Jakarta Sans' },
                        bodyFont: { family: 'Plus Jakarta Sans' }
                    }
                },
                cutout: '65%'
            }
        });
    }

    // 2. Trend Line Chart
    const trendCanvas = document.getElementById('analytics-trend-chart');
    if (trendCanvas) {
        const existingTrend = Chart.getChart(trendCanvas);
        if (existingTrend) existingTrend.destroy();

        const trends = Array.isArray(stats.monthly_trends) ? stats.monthly_trends : [];
        const trendLabels = trends.map(t => t.month);
        const totalScreenings = trends.map(t => t.total);
        const positiveScreenings = trends.map(t => t.positive);

        new Chart(trendCanvas, {
            type: 'line',
            data: {
                labels: trendLabels,
                datasets: [
                    {
                        label: 'Total Screenings',
                        data: totalScreenings,
                        borderColor: '#087E8B',
                        backgroundColor: 'rgba(8, 126, 139, 0.08)',
                        fill: true,
                        tension: 0.35,
                        pointBackgroundColor: '#087E8B',
                        pointRadius: 4,
                    },
                    {
                        label: 'Positive DR Detected',
                        data: positiveScreenings,
                        borderColor: '#EA580C',
                        backgroundColor: 'transparent',
                        borderDash: [5, 5],
                        tension: 0.35,
                        pointBackgroundColor: '#EA580C',
                        pointRadius: 4,
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
                            color: '#142D4E',
                            font: { family: 'Plus Jakarta Sans', size: 11, weight: '600' }
                        }
                    },
                    tooltip: {
                        backgroundColor: '#142D4E'
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        ticks: { color: '#8395A7', font: { family: 'Plus Jakarta Sans', size: 10 } },
                        grid: { color: '#E2EEF8' }
                    },
                    x: {
                        ticks: { color: '#8395A7', font: { family: 'Plus Jakarta Sans', size: 10 } },
                        grid: { color: '#E2EEF8' }
                    }
                }
            }
        });
    }
}
