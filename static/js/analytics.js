/**
 * Analytics Page JavaScript
 * Handles advanced filtering, charting, and data export
 */

// =========================================
// INITIALIZATION
// =========================================

document.addEventListener('DOMContentLoaded', function() {
    initializeAnalyticsPage();
    initializeFilters();
    loadAnalyticsData();
    setupCharts();
});

// =========================================
// PAGE INITIALIZATION
// =========================================

function initializeAnalyticsPage() {
    const apiKey = localStorage.getItem('substacker_api_key');
    if (!apiKey) {
        window.location.href = '/analyzer';
    }

    setupDateRangePicker();
    setupExportButtons();
    setupWebSocketUpdates();
}

function setupDateRangePicker() {
    const startDateInput = document.getElementById('start-date');
    const endDateInput = document.getElementById('end-date');

    if (startDateInput && endDateInput) {
        const today = new Date();
        const thirtyDaysAgo = new Date(today.getTime() - 30 * 24 * 60 * 60 * 1000);

        startDateInput.value = thirtyDaysAgo.toISOString().split('T')[0];
        endDateInput.value = today.toISOString().split('T')[0];

        startDateInput.addEventListener('change', () => applyFilters());
        endDateInput.addEventListener('change', () => applyFilters());
    }
}

// =========================================
// FILTERS
// =========================================

function initializeFilters() {
    const teamFilter = document.getElementById('team-filter');
    const providerFilter = document.getElementById('provider-filter');
    const modelFilter = document.getElementById('model-filter');

    if (teamFilter) {
        teamFilter.addEventListener('change', () => applyFilters());
    }
    if (providerFilter) {
        providerFilter.addEventListener('change', () => applyFilters());
    }
    if (modelFilter) {
        modelFilter.addEventListener('change', () => applyFilters());
    }
}

async function applyFilters() {
    const filters = getActiveFilters();
    await loadAnalyticsData(filters);
    updateCharts(filters);
}

function getActiveFilters() {
    return {
        start_date: document.getElementById('start-date')?.value || '',
        end_date: document.getElementById('end-date')?.value || '',
        team_id: document.getElementById('team-filter')?.value || '',
        provider: document.getElementById('provider-filter')?.value || '',
        model: document.getElementById('model-filter')?.value || ''
    };
}

// =========================================
// DATA LOADING
// =========================================

async function loadAnalyticsData(filters = {}) {
    try {
        const query = new URLSearchParams();
        Object.entries(filters).forEach(([key, value]) => {
            if (value) query.append(key, value);
        });

        const response = await fetch(`/api/analytics/data?${query}`, {
            headers: { 'X-API-Key': localStorage.getItem('substacker_api_key') }
        });

        if (!response.ok) throw new Error('Failed to load analytics data');
        const data = await response.json();

        updateMetrics(data.metrics);
        updateTables(data);
        return data;
    } catch (error) {
        console.error('Error loading analytics data:', error);
        showNotification('Failed to load analytics data', 'error');
    }
}

function updateMetrics(metrics) {
    if (!metrics) return;

    document.getElementById('total-cost').textContent = 
        '$' + (metrics.total_cost / 100).toFixed(2);
    document.getElementById('total-calls').textContent = 
        metrics.total_calls.toLocaleString();
    document.getElementById('avg-cost-call').textContent = 
        '$' + ((metrics.total_cost / 100 / metrics.total_calls) || 0).toFixed(4);
    document.getElementById('total-tokens').textContent = 
        metrics.total_tokens.toLocaleString();
}

function updateTables(data) {
    updateTeamPerformanceTable(data.team_performance || []);
    updateModelComparisonTable(data.model_comparison || []);
    updateAnomalyAlertsTable(data.anomalies || []);
}

function updateTeamPerformanceTable(teams) {
    const tbody = document.getElementById('team-performance-tbody');
    if (!tbody) return;

    tbody.innerHTML = teams.map(team => `
        <tr>
            <td><strong>${team.name}</strong></td>
            <td>${team.call_count.toLocaleString()}</td>
            <td>$${(team.cost / 100).toFixed(2)}</td>
            <td>${team.models.join(', ')}</td>
            <td><span class="badge badge-primary">${team.status}</span></td>
        </tr>
    `).join('');
}

function updateModelComparisonTable(models) {
    const tbody = document.getElementById('model-comparison-tbody');
    if (!tbody) return;

    tbody.innerHTML = models.map(model => `
        <tr>
            <td><code>${model.name}</code></td>
            <td>${model.provider}</td>
            <td>${model.calls.toLocaleString()}</td>
            <td>${model.tokens.toLocaleString()}</td>
            <td>$${(model.cost / 100).toFixed(4)}</td>
            <td>${(model.avg_cost / 100).toFixed(4)}</td>
        </tr>
    `).join('');
}

function updateAnomalyAlertsTable(anomalies) {
    const tbody = document.getElementById('anomaly-alerts-tbody');
    if (!tbody) return;

    if (!anomalies.length) {
        tbody.innerHTML = '<tr><td colspan="5" style="text-align: center; padding: 20px;">No anomalies detected</td></tr>';
        return;
    }

    tbody.innerHTML = anomalies.map(anomaly => `
        <tr>
            <td>${new Date(anomaly.timestamp).toLocaleString()}</td>
            <td>${anomaly.team}</td>
            <td><strong>$${(anomaly.cost / 100).toFixed(2)}</strong></td>
            <td>${anomaly.type}</td>
            <td><span class="badge badge-warning">${anomaly.severity}</span></td>
        </tr>
    `).join('');
}

// =========================================
// CHARTS
// =========================================

let costTrendChart, providerChart, modelChart;

function setupCharts() {
    initCostTrendChart();
    initProviderChart();
    initModelChart();
}

function initCostTrendChart() {
    const ctx = document.getElementById('cost-trend-chart');
    if (!ctx) return;

    costTrendChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: [],
            datasets: [{
                label: 'Daily Cost',
                data: [],
                borderColor: '#3b82f6',
                backgroundColor: 'rgba(59, 130, 246, 0.1)',
                tension: 0.4,
                fill: true,
                pointRadius: 4,
                pointHoverRadius: 6
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: true }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    title: { display: true, text: 'Cost ($)' }
                }
            }
        }
    });
}

function initProviderChart() {
    const ctx = document.getElementById('provider-breakdown-chart');
    if (!ctx) return;

    providerChart = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: ['OpenAI', 'Anthropic', 'Google', 'Azure'],
            datasets: [{
                data: [45, 25, 20, 10],
                backgroundColor: ['#3b82f6', '#8b5cf6', '#10b981', '#f59e0b'],
                borderWidth: 0
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { position: 'bottom' }
            }
        }
    });
}

function initModelChart() {
    const ctx = document.getElementById('model-comparison-chart');
    if (!ctx) return;

    modelChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: [],
            datasets: [{
                label: 'Cost',
                data: [],
                backgroundColor: '#3b82f6'
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            indexAxis: 'y',
            plugins: {
                legend: { display: false }
            },
            scales: {
                x: {
                    beginAtZero: true,
                    title: { display: true, text: 'Cost ($)' }
                }
            }
        }
    });
}

function updateCharts(filters = {}) {
    // Update with filtered data
    if (costTrendChart) {
        costTrendChart.data.labels = generateDateLabels();
        costTrendChart.data.datasets[0].data = generateCostData();
        costTrendChart.update();
    }
}

function generateDateLabels() {
    const dates = [];
    const start = new Date(document.getElementById('start-date')?.value || '');
    const end = new Date(document.getElementById('end-date')?.value || '');

    for (let d = new Date(start); d <= end; d.setDate(d.getDate() + 1)) {
        dates.push(d.toLocaleDateString());
    }

    return dates;
}

function generateCostData() {
    // Generate sample data - in production, fetch from API
    const days = generateDateLabels().length;
    return Array.from({ length: days }, () => Math.floor(Math.random() * 1000));
}

// =========================================
// EXPORT FUNCTIONALITY
// =========================================

function setupExportButtons() {
    const exportCsvBtn = document.getElementById('export-csv-btn');
    const exportJsonBtn = document.getElementById('export-json-btn');
    const exportPdfBtn = document.getElementById('export-pdf-btn');

    if (exportCsvBtn) {
        exportCsvBtn.addEventListener('click', () => exportAnalyticsData('csv'));
    }
    if (exportJsonBtn) {
        exportJsonBtn.addEventListener('click', () => exportAnalyticsData('json'));
    }
    if (exportPdfBtn) {
        exportPdfBtn.addEventListener('click', () => exportAnalyticsData('pdf'));
    }
}

async function exportAnalyticsData(format) {
    const filters = getActiveFilters();

    try {
        const query = new URLSearchParams();
        Object.entries(filters).forEach(([key, value]) => {
            if (value) query.append(key, value);
        });

        const response = await fetch(`/api/analytics/export?format=${format}&${query}`, {
            headers: { 'X-API-Key': localStorage.getItem('substacker_api_key') }
        });

        if (!response.ok) throw new Error('Failed to export data');

        const blob = await response.blob();
        const url = URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = `analytics-${new Date().toISOString().split('T')[0]}.${format}`;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        URL.revokeObjectURL(url);

        showNotification(`Data exported as ${format.toUpperCase()}`, 'success');
    } catch (error) {
        console.error('Error exporting data:', error);
        showNotification('Failed to export data', 'error');
    }
}

// =========================================
// WEBSOCKET UPDATES
// =========================================

function setupWebSocketUpdates() {
    if (!window.wsManager) return;

    window.wsManager.on('metrics_update', (data) => {
        updateMetrics(data.metrics);
    });

    window.wsManager.on('anomaly', (data) => {
        showNotification(`Anomaly detected: ${data.message}`, 'warning');
        const tbody = document.getElementById('anomaly-alerts-tbody');
        if (tbody) {
            const row = document.createElement('tr');
            row.innerHTML = `
                <td>${new Date().toLocaleString()}</td>
                <td>${data.team}</td>
                <td><strong>$${(data.cost / 100).toFixed(2)}</strong></td>
                <td>${data.type}</td>
                <td><span class="badge badge-warning">${data.severity}</span></td>
            `;
            tbody.insertBefore(row, tbody.firstChild);
        }
    });

    window.wsManager.requestMetrics();
}

// =========================================
// UTILITY FUNCTIONS
// =========================================

function showNotification(message, type = 'info') {
    const container = document.getElementById('toast-container') || createToastContainer();
    
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.innerHTML = `
        <i class="fas fa-${getNotificationIcon(type)}"></i>
        <span>${message}</span>
        <button class="toast-close" onclick="this.parentElement.remove()">×</button>
    `;

    container.appendChild(toast);
    setTimeout(() => toast.remove(), 5000);
}

function createToastContainer() {
    const container = document.createElement('div');
    container.id = 'toast-container';
    container.className = 'toast-container';
    document.body.appendChild(container);
    return container;
}

function getNotificationIcon(type) {
    const icons = {
        success: 'check-circle',
        error: 'exclamation-circle',
        warning: 'exclamation-triangle',
        info: 'info-circle'
    };
    return icons[type] || 'info-circle';
}

function refreshAnalytics() {
    loadAnalyticsData(getActiveFilters());
    showNotification('Analytics refreshed', 'info');
}
