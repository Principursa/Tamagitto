// Tamagitto Extension Popup - Main Interface Controller
console.log("🐾 Tamagitto Extension Loaded");

class TamagittoExtension {
    constructor() {
        this.apiBaseUrl = 'https://tamagitto.xyz/api';
        this.isAuthenticated = false;
        this.currentUser = null;
        this.currentEntity = null;
        this.repositories = [];
        this.websocket = null;
        this.initialized = false;

        // Initialize when DOM loads
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', () => this.init());
        } else {
            this.init();
        }
    }

    async init() {
        if (this.initialized) {
            console.log("⚠️ Extension already initialized");
            return;
        }

        console.log("🚀 Initializing Tamagitto Extension");
        this.initialized = true;

        try {
            // Check authentication status
            console.log("🔐 Checking authentication status...");
            await this.checkAuthStatus();
            console.log("✅ Auth check complete");

            // Set up event listeners
            console.log("🎧 Setting up event listeners...");
            this.setupEventListeners();
            console.log("✅ Event listeners ready");

            // Set up real-time updates from background service
            console.log("⚡ Setting up real-time updates...");
            this.setupRealtimeUpdates();
            console.log("✅ Real-time updates ready");

            // Initialize the appropriate screen
            console.log("🖥️ Initializing screen...");
            if (this.isAuthenticated) {
                console.log("👤 User authenticated, loading data...");
                await this.loadUserData();
                this.showScreen('entity-screen');
                console.log("✅ Entity screen displayed");
            } else {
                console.log("🔑 User not authenticated, showing auth screen...");
                this.showScreen('auth-screen');
                console.log("✅ Auth screen displayed");
            }
        } catch (error) {
            console.error("❌ Initialization error:", error);
            this.showError("Failed to initialize extension. Please try again.");
        }
    }

    async checkAuthStatus() {
        try {
            const stored = await chrome.storage.local.get(['tamagitto_token', 'tamagitto_user']);

            if (stored.tamagitto_token) {
                // Verify token with backend
                const response = await this.apiCall('/auth/me', 'GET', null, stored.tamagitto_token);

                if (response.ok) {
                    this.isAuthenticated = true;
                    this.currentUser = await response.json();
                    console.log("✅ User authenticated:", this.currentUser.username);
                } else {
                    // Token invalid, clear storage
                    await chrome.storage.local.remove(['tamagitto_token', 'tamagitto_user']);
                }
            }
        } catch (error) {
            console.error("❌ Auth check failed:", error);
        }
    }

    async loadUserData() {
        try {
            this.showLoading("Loading your code pets...");

            // Get user's entities
            const entitiesResponse = await this.authenticatedApiCall('/entities');
            if (entitiesResponse.ok) {
                const entitiesData = await entitiesResponse.json();

                if (entitiesData.entities && entitiesData.entities.length > 0) {
                    this.currentEntity = entitiesData.entities[0]; // Show first entity
                    this.updateEntityDisplay();
                } else {
                    // No entities, show repo selection
                    await this.loadRepositories();
                    this.showScreen('repo-selection-screen');
                }
            }

            // Load repositories
            await this.loadRepositories();

            this.hideLoading();

        } catch (error) {
            console.error("❌ Failed to load user data:", error);
            this.showError("Failed to load your data. Please try again.");
        }
    }

    async loadRepositories() {
        try {
            const response = await this.authenticatedApiCall('/repositories/github');
            if (response.ok) {
                const data = await response.json();
                this.repositories = data.repositories || [];
                this.updateRepositoryList();
            }
        } catch (error) {
            console.error("❌ Failed to load repositories:", error);
        }
    }

    setupEventListeners() {
        // Authentication
        const loginBtn = document.getElementById('github-login-btn');
        if (loginBtn) {
            loginBtn.addEventListener('click', () => this.startGitHubAuth());
        }

        const logoutBtn = document.getElementById('logout-btn');
        if (logoutBtn) {
            logoutBtn.addEventListener('click', () => this.logout());
        }

        // Repository selection
        const repoSearch = document.getElementById('repo-search');
        if (repoSearch) {
            repoSearch.addEventListener('input', (e) => this.filterRepositories(e.target.value));
        }

        // Entity management
        const changeRepoBtn = document.getElementById('change-repo-btn');
        if (changeRepoBtn) {
            changeRepoBtn.addEventListener('click', () => this.showScreen('repo-selection-screen'));
        }

        const viewHistoryBtn = document.getElementById('view-history-btn');
        if (viewHistoryBtn) {
            viewHistoryBtn.addEventListener('click', () => this.viewHealthHistory());
        }

        // Settings and info
        const settingsBtn = document.getElementById('settings-btn');
        if (settingsBtn) {
            settingsBtn.addEventListener('click', () => this.showSettings());
        }

        const infoBtn = document.getElementById('info-btn');
        if (infoBtn) {
            infoBtn.addEventListener('click', () => this.showInfo());
        }

        // Error handling
        const errorClose = document.getElementById('error-close');
        if (errorClose) {
            errorClose.addEventListener('click', () => this.hideError());
        }
    }

    async startGitHubAuth() {
        try {
            this.showLoading("Connecting to GitHub...");

            // Get GitHub auth URL from backend
            const response = await this.apiCall('/auth/github');
            if (response.ok) {
                const data = await response.json();

                // Open GitHub OAuth in new tab
                chrome.tabs.create({ url: data.auth_url }, (tab) => {
                    // Listen for tab updates to catch the callback
                    this.listenForAuthCallback(tab.id);
                });
            } else {
                throw new Error('Failed to get GitHub auth URL');
            }
        } catch (error) {
            console.error("❌ GitHub auth failed:", error);
            this.showError("Failed to connect to GitHub. Please try again.");
            this.hideLoading();
        }
    }

    listenForAuthCallback(tabId) {
        const listener = (id, changeInfo, tab) => {
            if (id === tabId && changeInfo.url && changeInfo.url.includes('tamagitto.xyz/api/auth/github/callback')) {
                // Auth callback reached - now we need to extract the auth data from the page
                chrome.tabs.onUpdated.removeListener(listener);

                // Execute script to get auth data from the page
                chrome.scripting.executeScript({
                    target: { tabId: tabId },
                    function: () => {
                        return window.tamagittoAuth || null;
                    }
                }, (results) => {
                    if (results && results[0] && results[0].result) {
                        const authData = results[0].result;
                        chrome.tabs.remove(tabId);
                        this.handleSuccessfulAuth(authData);
                    } else {
                        // Fallback - try again in 1 second
                        setTimeout(() => {
                            chrome.scripting.executeScript({
                                target: { tabId: tabId },
                                function: () => window.tamagittoAuth || null
                            }, (results) => {
                                if (results && results[0] && results[0].result) {
                                    const authData = results[0].result;
                                    chrome.tabs.remove(tabId);
                                    this.handleSuccessfulAuth(authData);
                                } else {
                                    chrome.tabs.remove(tabId);
                                    this.showError("Authentication failed. Please try again.");
                                    this.hideLoading();
                                }
                            });
                        }, 1000);
                    }
                });
            }
        };

        chrome.tabs.onUpdated.addListener(listener);
    }

    async handleSuccessfulAuth(authData) {
        try {
            this.showLoading("Completing authentication...");

            // Store auth data
            await chrome.storage.local.set({
                tamagitto_token: authData.access_token,
                tamagitto_user: authData.user
            });

            this.isAuthenticated = true;
            this.currentUser = authData.user;

            console.log("✅ Authentication successful!", authData.user.username);

            // Notify background service
            chrome.runtime.sendMessage({
                action: 'authenticate',
                data: { user: authData.user }
            });

            await this.loadUserData();

        } catch (error) {
            console.error("❌ Auth completion failed:", error);
            this.showError("Authentication failed. Please try again.");
        } finally {
            this.hideLoading();
        }
    }

    // Keep this method for backward compatibility, but it's no longer used
    async completeGitHubAuth(code) {
        console.log("⚠️ Legacy auth method called - this shouldn't happen with the new flow");
    }

    async logout() {
        try {
            // Clear storage
            await chrome.storage.local.remove(['tamagitto_token', 'tamagitto_user']);

            // Reset state
            this.isAuthenticated = false;
            this.currentUser = null;
            this.currentEntity = null;
            this.repositories = [];

            // Close websocket
            if (this.websocket) {
                this.websocket.close();
                this.websocket = null;
            }

            // Show auth screen
            this.showScreen('auth-screen');

        } catch (error) {
            console.error("❌ Logout failed:", error);
        }
    }

    async createEntityForRepo(repoId, repoName) {
        try {
            this.showLoading("Creating your code pet...");

            const response = await this.authenticatedApiCall(`/repositories/${repoId}/entity`, 'POST', {
                entity_type: 'pet', // Default to pet
                name: `${repoName.split('/')[1]} Buddy`
            });

            if (response.ok) {
                const data = await response.json();
                this.currentEntity = data.entity;

                // Enable monitoring
                const monitorResponse = await this.authenticatedApiCall(
                    `/repositories/${repoId}/monitoring/enable`,
                    'POST',
                    { enable_webhook: true }
                );

                if (monitorResponse.ok) {
                    console.log("✅ Monitoring enabled for repository");
                }

                this.updateEntityDisplay();
                this.showScreen('entity-screen');

            } else {
                throw new Error('Failed to create entity');
            }
        } catch (error) {
            console.error("❌ Entity creation failed:", error);
            this.showError("Failed to create your code pet. Please try again.");
        } finally {
            this.hideLoading();
        }
    }

    updateEntityDisplay() {
        if (!this.currentEntity) return;

        // Update entity name
        const nameEl = document.getElementById('entity-name');
        if (nameEl) nameEl.textContent = this.currentEntity.name;

        // Update health bar
        const healthFill = document.getElementById('health-fill');
        const healthScore = document.getElementById('health-score');
        if (healthFill && healthScore) {
            const healthPercent = Math.max(0, Math.min(100, this.currentEntity.health_score));
            healthFill.style.width = `${healthPercent}%`;
            healthScore.textContent = Math.round(healthPercent);

            // Update health bar color
            healthFill.className = `health-fill ${this.getHealthClass(healthPercent)}`;
        }

        // Update status
        const statusEl = document.getElementById('entity-status');
        if (statusEl) {
            statusEl.textContent = this.currentEntity.status;
            statusEl.className = `status-badge ${this.currentEntity.status}`;
        }

        // Update repository name
        const repoNameEl = document.getElementById('repo-name');
        if (repoNameEl && this.currentEntity.repository) {
            repoNameEl.textContent = this.currentEntity.repository.full_name;
        }

        // Update entity image
        const entityImage = document.getElementById('entity-image');
        if (entityImage) {
            entityImage.src = this.currentEntity.visual_url || 'icons/default-entity.png';
        }

        // Load recent activity
        this.loadRecentActivity();
    }

    async loadRecentActivity() {
        try {
            if (!this.currentEntity) return;

            const response = await this.authenticatedApiCall(`/entities/${this.currentEntity.id}/history?limit=5`);
            if (response.ok) {
                const data = await response.json();
                this.updateActivityList(data.history);
            }
        } catch (error) {
            console.error("❌ Failed to load activity:", error);
        }
    }

    updateActivityList(activities) {
        const activityList = document.getElementById('activity-list');
        if (!activityList) return;

        if (!activities || activities.length === 0) {
            activityList.innerHTML = '<div class="activity-item">No recent activity</div>';
            return;
        }

        activityList.innerHTML = activities.map(activity => `
            <div class="activity-item">
                <div class="activity-icon ${activity.health_score > (activity.previous_health || 0) ? 'positive' : 'negative'}">
                    ${activity.health_score > (activity.previous_health || 0) ? '📈' : '📉'}
                </div>
                <div class="activity-content">
                    <div class="activity-text">${activity.change_reason}</div>
                    <div class="activity-time">${this.formatTimeAgo(activity.created_at)}</div>
                </div>
                <div class="activity-change ${activity.health_score > (activity.previous_health || 0) ? 'positive' : 'negative'}">
                    ${activity.health_score > (activity.previous_health || 0) ? '+' : ''}${Math.round(activity.health_score - (activity.previous_health || 0))}
                </div>
            </div>
        `).join('');
    }

    updateRepositoryList() {
        const repoList = document.getElementById('repo-list');
        if (!repoList) return;

        if (this.repositories.length === 0) {
            repoList.innerHTML = '<div class="repo-item">No repositories found</div>';
            return;
        }

        repoList.innerHTML = this.repositories.map(repo => `
            <div class="repo-item" data-repo-id="${repo.id}">
                <div class="repo-info">
                    <div class="repo-name">${repo.full_name}</div>
                    <div class="repo-language">${repo.language || 'Unknown'}</div>
                </div>
                <div class="repo-actions">
                    <button class="select-repo-btn" data-repo-id="${repo.id}" data-repo-name="${repo.full_name}">
                        Select
                    </button>
                </div>
            </div>
        `).join('');

        // Add click listeners
        repoList.querySelectorAll('.select-repo-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const repoId = e.target.dataset.repoId;
                const repoName = e.target.dataset.repoName;
                this.createEntityForRepo(repoId, repoName);
            });
        });
    }

    filterRepositories(searchTerm) {
        const repoItems = document.querySelectorAll('.repo-item');
        repoItems.forEach(item => {
            const repoName = item.querySelector('.repo-name').textContent.toLowerCase();
            const matches = repoName.includes(searchTerm.toLowerCase());
            item.style.display = matches ? 'flex' : 'none';
        });
    }

    // Utility methods
    async apiCall(endpoint, method = 'GET', body = null, token = null) {
        const url = `${this.apiBaseUrl}${endpoint}`;
        const headers = {
            'Content-Type': 'application/json'
        };

        if (token) {
            headers.Authorization = `Bearer ${token}`;
        }

        const options = {
            method,
            headers
        };

        if (body && method !== 'GET') {
            options.body = JSON.stringify(body);
        }

        return fetch(url, options);
    }

    async authenticatedApiCall(endpoint, method = 'GET', body = null) {
        const stored = await chrome.storage.local.get(['tamagitto_token']);
        return this.apiCall(endpoint, method, body, stored.tamagitto_token);
    }

    showScreen(screenId) {
        console.log(`🖥️ Showing screen: ${screenId}`);

        // Hide all screens
        const allScreens = document.querySelectorAll('.screen');
        console.log(`Found ${allScreens.length} screens`);

        allScreens.forEach(screen => {
            screen.classList.add('hidden');
            console.log(`Hidden screen: ${screen.id}`);
        });

        // Show target screen
        const targetScreen = document.getElementById(screenId);
        if (targetScreen) {
            targetScreen.classList.remove('hidden');
            console.log(`✅ Displayed screen: ${screenId}`);
        } else {
            console.error(`❌ Screen not found: ${screenId}`);
        }

        // Also hide loading overlay to make sure it's not interfering
        this.hideLoading();
    }

    showLoading(message = "Loading...") {
        const overlay = document.getElementById('loading-overlay');
        const messageEl = document.getElementById('loading-message');

        if (overlay) {
            if (messageEl) messageEl.textContent = message;
            overlay.classList.remove('hidden');
        }
    }

    hideLoading() {
        const overlay = document.getElementById('loading-overlay');
        if (overlay) {
            overlay.classList.add('hidden');
            console.log("✅ Loading overlay hidden");
        } else {
            console.log("⚠️ Loading overlay not found");
        }
    }

    showError(message) {
        const container = document.getElementById('error-container');
        const messageEl = document.getElementById('error-message');

        if (container && messageEl) {
            messageEl.textContent = message;
            container.classList.remove('hidden');
        }
    }

    hideError() {
        const container = document.getElementById('error-container');
        if (container) {
            container.classList.add('hidden');
        }
    }

    getHealthClass(health) {
        if (health >= 80) return 'excellent';
        if (health >= 60) return 'good';
        if (health >= 40) return 'warning';
        if (health >= 20) return 'danger';
        return 'critical';
    }

    formatTimeAgo(dateString) {
        const date = new Date(dateString);
        const now = new Date();
        const diffMs = now - date;
        const diffMins = Math.floor(diffMs / 60000);

        if (diffMins < 1) return 'Just now';
        if (diffMins < 60) return `${diffMins}m ago`;

        const diffHours = Math.floor(diffMins / 60);
        if (diffHours < 24) return `${diffHours}h ago`;

        const diffDays = Math.floor(diffHours / 24);
        return `${diffDays}d ago`;
    }

    async viewHealthHistory() {
        // Open health history in new tab
        chrome.tabs.create({ url: `${this.apiBaseUrl.replace('/api', '')}/` });
    }

    showSettings() {
        // TODO: Implement settings panel
        console.log("Settings not implemented yet");
    }

    showInfo() {
        // TODO: Implement info panel
        console.log("Info panel not implemented yet");
    }

    setupRealtimeUpdates() {
        console.log("🔄 Setting up real-time updates...");

        // Listen for messages from background service
        chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
            switch (request.type) {
                case 'health_update':
                    this.handleHealthUpdate(request.data);
                    break;
                case 'entity_status_change':
                    this.handleStatusChange(request.data);
                    break;
                case 'new_commit_analyzed':
                    this.handleCommitAnalyzed(request.data);
                    break;
            }
        });

        // Skip initial health status request for now to avoid hanging
        console.log("✅ Real-time updates ready");

        // Set up periodic updates every 60 seconds (reduced frequency)
        this.updateInterval = setInterval(() => {
            if (this.isAuthenticated) {
                this.requestHealthUpdate();
            }
        }, 60000);
    }

    handleHealthUpdate(data) {
        if (!this.currentEntity || this.currentEntity.id !== data.entity_id) return;

        // Update current entity with new health data
        this.currentEntity.health_score = data.current_health;
        if (data.new_status) {
            this.currentEntity.status = data.new_status;
        }

        // Update the display
        this.updateEntityDisplay();

        // Show notification if health changed significantly
        if (data.health_change && Math.abs(data.health_change) >= 5) {
            this.showHealthNotification(data.health_change);
        }
    }

    handleStatusChange(data) {
        if (!this.currentEntity || this.currentEntity.id !== data.entity_id) return;

        this.currentEntity.status = data.new_status;

        // Update status display
        const statusEl = document.getElementById('entity-status');
        if (statusEl) {
            statusEl.textContent = data.new_status;
            statusEl.className = `status-badge ${data.new_status}`;
        }
    }

    handleCommitAnalyzed(data) {
        // Refresh recent activity to show new commit
        this.loadRecentActivity();

        // Show brief notification
        this.showTempMessage(`📊 Commit analyzed: ${Math.round(data.quality_score)}/100 quality`);
    }

    requestHealthUpdate() {
        chrome.runtime.sendMessage({ action: 'force_health_check' }, (response) => {
            if (chrome.runtime.lastError) {
                console.error("❌ Health check runtime error:", chrome.runtime.lastError);
                return;
            }

            if (response && !response.success) {
                console.error("❌ Health check failed:", response.error);
            }
        });
    }

    showHealthNotification(healthChange) {
        const notificationEl = document.createElement('div');
        notificationEl.className = `health-notification ${healthChange > 0 ? 'positive' : 'negative'}`;
        notificationEl.innerHTML = `
            <span class="notification-icon">${healthChange > 0 ? '📈' : '📉'}</span>
            <span class="notification-text">Health ${healthChange > 0 ? 'increased' : 'decreased'} by ${Math.abs(healthChange)}</span>
        `;

        document.body.appendChild(notificationEl);

        // Remove after 3 seconds
        setTimeout(() => {
            if (notificationEl.parentNode) {
                notificationEl.parentNode.removeChild(notificationEl);
            }
        }, 3000);
    }

    showTempMessage(message) {
        const messageEl = document.createElement('div');
        messageEl.className = 'temp-message';
        messageEl.textContent = message;

        document.body.appendChild(messageEl);

        setTimeout(() => {
            if (messageEl.parentNode) {
                messageEl.parentNode.removeChild(messageEl);
            }
        }, 2000);
    }
}

// Initialize extension
new TamagittoExtension();