/* ===============================
   EcoPackAI – Main Application JS
   =============================== */

// Global configuration
const CONFIG = {
    API_BASE_URL: window.location.origin + '/api',
    TOKEN_KEY: 'ecopackai_token',
    USER_KEY: 'ecopackai_user'
};

// Auth management
class AuthManager {
    static getToken() {
        return localStorage.getItem(CONFIG.TOKEN_KEY);
    }

    static setToken(token) {
        localStorage.setItem(CONFIG.TOKEN_KEY, token);
    }

    static getUser() {
        const user = localStorage.getItem(CONFIG.USER_KEY);
        return user ? JSON.parse(user) : null;
    }

    static setUser(user) {
        localStorage.setItem(CONFIG.USER_KEY, JSON.stringify(user));
    }

    static isAuthenticated() {
        return !!this.getToken();
    }

    static clear() {
        localStorage.removeItem(CONFIG.TOKEN_KEY);
        localStorage.removeItem(CONFIG.USER_KEY);
        localStorage.removeItem('currentRecommendations');
    }

    static async checkAuth() {
        if (!this.isAuthenticated()) {
            window.location.href = '/login';
            return false;
        }

        try {
            await this.fetchProfile();
            return true;
        } catch (error) {
            this.clear();
            window.location.href = '/login';
            return false;
        }
    }

    static async fetchProfile() {
        const token = this.getToken();
        if (!token) throw new Error('No token');

        const response = await fetch('/api/auth/profile', {
            headers: { 'Authorization': `Bearer ${token}` }
        });

        if (!response.ok) {
            if (response.status === 401) {
                this.clear();
                throw new Error('Session expired');
            }
            throw new Error('Failed to fetch profile');
        }

        const user = await response.json();
        this.setUser(user);
        return user;
    }
}

// API service
class APIService {
    static async request(endpoint, options = {}) {
        const token = AuthManager.getToken();
        const url = `${CONFIG.API_BASE_URL}${endpoint}`;

        const headers = {
            'Content-Type': 'application/json',
            ...(token ? { 'Authorization': `Bearer ${token}` } : {}),
            ...options.headers
        };

        const controller = new AbortController();
        const timeout = setTimeout(() => controller.abort(), 30000);

        try {
            const response = await fetch(url, {
                ...options,
                headers,
                signal: controller.signal
            });

            clearTimeout(timeout);

            if (response.status === 401) {
                AuthManager.clear();
                window.location.href = '/login';
                throw new Error('Session expired');
            }

            if (!response.ok) {
                const errorText = await response.text();
                throw new Error(`API Error ${response.status}: ${errorText}`);
            }

            return await response.json();
        } catch (error) {
            if (error.name === 'AbortError') {
                throw new Error('Request timeout. Please try again.');
            }
            throw error;
        }
    }

    static async get(endpoint) {
        return this.request(endpoint, { method: 'GET' });
    }

    static async post(endpoint, data) {
        return this.request(endpoint, {
            method: 'POST',
            body: JSON.stringify(data)
        });
    }

    static async put(endpoint, data) {
        return this.request(endpoint, {
            method: 'PUT',
            body: JSON.stringify(data)
        });
    }

    static async delete(endpoint) {
        return this.request(endpoint, { method: 'DELETE' });
    }
}

// Analytics service
class AnalyticsService {
    static async getDashboard() {
        return APIService.get('/analytics/dashboard');
    }

    static async getMaterialInsights() {
        return APIService.get('/analytics/insights/materials');
    }

    static async exportReport(format) {
        const token = AuthManager.getToken();
        const url = `/api/analytics/export/${format}`;

        const response = await fetch(url, {
            headers: { 'Authorization': `Bearer ${token}` }
        });

        if (!response.ok) {
            throw new Error('Export failed');
        }

        const blob = await response.blob();
        const filename = `EcoPackAI_Report_${new Date().toISOString().split('T')[0]}.${format}`;

        // Download file
        const urlObj = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = urlObj;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        window.URL.revokeObjectURL(urlObj);
    }
}

// Recommendations service
class RecommendationService {
    static async analyzeProduct(productData) {
        return APIService.post('/recommendations/recommend', productData);
    }

    static async getHistory() {
        return APIService.get('/recommendations/history');
    }

    static async getMaterials() {
        return APIService.get('/recommendations/materials');
    }

    static async saveRecommendation(productId, materialId) {
        return APIService.post('/recommendations/save', {
            product_id: productId,
            material_id: materialId
        });
    }
}

// UI components
class UIComponents {
    static showLoading(selector = 'body') {
        const container = document.querySelector(selector);
        if (container) {
            container.innerHTML = `
                <div class="spinner-container">
                    <div class="spinner-border text-success" role="status">
                        <span class="visually-hidden">Loading...</span>
                    </div>
                </div>
            `;
        }
    }

    static showError(message, selector = 'body') {
        const container = document.querySelector(selector);
        if (container) {
            container.innerHTML = `
                <div class="alert alert-danger" role="alert">
                    <i class="fas fa-exclamation-circle me-2"></i>
                    ${message}
                </div>
            `;
        }
    }

    static showSuccess(message, selector = 'body') {
        const container = document.querySelector(selector);
        if (container) {
            const alert = document.createElement('div');
            alert.className = 'alert alert-success alert-dismissible fade show';
            alert.innerHTML = `
                <i class="fas fa-check-circle me-2"></i>
                ${message}
                <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
            `;
            container.prepend(alert);

            setTimeout(() => {
                if (alert.parentNode) {
                    alert.remove();
                }
            }, 5000);
        }
    }

    static formatPercentage(value) {
        return `${parseFloat(value).toFixed(1)}%`;
    }

    static formatNumber(value) {
        return new Intl.NumberFormat().format(value);
    }

    static formatDate(dateString) {
        const date = new Date(dateString);
        return date.toLocaleDateString('en-US', {
            year: 'numeric',
            month: 'short',
            day: 'numeric'
        });
    }

    static createProgressBar(value, max = 100) {
        const percentage = (value / max) * 100;
        return `
            <div class="progress" style="height: 10px;">
                <div class="progress-bar" role="progressbar" 
                     style="width: ${percentage}%" 
                     aria-valuenow="${value}" 
                     aria-valuemin="0" 
                     aria-valuemax="${max}">
                </div>
            </div>
            <small class="text-muted">${value.toFixed(1)}%</small>
        `;
    }
}

// Dashboard manager
class DashboardManager {
    static async load() {
        try {
            if (!AuthManager.isAuthenticated()) {
                return;
            }

            // Update date
            this.updateDate();

            const data = await AnalyticsService.getDashboard();

            // Update metrics
            if (data && data.metrics) {
                this.updateMetrics(data.metrics);
            }

            // Render charts
            if (data.charts && Object.keys(data.charts).length > 0) {
                this.renderCharts(data.charts);
            } else {
                this.renderEmptyCharts();
            }

            // Render recent activity
            if (data.recent_recommendations) {
                this.renderActivities(data.recent_recommendations);
            }

            // Update username
            const user = AuthManager.getUser();
            if (user && document.getElementById('username')) {
                document.getElementById('username').textContent = user.username;
            }

        } catch (error) {
            console.error('Dashboard load error:', error);
            UIComponents.showError('Failed to load dashboard data. Please try refreshing.', '#dashboardContent');
            this.renderEmptyCharts(); // Fallback
        }
    }

    static updateDate() {
        const dateElement = document.getElementById('currentDate');
        if (dateElement) {
            const currentDate = new Date();
            const options = { year: 'numeric', month: 'long', day: 'numeric' };
            dateElement.textContent = currentDate.toLocaleDateString('en-US', options);
        }
    }

    static updateMetrics(metrics) {
        const elements = {
            'totalRecs': document.getElementById('totalRecs'),
            'avgCO2': document.getElementById('avgCO2'),
            'avgCost': document.getElementById('avgCost'),
            'topMaterial': document.getElementById('topMaterial'),
            'co2Reduced': document.getElementById('co2Reduced'),
            'costSaved': document.getElementById('costSaved'),
            'ecoScore': document.getElementById('ecoScore')
        };

        for (const [id, element] of Object.entries(elements)) {
            if (element) {
                switch (id) {
                    case 'totalRecs':
                        element.textContent = metrics.total_recommendations || 0;
                        break;
                    case 'avgCO2':
                    case 'co2Reduced':
                        element.textContent = UIComponents.formatPercentage(metrics.avg_co2_reduction || 0);
                        break;
                    case 'avgCost':
                    case 'costSaved':
                        element.textContent = UIComponents.formatPercentage(metrics.avg_cost_savings || 0);
                        break;
                    case 'topMaterial':
                        element.textContent = metrics.top_material || 'None';
                        break;
                    case 'ecoScore':
                        element.textContent = metrics.avg_eco_score ? metrics.avg_eco_score.toFixed(2) : '0';
                        break;
                }
            }
        }
    }

    static renderCharts(charts) {
        // CO2 Trend Chart
        if (charts.trend_chart && document.getElementById('co2Chart')) {
            const container = document.getElementById('co2Chart');
            container.innerHTML = ''; // Clear loading spinner

            const layout = charts.trend_chart.layout;
            layout.xaxis = { ...layout.xaxis, type: 'category' };

            Plotly.newPlot(container,
                charts.trend_chart.data,
                layout,
                { responsive: true, displayModeBar: true }
            );
        }

        // Material Usage Chart
        if (charts.material_chart && document.getElementById('materialChart')) {
            const container = document.getElementById('materialChart');
            container.innerHTML = ''; // Clear loading spinner
            Plotly.newPlot(container,
                charts.material_chart.data,
                charts.material_chart.layout,
                { responsive: true, displayModeBar: false }
            );
        }

        // Score Distribution Chart
        const scoreChartContainer = document.getElementById('scoreChart') || document.getElementById('costChart');
        if (charts.score_chart && scoreChartContainer) {
            scoreChartContainer.innerHTML = ''; // Clear loading spinner
            Plotly.newPlot(scoreChartContainer,
                charts.score_chart.data,
                charts.score_chart.layout,
                { responsive: true, displayModeBar: true }
            );
        }
    }

    static renderActivities(activities) {
        const container = document.getElementById('recentActivity');
        if (!container) return;

        if (activities.length === 0) {
            container.innerHTML = `
                <div class="empty-state">
                    <div class="empty-icon"><i class="fas fa-history"></i></div>
                    <p>No recent activity</p>
                </div>
            `;
            return;
        }

        container.innerHTML = activities.map(act => `
            <div class="activity-item d-flex gap-3 mb-3 pb-3 border-bottom">
                <div class="activity-icon bg-success bg-opacity-10 text-success p-2 rounded">
                    <i class="fas fa-leaf"></i>
                </div>
                <div class="activity-content">
                    <div class="activity-title d-flex justify-content-between">
                        <span>${act.product}</span>
                        <small class="text-success fw-bold">${(act.score * 10).toFixed(1)}</small>
                    </div>
                    <div class="activity-subtitle text-muted small">${act.material}</div>
                    <div class="activity-time mt-1">
                        <i class="far fa-clock me-1"></i>${new Date(act.date).toLocaleDateString()}
                    </div>
                </div>
            </div>
        `).join('');
    }

    static startAutoRefresh() {
        // Clear existing interval if any
        if (this.refreshInterval) {
            clearInterval(this.refreshInterval);
        }

        // Refresh every 30 seconds
        this.refreshInterval = setInterval(async () => {
            console.log('Refreshing dashboard data...');
            await this.load();
            if (window.location.pathname === '/analytics' || window.location.pathname === '/dashboard') {
                await MaterialInsightsManager.load();
            }
        }, 30000);
    }

    static renderEmptyCharts() {
        const emptyConfig = {
            data: [{
                x: [],
                y: [],
                type: 'scatter',
                mode: 'lines',
                line: { color: '#198754' }
            }],
            layout: {
                title: 'No Data Available',
                plot_bgcolor: 'rgba(240, 248, 255, 0.8)',
                paper_bgcolor: 'rgba(255, 255, 255, 0.9)',
                xaxis: { title: 'Date' },
                yaxis: { title: 'Value' },
                annotations: [{
                    text: 'No data yet',
                    xref: 'paper',
                    yref: 'paper',
                    x: 0.5,
                    y: 0.5,
                    showarrow: false,
                    font: { size: 14, color: '#6c757d' }
                }]
            }
        };

        ['co2Chart', 'materialChart', 'scoreChart', 'costChart'].forEach(id => {
            const element = document.getElementById(id);
            if (element) {
                try {
                    element.innerHTML = '';
                    Plotly.newPlot(element, emptyConfig.data, emptyConfig.layout);
                } catch (e) { console.warn('Plotly error:', e); }
            }
        });
    }
}

// Material insights manager
class MaterialInsightsManager {
    static async load() {
        try {
            const container = document.getElementById('insightsContainer');
            if (!container) return;

            container.innerHTML = `
                <div class="col-12 text-center py-4">
                    <div class="spinner-border text-success"></div>
                    <p class="mt-2 text-muted">Loading insights...</p>
                </div>
            `;

            const data = await AnalyticsService.getMaterialInsights();

            if (!data.insights || data.insights.length === 0) {
                container.innerHTML = `
                    <div class="col-12 text-center py-4">
                        <p class="text-muted">No material insights available yet.</p>
                        <a href="/product-input" class="btn btn-sm btn-success">
                            Analyze First Product
                        </a>
                    </div>
                `;
                return;
            }

            const insights = data.insights.slice(0, 6); // Show top 6

            container.innerHTML = insights.map((insight, index) => `
                <div class="col-md-4 mb-3 slide-up" style="animation-delay: ${index * 0.1}s">
                    <div class="card h-100">
                        <div class="card-body">
                            <div class="d-flex justify-content-between align-items-start mb-2">
                                <h6 class="fw-bold mb-0">${insight.material}</h6>
                                <span class="badge bg-success">${insight.usage_count} uses</span>
                            </div>
                            
                            <div class="mb-3">
                                <small class="text-muted d-block mb-1">CO₂ Reduction</small>
                                ${UIComponents.createProgressBar(insight.avg_co2_reduction)}
                            </div>
                            
                            <div class="mb-3">
                                <small class="text-muted d-block mb-1">Cost Savings</small>
                                ${UIComponents.createProgressBar(insight.avg_cost_savings)}
                            </div>
                            
                            <div class="d-flex justify-content-between align-items-center">
                                <small class="text-muted">Avg Score</small>
                                <span class="fw-bold">${insight.avg_score.toFixed(2)}</span>
                            </div>
                            
                            <div class="mt-3 d-flex justify-content-between small">
                                <span title="Recyclability">
                                    <i class="fas fa-recycle text-primary"></i> ${insight.recyclability}%
                                </span>
                                <span title="Strength">
                                    <i class="fas fa-shield-alt text-warning"></i> ${insight.strength}/10
                                </span>
                                <span title="Cost">
                                    <i class="fas fa-coins text-success"></i> ₹${insight.cost_per_kg}
                                </span>
                            </div>
                        </div>
                    </div>
                </div>
            `).join('');

        } catch (error) {
            console.error('Material insights error:', error);
            const container = document.getElementById('insightsContainer');
            if (container) {
                container.innerHTML = `
                    <div class="col-12 text-center py-4">
                        <div class="alert alert-warning">
                            Failed to load material insights. Please try again.
                        </div>
                    </div>
                `;
            }
        }
    }
}

// Product analysis manager
class ProductAnalysisManager {
    static async analyze(formData) {
        try {
            const result = await RecommendationService.analyzeProduct(formData);

            // Save recommendations for display
            if (result.recommendations) {
                localStorage.setItem('currentRecommendations', JSON.stringify({
                    product_id: result.product_id,
                    product: result.product_name,
                    recommendations: result.recommendations,
                    timestamp: new Date().toISOString()
                }));
            }

            return result;
        } catch (error) {
            console.error('Product analysis error:', error);
            throw error;
        }
    }

    static loadRecommendations() {
        try {
            const container = document.getElementById('recommendationsContainer');
            if (!container) return;

            const rawData = localStorage.getItem('currentRecommendations');
            if (!rawData) {
                container.innerHTML = `
                    <div class="col-12 text-center py-5">
                        <h4 class="text-muted mb-3">No recommendations found</h4>
                        <a href="/product-input" class="btn btn-success">
                            <i class="fas fa-plus me-2"></i>Start New Analysis
                        </a>
                    </div>
                `;
                return;
            }

            const data = JSON.parse(rawData);
            const recommendations = data.recommendations || [];
            const productName = data.product || 'Your Product';
            const productId = data.product_id;

            // Update product name
            const productTitle = document.getElementById('productTitle');
            if (productTitle) {
                productTitle.textContent = `Recommendations for: ${productName}`;
            }

            // Render recommendations
            container.innerHTML = recommendations.map((rec, index) => {
                const rank = index + 1;
                let rankClass = 'bg-secondary';
                let rankText = `#${rank}`;

                if (rank === 1) {
                    rankClass = 'bg-warning text-dark';
                    rankText = '🥇 Best';
                } else if (rank === 2) {
                    rankClass = 'bg-light text-dark';
                    rankText = '🥈 Runner-up';
                } else if (rank === 3) {
                    rankClass = 'bg-info text-white';
                    rankText = '🥉 3rd';
                }

                return `
                    <div class="col-md-6 col-lg-4 mb-4 slide-up" style="animation-delay: ${index * 0.1}s">
                        <div class="card h-100">
                            <div class="card-body">
                                <div class="d-flex justify-content-between align-items-start mb-3">
                                    <span class="badge ${rankClass}">${rankText}</span>
                                    <span class="fw-bold text-success fs-5">${(rec.score * 10).toFixed(1)}/10</span>
                                </div>
                                
                                <h5 class="card-title mb-3">${rec.material_name}</h5>
                                
                                <div class="mb-3">
                                    <div class="d-flex justify-content-between mb-1">
                                        <small class="text-muted">CO₂ Reduction</small>
                                        <small class="fw-bold text-success">${rec.co2_reduction_percent}%</small>
                                    </div>
                                    ${UIComponents.createProgressBar(rec.co2_reduction_percent)}
                                </div>
                                
                                <div class="mb-3">
                                    <div class="d-flex justify-content-between mb-1">
                                        <small class="text-muted">Cost Savings</small>
                                        <small class="fw-bold text-primary">${rec.cost_savings_percent}%</small>
                                    </div>
                                    ${UIComponents.createProgressBar(rec.cost_savings_percent)}
                                </div>
                                
                                <div class="row g-2 mt-4">
                                    <div class="col-6">
                                        <div class="text-center p-2 bg-light rounded">
                                            <small class="text-muted d-block">Recyclability</small>
                                            <strong>${rec.recyclability}%</strong>
                                        </div>
                                    </div>
                                    <div class="col-6">
                                        <div class="text-center p-2 bg-light rounded">
                                            <small class="text-muted d-block">Strength</small>
                                            <strong>${rec.strength}/10</strong>
                                        </div>
                                    </div>
                                    <div class="col-6">
                                        <div class="text-center p-2 bg-light rounded">
                                            <small class="text-muted d-block">Cost</small>
                                            <strong>₹${rec.cost_per_kg}/kg</strong>
                                        </div>
                                    </div>
                                    <div class="col-6">
                                        <div class="text-center p-2 bg-light rounded">
                                            <small class="text-muted d-block">Biodegradable</small>
                                            <strong>${rec.biodegradability}/10</strong>
                                        </div>
                                    </div>
                                </div>
                                
                                <button class="btn btn-success w-100 mt-3" 
                                        onclick="window.selectMaterial(${rec.material_id}, ${productId})">
                                    <i class="fas fa-save me-2"></i>Save This Analysis
                                </button>
                            </div>
                        </div>
                    </div>
                `;
            }).join('');

        } catch (error) {
            console.error('Load recommendations error:', error);
            const container = document.getElementById('recommendationsContainer');
            if (container) {
                container.innerHTML = `
                    <div class="col-12">
                        <div class="alert alert-danger">
                            <i class="fas fa-exclamation-triangle me-2"></i>
                            Failed to load recommendations. Please try again.
                        </div>
                    </div>
                `;
            }
        }
    }
}

// Initialize application
document.addEventListener('DOMContentLoaded', async function () {
    // Add fade-in animation to body
    document.body.classList.add('fade-in');

    // Check authentication for protected pages
    const protectedPages = ['/dashboard', '/product-input', '/recommendations', '/analytics', '/report'];
    const currentPath = window.location.pathname;

    if (protectedPages.includes(currentPath)) {
        const isAuthenticated = await AuthManager.checkAuth();
        if (!isAuthenticated) {
            return;
        }
    }

    // Check for Plotly
    if (typeof Plotly === 'undefined') {
        console.error('Plotly.js is not loaded');
        UIComponents.showError('Chart library failed to load. Please check your internet connection.', '#dashboardContent');
    }

    // Normalized path check
    const normalizedPath = currentPath.replace(/\/$/, '') || '/';

    // Page-specific initialization
    switch (normalizedPath) {
        case '/':
        case '/dashboard':
            await DashboardManager.load();
            DashboardManager.startAutoRefresh();
            await MaterialInsightsManager.load();
            break;

        case '/analytics':
            await DashboardManager.load();
            DashboardManager.startAutoRefresh();
            await MaterialInsightsManager.load();
            break;

        case '/recommendations':
            ProductAnalysisManager.loadRecommendations();
            break;

        case '/product-input':
            // Product input page has its own JS
            break;

        case '/report':
            // Report page has data-export buttons handled by global listener
            break;
    }

    // Initialize global export buttons (for both analytics and report pages)
    setupExportButtons();

    // Global event listeners
    setupGlobalListeners();
});

// Setup export buttons
function setupExportButtons() {
    document.querySelectorAll('[onclick^="EcoPackAI.AnalyticsService.exportReport"]').forEach(btn => {
        // Already handled by inline onclick, but we can add more robust listeners if needed
    });
}

// Global event listeners
function setupGlobalListeners() {
    // Logout button
    const logoutBtn = document.querySelector('[data-logout]');
    if (logoutBtn) {
        logoutBtn.addEventListener('click', function (e) {
            e.preventDefault();
            AuthManager.clear();
            window.location.href = '/login';
        });
    }

    // Export buttons
    document.querySelectorAll('[data-export]').forEach(btn => {
        btn.addEventListener('click', async function () {
            const format = this.dataset.export;
            try {
                await AnalyticsService.exportReport(format);
                UIComponents.showSuccess(`Report exported successfully as ${format.toUpperCase()}!`);
            } catch (error) {
                UIComponents.showError('Failed to export report. Please try again.');
            }
        });
    });
}

// Global functions (available in templates)
window.selectMaterial = async function (materialId, productId) {
    if (!productId) {
        UIComponents.showError('Product ID missing. Please redo analysis.');
        return;
    }

    try {
        const btn = event.currentTarget;
        const originalHtml = btn.innerHTML;
        btn.disabled = true;
        btn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Saving...';

        const response = await window.EcoPackAI.RecommendationService.saveRecommendation(productId, materialId);
        UIComponents.showSuccess(response.message || 'Analysis saved successfully!');

        btn.innerHTML = '<i class="fas fa-check me-2"></i>Saved';
        btn.classList.remove('btn-success');
        btn.classList.add('btn-outline-secondary');
    } catch (error) {
        console.error('Save error:', error);
        UIComponents.showError('Failed to save analysis. Please try again.');
    }
};

window.exportReport = async function (format) {
    try {
        await AnalyticsService.exportReport(format);
        UIComponents.showSuccess(`Report exported as ${format.toUpperCase()}`);
    } catch (error) {
        UIComponents.showError('Export failed. Please try again.');
    }
};

window.logout = function () {
    AuthManager.clear();
    window.location.href = '/login';
};

// Make services available globally
window.EcoPackAI = {
    AuthManager,
    APIService,
    AnalyticsService,
    RecommendationService,
    DashboardManager,
    MaterialInsightsManager,
    ProductAnalysisManager,
    UIComponents
};