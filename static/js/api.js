/**
 * API Client
 * Centralized API communication and data fetching
 */

class APIClient {
    constructor(baseURL = '/api', timeout = 30000) {
        this.baseURL = baseURL;
        this.timeout = timeout;
        this.headers = {
            'Content-Type': 'application/json'
        };
    }

    /**
     * Get API key from storage
     */
    getApiKey() {
        return localStorage.getItem('substacker_api_key');
    }

    /**
     * Set API key in headers
     */
    setApiKey(key) {
        localStorage.setItem('substacker_api_key', key);
        if (key) {
            this.headers['X-API-Key'] = key;
        } else {
            delete this.headers['X-API-Key'];
        }
    }

    /**
     * Generic fetch wrapper
     */
    async fetch(endpoint, options = {}) {
        const url = `${this.baseURL}${endpoint}`;
        const apiKey = this.getApiKey();

        const config = {
            method: options.method || 'GET',
            headers: { ...this.headers },
            timeout: this.timeout,
            ...options
        };

        if (apiKey) {
            config.headers['X-API-Key'] = apiKey;
        }

        try {
            const response = await fetch(url, config);

            // Handle 401 Unauthorized
            if (response.status === 401) {
                this.setApiKey(null);
                window.location.href = '/admin/login';
                return null;
            }

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }

            // Handle empty response
            if (response.status === 204) {
                return null;
            }

            return await response.json();
        } catch (error) {
            console.error('API Error:', error);
            throw error;
        }
    }

    /**
     * GET request
     */
    get(endpoint, params = {}) {
        const query = new URLSearchParams(params).toString();
        const url = query ? `${endpoint}?${query}` : endpoint;
        return this.fetch(url, { method: 'GET' });
    }

    /**
     * POST request
     */
    post(endpoint, data = {}) {
        return this.fetch(endpoint, {
            method: 'POST',
            body: JSON.stringify(data)
        });
    }

    /**
     * PUT request
     */
    put(endpoint, data = {}) {
        return this.fetch(endpoint, {
            method: 'PUT',
            body: JSON.stringify(data)
        });
    }

    /**
     * DELETE request
     */
    delete(endpoint) {
        return this.fetch(endpoint, { method: 'DELETE' });
    }

    /**
     * PATCH request
     */
    patch(endpoint, data = {}) {
        return this.fetch(endpoint, {
            method: 'PATCH',
            body: JSON.stringify(data)
        });
    }

    // =========================================
    // ADMIN ENDPOINTS
    // =========================================

    /**
     * Get admin dashboard data
     */
    getAdminDashboard() {
        return this.get('/admin/dashboard');
    }

    /**
     * Get all teams
     */
    getTeams() {
        return this.get('/admin/teams');
    }

    /**
     * Create team
     */
    createTeam(data) {
        return this.post('/admin/teams', data);
    }

    /**
     * Update team
     */
    updateTeam(teamId, data) {
        return this.put(`/admin/teams/${teamId}`, data);
    }

    /**
     * Delete team
     */
    deleteTeam(teamId) {
        return this.delete(`/admin/teams/${teamId}`);
    }

    /**
     * Get all budgets
     */
    getBudgets() {
        return this.get('/admin/budgets');
    }

    /**
     * Create budget
     */
    createBudget(data) {
        return this.post('/admin/budgets', data);
    }

    /**
     * Update budget
     */
    updateBudget(budgetId, data) {
        return this.put(`/admin/budgets/${budgetId}`, data);
    }

    /**
     * Delete budget
     */
    deleteBudget(budgetId) {
        return this.delete(`/admin/budgets/${budgetId}`);
    }

    /**
     * Get alerts
     */
    getAlerts() {
        return this.get('/admin/alerts');
    }

    /**
     * Update admin settings
     */
    saveSettings(data) {
        return this.post('/admin/settings', data);
    }

    // =========================================
    // ANALYTICS ENDPOINTS
    // =========================================

    /**
     * Get analytics data with filters
     */
    getAnalytics(filters = {}) {
        return this.get('/analytics/data', filters);
    }

    /**
     * Export analytics data
     */
    exportAnalytics(format, filters = {}) {
        const query = new URLSearchParams({
            format,
            ...filters
        }).toString();
        return `${this.baseURL}/analytics/export?${query}`;
    }

    // =========================================
    // DASHBOARD ENDPOINTS
    // =========================================

    /**
     * Get dashboard data
     */
    getDashboard() {
        return this.get('/dashboard/realtime');
    }

    /**
     * Get team costs
     */
    getTeamCosts(filters = {}) {
        return this.get('/dashboard/costs', filters);
    }

    /**
     * Get recent activity
     */
    getActivity(limit = 20) {
        return this.get('/dashboard/activity', { limit });
    }

    // =========================================
    // USER ENDPOINTS
    // =========================================

    /**
     * Get user profile
     */
    getUserProfile() {
        return this.get('/users/profile');
    }

    /**
     * Update user profile
     */
    updateUserProfile(data) {
        return this.put('/users/profile', data);
    }

    /**
     * Get user settings
     */
    getUserSettings() {
        return this.get('/users/settings');
    }

    /**
     * Update user settings
     */
    updateUserSettings(data) {
        return this.put('/users/settings', data);
    }

    // =========================================
    // AUTH ENDPOINTS
    // =========================================

    /**
     * Login
     */
    login(email, password) {
        return this.post('/auth/login', { email, password });
    }

    /**
     * Logout
     */
    logout() {
        this.setApiKey(null);
        return this.post('/auth/logout');
    }

    /**
     * Register
     */
    register(email, password, name) {
        return this.post('/auth/register', { email, password, name });
    }

    /**
     * Refresh token
     */
    refreshToken() {
        return this.post('/auth/refresh');
    }

    // =========================================
    // ERROR HANDLING
    // =========================================

    /**
     * Handle API errors
     */
    handleError(error) {
        if (error.response) {
            // Server responded with error status
            const status = error.response.status;
            const message = error.response.data?.message || 'API Error';
            
            if (status === 401) {
                this.setApiKey(null);
                window.location.href = '/login';
            }
            
            throw new Error(message);
        } else if (error.request) {
            // Request made but no response
            throw new Error('No response from server');
        } else {
            // Error in request setup
            throw new Error(error.message);
        }
    }
}

// Create global instance
const api = new APIClient('/api');

// Export for use
if (typeof module !== 'undefined' && module.exports) {
    module.exports = APIClient;
}
