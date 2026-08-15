// ===== ADMIN DASHBOARD FUNCTIONALITY v2.0 =====

// Global charts object
const charts = {};
const chartColors = {
    primary: '#6366f1',
    success: '#10b981',
    warning: '#f59e0b',
    danger: '#ef4444',
    info: '#3b82f6',
    purple: '#8b5cf6',
    providers: {
        openai: '#10b981',
        anthropic: '#f59e0b',
        google: '#3b82f6',
        azure: '#8b5cf6'
    }
};

// Get all menu items and sections
const menuItems = document.querySelectorAll('.menu-item');
const sections = document.querySelectorAll('.admin-section');
const logoutBtn = document.getElementById('logoutBtn');

// ===== SECTION NAVIGATION =====

menuItems.forEach(item => {
    item.addEventListener('click', (e) => {
        e.preventDefault();
        
        const sectionName = item.getAttribute('data-section');
        
        menuItems.forEach(m => m.classList.remove('active'));
        sections.forEach(s => s.classList.remove('active'));
        
        item.classList.add('active');
        const targetSection = document.getElementById(sectionName);
        if (targetSection) {
            targetSection.classList.add('active');
            
            // Initialize charts when overview section is shown
            if (sectionName === 'overview') {
                setTimeout(initCharts, 100);
            }
        }
    });
});

// ===== LOGOUT FUNCTIONALITY =====

logoutBtn.addEventListener('click', () => {
    document.cookie = 'admin_token=; path=/; expires=Thu, 01 Jan 1970 00:00:00 UTC;';
    window.location.href = '/';
});

// ===== CHART INITIALIZATION =====

function initCharts() {
    // Only initialize once
    if (Object.keys(charts).length > 0) return;
    
    // Sample data for demonstration (in production, fetch from API)
    const leadsData = generateLeadsData(30);
    const providerData = {
        labels: ['OpenAI', 'Anthropic', 'Google', 'Azure'],
        data: [4500, 2100, 890, 1200]
    };
    const teamData = {
        labels: ['Engineering', 'Data Science', 'Marketing', 'Product'],
        data: [3200, 2100, 1800, 1590]
    };
    const modelData = {
        labels: ['GPT-4', 'GPT-3.5', 'Claude-3', 'Gemini-Pro', 'Others'],
        data: [3400, 2100, 1800, 800, 392]
    };
    
    // Initialize each chart
    initLeadsChart(leadsData);
    initProviderChart(providerData);
    initTeamChart(teamData);
    initModelChart(modelData);
}

function generateLeadsData(days) {
    const labels = [];
    const data = [];
    const today = new Date();
    
    for (let i = days; i > 0; i--) {
        const date = new Date(today);
        date.setDate(date.getDate() - i);
        labels.push(date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' }));
        data.push(Math.floor(Math.random() * 30 + 10)); // Random leads 10-40
    }
    
    return { labels, data };
}

function initLeadsChart(data) {
    const ctx = document.getElementById('leadsChart');
    if (!ctx) return;
    
    charts.leads = new Chart(ctx, {
        type: 'line',
        data: {
            labels: data.labels,
            datasets: [{
                label: 'New Leads',
                data: data.data,
                borderColor: chartColors.primary,
                backgroundColor: chartColors.primary + '15',
                fill: true,
                tension: 0.4,
                pointRadius: 4,
                pointBackgroundColor: chartColors.primary,
                pointBorderColor: '#fff',
                pointBorderWidth: 2
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            plugins: {
                legend: {
                    display: true,
                    position: 'top'
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    grid: {
                        color: 'rgba(0,0,0,0.05)'
                    }
                },
                x: {
                    grid: {
                        display: false
                    }
                }
            }
        }
    });
}

function initProviderChart(data) {
    const ctx = document.getElementById('providerChart');
    if (!ctx) return;
    
    const colors = [
        chartColors.providers.openai,
        chartColors.providers.anthropic,
        chartColors.providers.google,
        chartColors.providers.azure
    ];
    
    charts.provider = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: data.labels,
            datasets: [{
                data: data.data,
                backgroundColor: colors,
                borderColor: '#fff',
                borderWidth: 2
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            plugins: {
                legend: {
                    position: 'right'
                }
            }
        }
    });
}

function initTeamChart(data) {
    const ctx = document.getElementById('teamChart');
    if (!ctx) return;
    
    charts.team = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: data.labels,
            datasets: [{
                label: 'Cost ($)',
                data: data.data,
                backgroundColor: [
                    chartColors.primary,
                    chartColors.success,
                    chartColors.warning,
                    chartColors.danger
                ]
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            indexAxis: 'y',
            plugins: {
                legend: {
                    display: false
                }
            },
            scales: {
                x: {
                    beginAtZero: true,
                    grid: {
                        color: 'rgba(0,0,0,0.05)'
                    }
                },
                y: {
                    grid: {
                        display: false
                    }
                }
            }
        }
    });
}

function initModelChart(data) {
    const ctx = document.getElementById('modelChart');
    if (!ctx) return;
    
    charts.model = new Chart(ctx, {
        type: 'pie',
        data: {
            labels: data.labels,
            datasets: [{
                data: data.data,
                backgroundColor: [
                    chartColors.primary,
                    chartColors.success,
                    chartColors.warning,
                    chartColors.danger,
                    '#d1d5db'
                ],
                borderColor: '#fff',
                borderWidth: 2
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            plugins: {
                legend: {
                    position: 'bottom'
                }
            }
        }
    });
}

// ===== PERIOD SELECTOR =====

const trendsPeriod = document.getElementById('trendsPeriod');
if (trendsPeriod) {
    trendsPeriod.addEventListener('change', (e) => {
        const days = parseInt(e.target.value);
        const data = generateLeadsData(days);
        
        if (charts.leads) {
            charts.leads.data.labels = data.labels;
            charts.leads.data.datasets[0].data = data.data;
            charts.leads.update();
        }
    });
}

// ===== LEADS SEARCH =====

const leadsSearch = document.getElementById('leadsSearch');
if (leadsSearch) {
    leadsSearch.addEventListener('input', (e) => {
        const searchTerm = e.target.value.toLowerCase();
        const tableRows = document.querySelectorAll('.leads-table tbody tr');
        
        tableRows.forEach(row => {
            const email = row.querySelector('.email-cell').textContent.toLowerCase();
            row.style.display = email.includes(searchTerm) ? '' : 'none';
        });
    });
}

// ===== EXPORT LEADS =====

const exportLeadsBtn = document.getElementById('exportLeads');
if (exportLeadsBtn) {
    exportLeadsBtn.addEventListener('click', exportLeadsAsCSV);
}

function exportLeadsAsCSV() {
    const table = document.querySelector('.leads-table');
    let csv = '';
    
    // Headers
    const headers = [];
    table.querySelectorAll('thead th').forEach(th => {
        headers.push(th.textContent.trim());
    });
    csv += headers.join(',') + '\n';
    
    // Rows
    table.querySelectorAll('tbody tr').forEach(tr => {
        const row = [];
        tr.querySelectorAll('td').forEach((td, index) => {
            let text = td.textContent.trim();
            if (index === 0) {
                text = text.replace('envelope', '').trim();
            }
            if (text.includes(',')) {
                text = `"${text}"`;
            }
            row.push(text);
        });
        csv += row.join(',') + '\n';
    });
    
    downloadFile(csv, 'leads_export.csv', 'text/csv');
}

// ===== ALERTS MANAGEMENT =====

const clearAlertsBtn = document.getElementById('clearAlertsBtn');
if (clearAlertsBtn) {
    clearAlertsBtn.addEventListener('click', () => {
        const alertsContainer = document.querySelector('.alerts-container');
        const alerts = alertsContainer.querySelectorAll('.alert-item');
        alerts.forEach(alert => {
            alert.style.animation = 'fadeOut 0.3s ease-out';
            setTimeout(() => alert.remove(), 300);
        });
        
        // Show empty state
        alertsContainer.innerHTML = '<div class="empty-state"><p>No alerts</p></div>';
    });
}

// Alert click handlers
document.querySelectorAll('.alert-action').forEach(btn => {
    btn.addEventListener('click', () => {
        showNotification('Alert details would load here', 'info');
    });
});

// ===== REPORTS & EXPORTS =====

const generateReportBtn = document.getElementById('generateReportBtn');
if (generateReportBtn) {
    generateReportBtn.addEventListener('click', () => {
        const reportType = document.getElementById('reportType').value;
        generatePDFReport(reportType);
    });
}

const exportDataBtn = document.getElementById('exportDataBtn');
if (exportDataBtn) {
    exportDataBtn.addEventListener('click', exportAllData);
}

function generatePDFReport(type) {
    // In production, call backend API to generate PDF
    console.log('Generating ' + type + ' report...');
    
    const date = new Date().toLocaleDateString();
    const filename = `substacker-${type}-report-${date}.pdf`;
    
    showNotification('Report generated: ' + filename, 'success');
}

function exportAllData() {
    // Export comprehensive CSV with all analysis data
    let csv = 'Export Date,Lead Email,Status,Total Cost,Waste Found,Savings %,Provider,Team\n';
    
    // Add sample rows
    const sampleData = [
        ['Oct 30 2025', 'user1@example.com', 'analyzed', '1500', '350', '23.3%', 'OpenAI', 'Engineering'],
        ['Oct 30 2025', 'user2@example.com', 'analyzed', '2100', '580', '27.6%', 'Anthropic', 'Data Science'],
        ['Oct 29 2025', 'user3@example.com', 'new', '-', '-', '-', '-', '-']
    ];
    
    sampleData.forEach(row => {
        csv += row.map(cell => `"${cell}"`).join(',') + '\n';
    });
    
    downloadFile(csv, 'substacker-export.csv', 'text/csv');
    showNotification('Data exported successfully', 'success');
}

// Report card buttons
document.querySelectorAll('.report-button').forEach(btn => {
    btn.addEventListener('click', () => {
        const reportName = btn.parentElement.querySelector('h3').textContent;
        generatePDFReport(reportName.toLowerCase());
    });
});

// Report download buttons
document.querySelectorAll('.report-item .mini-button').forEach((btn, index) => {
    if (index % 2 === 0) {
        // Download button
        btn.addEventListener('click', () => {
            const reportName = btn.parentElement.parentElement.querySelector('.report-name').textContent;
            showNotification('Downloading: ' + reportName, 'info');
        });
    } else {
        // Delete button
        btn.addEventListener('click', () => {
            btn.parentElement.parentElement.parentElement.style.opacity = '0.5';
            setTimeout(() => {
                btn.parentElement.parentElement.parentElement.remove();
            }, 300);
            showNotification('Report deleted', 'warning');
        });
    }
});

// ===== MINI BUTTON ACTIONS =====

const miniButtons = document.querySelectorAll('.mini-button');
miniButtons.forEach(button => {
    button.addEventListener('click', (e) => {
        const icon = button.querySelector('i');
        const row = button.closest('tr');
        if (!row) return;
        
        const email = row.querySelector('.email-cell').textContent.replace('envelope', '').trim();
        
        if (icon.classList.contains('fa-eye')) {
            showNotification('Opening details for: ' + email, 'info');
        } else if (icon.classList.contains('fa-envelope')) {
            if (confirm('Send welcome email to ' + email + '?')) {
                showNotification('Email sent to ' + email, 'success');
            }
        }
    });
});

// ===== SETTINGS FUNCTIONALITY =====

// Email Notifications Toggle
const emailNotifToggle = document.getElementById('emailNotif');
if (emailNotifToggle) {
    emailNotifToggle.addEventListener('change', (e) => {
        const status = e.target.checked ? 'enabled' : 'disabled';
        showNotification('Email notifications ' + status, 'info');
    });
}

// Daily Report Toggle
const dailyReportToggle = document.getElementById('dailyReport');
if (dailyReportToggle) {
    dailyReportToggle.addEventListener('change', (e) => {
        const status = e.target.checked ? 'enabled' : 'disabled';
        showNotification('Daily reports ' + status, 'info');
    });
}

// Change Password Button
const changePasswordBtn = document.querySelector('.settings-form .form-button');
if (changePasswordBtn) {
    changePasswordBtn.addEventListener('click', (e) => {
        if (e.target.textContent.includes('Change Password')) {
            showNotification('Password change feature coming soon', 'warning');
        }
    });
}

// Clear Cache Button
const clearCacheBtn = document.querySelector('.settings-card.danger .form-button');
if (clearCacheBtn) {
    clearCacheBtn.addEventListener('click', (e) => {
        if (confirm('Clear the duplicate detection cache? This cannot be undone.')) {
            showNotification('Cache cleared successfully', 'success');
        }
    });
}

// ===== UTILITY FUNCTIONS =====

function downloadFile(content, filename, type) {
    const blob = new Blob([content], { type: type });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    window.URL.revokeObjectURL(url);
    a.remove();
}

function showNotification(message, type = 'info') {
    const notification = document.createElement('div');
    notification.className = `notification notification-${type}`;
    notification.innerHTML = `
        <i class="fas fa-${type === 'success' ? 'check-circle' : type === 'warning' ? 'exclamation-triangle' : type === 'danger' ? 'times-circle' : 'info-circle'}"></i>
        <span>${message}</span>
    `;
    
    document.body.appendChild(notification);
    
    setTimeout(() => {
        notification.classList.add('show');
    }, 10);
    
    setTimeout(() => {
        notification.classList.remove('show');
        setTimeout(() => notification.remove(), 300);
    }, 3000);
}

// ===== SDK KEYS MANAGEMENT =====

const createForm = document.getElementById('createKeyForm');
if (createForm) {
    const createdKeyDiv = document.getElementById('createdKey');
    const newKeyInput = document.getElementById('newKeyInput');
    const copyKeyBtn = document.getElementById('copyKeyBtn');
    const keysTable = document.getElementById('keysTable');

    createForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const formData = new FormData(createForm);
        try {
            const res = await fetch(createForm.action, {
                method: 'POST',
                body: formData
            });
            const data = await res.json();
            if(data.success && data.api_key){
                // show the key for one-time copy
                newKeyInput.value = data.api_key;
                createdKeyDiv.style.display = 'block';
                // add new row to table
                const tr = document.createElement('tr');
                tr.setAttribute('data-prefix', data.key_prefix);
                tr.innerHTML = `<td><code>${data.key_prefix}</code></td><td>Just now</td><td>-</td><td><span class="badge badge-success">Active</span></td><td><button class="mini-button revokeBtn"><i class="fas fa-times"></i> Revoke</button></td>`;
                keysTable.insertBefore(tr, keysTable.firstChild);
                showNotification('API key generated. Copy it now!', 'success');
            } else {
                showNotification(data.error || 'Failed to create key', 'danger');
            }
        } catch(err){
            showNotification('Key creation failed: ' + err.message, 'danger');
        }
    });

    if(copyKeyBtn) {
        copyKeyBtn.addEventListener('click', () => {
            if(newKeyInput.value){
                navigator.clipboard.writeText(newKeyInput.value);
                showNotification('API key copied to clipboard', 'success');
            }
        });
    }

    // Revoke buttons
    keysTable.addEventListener('click', async (e) => {
        if(e.target && (e.target.classList.contains('revokeBtn') || e.target.closest('.revokeBtn'))){
            const btn = e.target.closest('.revokeBtn');
            const tr = btn.closest('tr');
            const prefix = tr.getAttribute('data-prefix');
            if(!confirm('Revoke key ' + prefix + '? This cannot be undone.')) return;

            const form = new FormData();
            form.append('key_prefix', prefix);

            try{
                const res = await fetch('/api/revoke-key', { method: 'POST', body: form });
                const data = await res.json();
                if(data.success){
                    // update UI
                    tr.querySelector('td:nth-child(4)').innerHTML = '<span class="badge badge-gray">Revoked</span>';
                    btn.remove();
                    showNotification('Key revoked', 'success');
                } else {
                    showNotification(data.error || 'Failed to revoke', 'danger');
                }
            } catch(err){
                showNotification('Revoke failed: ' + err.message, 'danger');
            }
        }
    });
}

// ===== INITIALIZATION =====

// Initialize charts when page loads if overview section is visible
window.addEventListener('load', () => {
    const overviewSection = document.getElementById('overview');
    if (overviewSection && overviewSection.classList.contains('active')) {
        initCharts();
    }
});

console.log('Admin dashboard v2.0 loaded successfully');
