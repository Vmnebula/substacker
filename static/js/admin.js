// ===== ADMIN DASHBOARD JAVASCRIPT =====
// Comprehensive admin dashboard functionality including tabs, modals, CRUD operations, and real-time updates

// ===== STATE MANAGEMENT =====
const AdminState = {
    currentSection: 'overview',
    teams: [],
    budgets: [],
    alerts: [],
    filters: {
        dateRange: 30,
        team: null,
        provider: null,
        model: null
    },
    charts: {},
    initialized: false
};

// ===== INITIALIZATION =====
document.addEventListener('DOMContentLoaded', () => {
    initializeAdmin();
});

function initializeAdmin() {
    if (AdminState.initialized) return;
    
    setupTabNavigation();
    setupEventListeners();
    setupCharts();
    loadDashboardData();
    setupWebSocketConnection();
    
    AdminState.initialized = true;
}

// ===== TAB SWITCHING =====
function setupTabNavigation() {
    const menuItems = document.querySelectorAll('.menu-item');
    
    menuItems.forEach(item => {
        item.addEventListener('click', (e) => {
            e.preventDefault();
            const section = item.dataset.section;
            switchToSection(section);
        });
    });
}

function switchToSection(sectionName) {
    // Hide all sections
    document.querySelectorAll('.admin-section').forEach(section => {
        section.classList.remove('active');
    });
    
    // Show target section
    const targetSection = document.getElementById(sectionName);
    if (targetSection) {
        targetSection.classList.add('active');
        AdminState.currentSection = sectionName;
        
        // Load section-specific data
        switch(sectionName) {
            case 'teams':
                loadTeams();
                break;
            case 'budgets':
                loadBudgets();
                break;
            case 'alerts':
                loadAlerts();
                break;
            case 'settings':
                loadSettings();
                break;
        }
    }
    
    // Update active nav item
    document.querySelectorAll('.menu-item').forEach(item => {
        item.classList.toggle('active', item.dataset.section === sectionName);
    });
}

// ===== EVENT LISTENERS =====
function setupEventListeners() {
    // Logout button
    document.getElementById('logoutBtn')?.addEventListener('click', handleLogout);
    
    // Refresh button
    document.getElementById('refreshBtn')?.addEventListener('click', () => {
        loadDashboardData();
        showToast('Data refreshed', 'info');
    });
    
    // Date range selector
    document.getElementById('dateRangeSelect')?.addEventListener('change', (e) => {
        AdminState.filters.dateRange = parseInt(e.target.value);
        if (AdminState.currentSection === 'overview') {
            loadDashboardData();
        }
    });
    
    // Team CRUD buttons
    document.getElementById('createTeamBtn')?.addEventListener('click', openCreateTeamModal);
    document.getElementById('clearFiltersBtn')?.addEventListener('click', clearFilters);
    
    // Budget buttons
    document.getElementById('createBudgetBtn')?.addEventListener('click', openCreateBudgetModal);
    
    // Alert buttons
    document.getElementById('configureAlertsBtn')?.addEventListener('click', openAlertConfigModal);
    document.getElementById('clearAllAlertsBtn')?.addEventListener('click', clearAllAlerts);
    
    // Settings buttons
    document.getElementById('saveSettingsBtn')?.addEventListener('click', saveSettings);
    document.getElementById('resetSettingsBtn')?.addEventListener('click', resetSettings);
}

// ===== DATA LOADING =====
async function loadDashboardData() {
    try {
        // Simulate API call
        const mockData = generateMockDashboardData();
        
        // Update KPI cards
        updateKPICards(mockData);
        
        // Update charts
        updateCharts(mockData);
        
        // Update top teams table
        updateTopTeamsTable(mockData.topTeams);
        
    } catch (error) {
        console.error('Error loading dashboard data:', error);
        showToast('Failed to load dashboard data', 'error');
    }
}

function generateMockDashboardData() {
    const now = Date.now();
    const days = AdminState.filters.dateRange;
    
    return {
        totalCost: 15234.50,
        costChange: 12.5,
        activeTeams: 8,
        teamChange: 2,
        activeAlerts: 3,
        alertsStatus: 'warning',
        growthRate: 8.5,
        growthTrend: 'up',
        costTrend: Array.from({length: days}, (_, i) => ({
            date: new Date(now - (days - i) * 86400000).toLocaleDateString(),
            cost: Math.random() * 1000 + 400
        })),
        teamDistribution: [
            {name: 'Engineering', value: 8500},
            {name: 'Product', value: 3200},
            {name: 'Data', value: 2100},
            {name: 'Support', value: 1434}
        ],
        topTeams: [
            {name: 'Engineering', cost: 8500, budget: 10000, utilization: 85, status: 'on-track'},
            {name: 'Product', cost: 3200, budget: 5000, utilization: 64, status: 'on-track'},
            {name: 'Data', cost: 2100, budget: 3000, utilization: 70, status: 'on-track'},
            {name: 'Support', cost: 1434, budget: 2000, utilization: 72, status: 'on-track'}
        ]
    };
}

function updateKPICards(data) {
    document.getElementById('totalOrgCost').textContent = formatCurrency(data.totalCost);
    document.getElementById('costChange').textContent = `${data.costChange > 0 ? '+' : ''}${data.costChange}%`;
    document.getElementById('activeTeams').textContent = data.activeTeams;
    document.getElementById('teamChange').textContent = `${data.teamChange} new this period`;
    document.getElementById('activeAlerts').textContent = data.activeAlerts;
    document.getElementById('alertsStatus').textContent = data.activeAlerts > 0 ? `${data.activeAlerts} alerts` : 'All systems normal';
    document.getElementById('growthRate').textContent = `${data.growthRate}%`;
    document.getElementById('growthTrend').textContent = `${data.growthTrend === 'up' ? '↑' : '↓'} Month-on-month`;
}

function updateTopTeamsTable(teams) {
    const tbody = document.getElementById('topTeamsBody');
    if (!tbody) return;
    
    tbody.innerHTML = teams.map(team => `
        <tr>
            <td>${team.name}</td>
            <td>${formatCurrency(team.cost)}</td>
            <td>${formatCurrency(team.budget)}</td>
            <td>
                <div style="display: flex; align-items: center; gap: 8px;">
                    <div style="background: #e5e7eb; height: 8px; border-radius: 4px; flex: 1; width: 100px;">
                        <div style="background: ${team.utilization > 80 ? '#ef4444' : '#10b981'}; height: 100%; width: ${team.utilization}%; border-radius: 4px;"></div>
                    </div>
                    ${team.utilization}%
                </div>
            </td>
            <td><span class="badge badge-success">${team.status}</span></td>
            <td>
                <button class="mini-button" onclick="editTeam('${team.name}')" title="Edit">
                    <i class="fas fa-edit"></i>
                </button>
                <button class="mini-button" onclick="deleteTeam('${team.name}')" title="Delete">
                    <i class="fas fa-trash"></i>
                </button>
            </td>
        </tr>
    `).join('');
}

// ===== CHARTS =====
function setupCharts() {
    const ctx1 = document.getElementById('costTrendChart')?.getContext('2d');
    const ctx2 = document.getElementById('teamDistributionChart')?.getContext('2d');
    
    if (ctx1) {
        AdminState.charts.costTrend = new Chart(ctx1, {
            type: 'line',
            data: {
                labels: Array.from({length: 30}, (_, i) => i + 1),
                datasets: [{
                    label: 'Daily Cost',
                    data: Array.from({length: 30}, () => Math.random() * 1000 + 400),
                    borderColor: '#ef4444',
                    backgroundColor: 'rgba(239, 68, 68, 0.1)',
                    tension: 0.4,
                    fill: true
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {display: false}
                },
                scales: {
                    y: {beginAtZero: true}
                }
            }
        });
    }
    
    if (ctx2) {
        AdminState.charts.teamDistribution = new Chart(ctx2, {
            type: 'doughnut',
            data: {
                labels: ['Engineering', 'Product', 'Data', 'Support'],
                datasets: [{
                    data: [8500, 3200, 2100, 1434],
                    backgroundColor: ['#ef4444', '#3b82f6', '#10b981', '#f59e0b']
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {position: 'bottom'}
                }
            }
        });
    }
}

function updateCharts(data) {
    // Update cost trend chart
    if (AdminState.charts.costTrend) {
        AdminState.charts.costTrend.data.labels = data.costTrend.map(d => d.date);
        AdminState.charts.costTrend.data.datasets[0].data = data.costTrend.map(d => d.cost);
        AdminState.charts.costTrend.update();
    }
    
    // Update team distribution chart
    if (AdminState.charts.teamDistribution) {
        AdminState.charts.teamDistribution.data.labels = data.teamDistribution.map(d => d.name);
        AdminState.charts.teamDistribution.data.datasets[0].data = data.teamDistribution.map(d => d.value);
        AdminState.charts.teamDistribution.update();
    }
}

// ===== TEAM MANAGEMENT =====
async function loadTeams(page = 1) {
    try {
        const mockTeams = [
            {id: 1, name: 'Engineering', members: 8, created: '2025-01-15', status: 'active', monthlyCost: 8500},
            {id: 2, name: 'Product', members: 5, created: '2025-02-01', status: 'active', monthlyCost: 3200},
            {id: 3, name: 'Data', members: 3, created: '2025-02-15', status: 'active', monthlyCost: 2100},
            {id: 4, name: 'Support', members: 2, created: '2025-03-01', status: 'active', monthlyCost: 1434}
        ];
        
        AdminState.teams = mockTeams;
        updateTeamsTable(mockTeams);
    } catch (error) {
        console.error('Error loading teams:', error);
    }
}

function updateTeamsTable(teams) {
    const tbody = document.getElementById('teamsTableBody');
    if (!tbody) return;
    
    tbody.innerHTML = teams.map(team => `
        <tr>
            <td>${team.name}</td>
            <td>${team.members}</td>
            <td>${team.created}</td>
            <td><span class="badge badge-success">${team.status}</span></td>
            <td>${formatCurrency(team.monthlyCost)}</td>
            <td>
                <button class="mini-button" onclick="editTeam('${team.name}')" title="Edit">
                    <i class="fas fa-edit"></i>
                </button>
                <button class="mini-button" onclick="deleteTeam('${team.name}')" title="Delete">
                    <i class="fas fa-trash"></i>
                </button>
            </td>
        </tr>
    `).join('');
}

function openCreateTeamModal() {
    const modal = createModal('Create Team', `
        <div class="form-group">
            <label>Team Name</label>
            <input type="text" id="teamNameInput" class="form-input" placeholder="Engineering">
        </div>
        <div class="form-group">
            <label>Description</label>
            <textarea id="teamDescInput" class="form-input" placeholder="Team description" style="height: 80px;"></textarea>
        </div>
        <div class="form-group">
            <label>Budget (Monthly)</label>
            <input type="number" id="teamBudgetInput" class="form-input" placeholder="10000">
        </div>
        <div style="display: flex; gap: 10px; margin-top: 20px;">
            <button onclick="saveTeam()" class="action-button primary" style="flex: 1;">Create</button>
            <button onclick="closeModal()" class="action-button secondary" style="flex: 1;">Cancel</button>
        </div>
    `);
}

function saveTeam() {
    const name = document.getElementById('teamNameInput')?.value;
    const desc = document.getElementById('teamDescInput')?.value;
    const budget = document.getElementById('teamBudgetInput')?.value;
    
    if (!name) {
        showToast('Please enter team name', 'error');
        return;
    }
    
    showToast(`Team "${name}" created successfully`, 'success');
    closeModal();
    loadTeams();
}

function editTeam(teamName) {
    const team = AdminState.teams.find(t => t.name === teamName);
    if (!team) return;
    
    const modal = createModal(`Edit Team: ${teamName}`, `
        <div class="form-group">
            <label>Team Name</label>
            <input type="text" id="teamNameInput" class="form-input" value="${team.name}">
        </div>
        <div class="form-group">
            <label>Status</label>
            <select id="teamStatusInput" class="form-input">
                <option value="active" ${team.status === 'active' ? 'selected' : ''}>Active</option>
                <option value="inactive" ${team.status === 'inactive' ? 'selected' : ''}>Inactive</option>
                <option value="archived" ${team.status === 'archived' ? 'selected' : ''}>Archived</option>
            </select>
        </div>
        <div style="display: flex; gap: 10px; margin-top: 20px;">
            <button onclick="updateTeam('${teamName}')" class="action-button primary" style="flex: 1;">Update</button>
            <button onclick="closeModal()" class="action-button secondary" style="flex: 1;">Cancel</button>
        </div>
    `);
}

function updateTeam(oldName) {
    const newName = document.getElementById('teamNameInput')?.value;
    showToast(`Team updated successfully`, 'success');
    closeModal();
    loadTeams();
}

function deleteTeam(teamName) {
    if (!confirm(`Are you sure you want to delete team "${teamName}"?`)) return;
    showToast(`Team "${teamName}" deleted`, 'success');
    loadTeams();
}

// ===== BUDGET MANAGEMENT =====
async function loadBudgets() {
    try {
        const mockBudgets = [
            {team: 'Engineering', budget: 10000, spent: 8500, status: 'on-track'},
            {team: 'Product', budget: 5000, spent: 3200, status: 'on-track'},
            {team: 'Data', budget: 3000, spent: 2100, status: 'on-track'},
            {team: 'Support', budget: 2000, spent: 1434, status: 'on-track'}
        ];
        
        AdminState.budgets = mockBudgets;
        updateBudgetsGrid(mockBudgets);
    } catch (error) {
        console.error('Error loading budgets:', error);
    }
}

function updateBudgetsGrid(budgets) {
    const grid = document.getElementById('budgetsGrid');
    if (!grid) return;
    
    grid.innerHTML = budgets.map(budget => `
        <div class="budget-card" style="background: white; border: 1px solid #e5e7eb; border-radius: 12px; padding: 20px;">
            <div style="display: flex; justify-content: space-between; align-items: start; margin-bottom: 16px;">
                <h3 style="font-weight: 600; font-size: 1.1rem;">${budget.team}</h3>
                <button class="mini-button" onclick="editBudget('${budget.team}')">
                    <i class="fas fa-edit"></i>
                </button>
            </div>
            <div style="margin-bottom: 12px;">
                <div style="display: flex; justify-content: space-between; margin-bottom: 8px;">
                    <span style="color: #6b7280;">Spent</span>
                    <span style="font-weight: 600;">${formatCurrency(budget.spent)}</span>
                </div>
                <div style="background: #e5e7eb; height: 8px; border-radius: 4px;">
                    <div style="background: ${budget.spent / budget.budget > 0.8 ? '#ef4444' : '#10b981'}; height: 100%; width: ${(budget.spent / budget.budget) * 100}%; border-radius: 4px;"></div>
                </div>
            </div>
            <div style="display: flex; justify-content: space-between; color: #6b7280; font-size: 0.9rem;">
                <span>${formatCurrency(budget.spent)} / ${formatCurrency(budget.budget)}</span>
                <span class="badge" style="background: ${budget.spent / budget.budget > 0.8 ? 'rgba(239, 68, 68, 0.1); color: #ef4444;' : 'rgba(16, 185, 129, 0.1); color: #10b981;'}">${budget.status}</span>
            </div>
        </div>
    `).join('');
}

function openCreateBudgetModal() {
    const modal = createModal('Create Budget', `
        <div class="form-group">
            <label>Team</label>
            <select id="budgetTeamSelect" class="form-input">
                ${AdminState.teams.map(t => `<option value="${t.name}">${t.name}</option>`).join('')}
            </select>
        </div>
        <div class="form-group">
            <label>Monthly Budget Amount</label>
            <input type="number" id="budgetAmountInput" class="form-input" placeholder="10000">
        </div>
        <div class="form-group">
            <label>Alert Threshold (%)</label>
            <input type="number" id="budgetThresholdInput" class="form-input" value="80" min="0" max="100">
        </div>
        <div style="display: flex; gap: 10px; margin-top: 20px;">
            <button onclick="saveBudget()" class="action-button primary" style="flex: 1;">Create</button>
            <button onclick="closeModal()" class="action-button secondary" style="flex: 1;">Cancel</button>
        </div>
    `);
}

function saveBudget() {
    const team = document.getElementById('budgetTeamSelect')?.value;
    const amount = document.getElementById('budgetAmountInput')?.value;
    const threshold = document.getElementById('budgetThresholdInput')?.value;
    
    if (!team || !amount) {
        showToast('Please fill all required fields', 'error');
        return;
    }
    
    showToast(`Budget created for ${team}`, 'success');
    closeModal();
    loadBudgets();
}

function editBudget(teamName) {
    const budget = AdminState.budgets.find(b => b.team === teamName);
    if (!budget) return;
    
    const modal = createModal(`Edit Budget: ${teamName}`, `
        <div class="form-group">
            <label>Monthly Budget Amount</label>
            <input type="number" id="budgetAmountInput" class="form-input" value="${budget.budget}">
        </div>
        <div class="form-group">
            <label>Alert Threshold (%)</label>
            <input type="number" id="budgetThresholdInput" class="form-input" value="80">
        </div>
        <div style="display: flex; gap: 10px; margin-top: 20px;">
            <button onclick="updateBudget('${teamName}')" class="action-button primary" style="flex: 1;">Update</button>
            <button onclick="closeModal()" class="action-button secondary" style="flex: 1;">Cancel</button>
        </div>
    `);
}

function updateBudget(teamName) {
    showToast(`Budget updated for ${teamName}`, 'success');
    closeModal();
    loadBudgets();
}

// ===== ALERT MANAGEMENT =====
async function loadAlerts() {
    try {
        const mockAlerts = [
            {
                type: 'budget-exceeded',
                severity: 'high',
                title: 'Budget Alert: Engineering Team',
                description: 'Engineering team is at 85% of monthly budget ($8,500/$10,000)',
                timestamp: '2 hours ago'
            },
            {
                type: 'anomaly',
                severity: 'medium',
                title: 'Unusual Cost Pattern',
                description: 'GPT-4 usage increased 150% compared to last week',
                timestamp: '4 hours ago'
            },
            {
                type: 'threshold',
                severity: 'critical',
                title: 'Daily Spending Threshold Exceeded',
                description: 'Daily spend reached $2,500 today (Alert threshold: $2,000)',
                timestamp: '1 hour ago'
            }
        ];
        
        AdminState.alerts = mockAlerts;
        updateAlertsContainer(mockAlerts);
    } catch (error) {
        console.error('Error loading alerts:', error);
    }
}

function updateAlertsContainer(alerts) {
    const container = document.getElementById('alertsContainer');
    if (!container) return;
    
    if (alerts.length === 0) {
        container.innerHTML = '<div class="text-center" style="padding: 40px;">No active alerts</div>';
        return;
    }
    
    const severityColors = {
        critical: '#ef4444',
        high: '#f59e0b',
        medium: '#3b82f6',
        low: '#10b981'
    };
    
    container.innerHTML = alerts.map(alert => `
        <div class="alert-item" style="border-left-color: ${severityColors[alert.severity]}; padding: 16px; border-left: 4px solid; border-radius: 6px; background: white; margin-bottom: 12px; display: flex; justify-content: space-between; align-items: start;">
            <div style="flex: 1;">
                <div style="font-weight: 600; margin-bottom: 4px;">${alert.title}</div>
                <div style="color: #6b7280; font-size: 0.9rem; margin-bottom: 8px;">${alert.description}</div>
                <div style="font-size: 0.85rem; color: #9ca3af;">${alert.timestamp}</div>
            </div>
            <button class="mini-button" title="Dismiss" onclick="dismissAlert('${alert.title}')">
                <i class="fas fa-times"></i>
            </button>
        </div>
    `).join('');
}

function openAlertConfigModal() {
    const modal = createModal('Configure Alerts', `
        <div class="form-group">
            <label class="label-with-toggle">
                <span>Budget Alerts</span>
                <div class="toggle-switch">
                    <input type="checkbox" id="alertBudget" checked>
                    <label for="alertBudget"></label>
                </div>
            </label>
            <input type="number" id="budgetThreshold" class="form-input" value="80" placeholder="% threshold">
        </div>
        <div class="form-group">
            <label class="label-with-toggle">
                <span>Anomaly Detection</span>
                <div class="toggle-switch">
                    <input type="checkbox" id="alertAnomaly" checked>
                    <label for="alertAnomaly"></label>
                </div>
            </label>
        </div>
        <div class="form-group">
            <label class="label-with-toggle">
                <span>Daily Threshold Alerts</span>
                <div class="toggle-switch">
                    <input type="checkbox" id="alertDaily" checked>
                    <label for="alertDaily"></label>
                </div>
            </label>
            <input type="number" id="dailyThreshold" class="form-input" value="2000" placeholder="Daily limit">
        </div>
        <div style="display: flex; gap: 10px; margin-top: 20px;">
            <button onclick="saveAlertConfig()" class="action-button primary" style="flex: 1;">Save</button>
            <button onclick="closeModal()" class="action-button secondary" style="flex: 1;">Cancel</button>
        </div>
    `);
}

function saveAlertConfig() {
    showToast('Alert configuration updated', 'success');
    closeModal();
}

function dismissAlert(title) {
    AdminState.alerts = AdminState.alerts.filter(a => a.title !== title);
    updateAlertsContainer(AdminState.alerts);
    showToast('Alert dismissed', 'info');
}

function clearAllAlerts() {
    if (!confirm('Clear all alerts?')) return;
    AdminState.alerts = [];
    updateAlertsContainer([]);
    showToast('All alerts cleared', 'success');
}

// ===== SETTINGS =====
async function loadSettings() {
    // Load current settings
}

function saveSettings() {
    showToast('Settings saved successfully', 'success');
}

function resetSettings() {
    if (!confirm('Reset all settings to defaults?')) return;
    showToast('Settings reset to defaults', 'info');
}

// ===== FILTERS =====
function clearFilters() {
    AdminState.filters = {
        dateRange: 30,
        team: null,
        provider: null,
        model: null
    };
    document.querySelectorAll('.filter-select, .filter-input').forEach(el => {
        el.value = '';
    });
    showToast('Filters cleared', 'info');
    loadTeams();
}

// ===== MODALS =====
function createModal(title, content) {
    const modal = document.createElement('div');
    modal.className = 'modal-overlay';
    modal.style.cssText = `
        position: fixed;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        background: rgba(0,0,0,0.5);
        display: flex;
        align-items: center;
        justify-content: center;
        z-index: 1000;
    `;
    
    modal.innerHTML = `
        <div class="modal-content" style="background: white; border-radius: 12px; padding: 24px; max-width: 500px; width: 90%; box-shadow: 0 20px 25px rgba(0,0,0,0.15);">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
                <h2 style="font-size: 1.25rem; font-weight: 700;">${title}</h2>
                <button onclick="closeModal()" style="background: none; border: none; font-size: 1.5rem; cursor: pointer; color: #6b7280;">
                    <i class="fas fa-times"></i>
                </button>
            </div>
            ${content}
        </div>
    `;
    
    document.body.appendChild(modal);
    modal.addEventListener('click', (e) => {
        if (e.target === modal) closeModal();
    });
    
    return modal;
}

function closeModal() {
    const modal = document.querySelector('.modal-overlay');
    if (modal) modal.remove();
}

// ===== WEBSOCKET INTEGRATION =====
function setupWebSocketConnection() {
    if (window.WebSocketManager) {
        window.WebSocketManager.connect();
        window.WebSocketManager.on('data-update', (data) => {
            if (AdminState.currentSection === 'overview') {
                updateKPICards(data);
                updateCharts(data);
            }
        });
    }
}

// ===== UTILITIES =====
function formatCurrency(amount) {
    return new Intl.NumberFormat('en-US', {
        style: 'currency',
        currency: 'USD'
    }).format(amount);
}

function showToast(message, type = 'info') {
    const toast = document.createElement('div');
    toast.className = `notification notification-${type} show`;
    toast.style.cssText = `
        position: fixed;
        bottom: 20px;
        right: 20px;
        padding: 16px 20px;
        background: white;
        border-radius: 8px;
        box-shadow: 0 10px 25px rgba(0,0,0,0.2);
        display: flex;
        align-items: center;
        gap: 12px;
        z-index: 2000;
        animation: slideIn 0.3s ease;
    `;
    
    const iconClass = {
        success: 'fa-check-circle',
        error: 'fa-exclamation-circle',
        warning: 'fa-exclamation-triangle',
        info: 'fa-info-circle'
    }[type] || 'fa-info-circle';
    
    toast.innerHTML = `
        <i class="fas ${iconClass}"></i>
        <span>${message}</span>
    `;
    
    document.getElementById('toastContainer').appendChild(toast);
    setTimeout(() => toast.remove(), 3000);
}

function handleLogout() {
    if (confirm('Are you sure you want to logout?')) {
        window.location.href = '/logout';
    }
}
