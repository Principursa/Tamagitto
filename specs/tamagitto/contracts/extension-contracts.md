# Extension Contracts

**Feature**: Tamagitto Chrome Extension Interface  
**Date**: 2025-09-27  
**Manifest Version**: 3

## Extension Architecture

### Manifest V3 Configuration
```json
{
    "manifest_version": 3,
    "name": "Tamagitto - Code Tamagotchi",
    "version": "1.0.0",
    "description": "Keep your code pet alive with quality commits!",
    
    "permissions": [
        "storage",
        "identity",
        "activeTab"
    ],
    
    "host_permissions": [
        "https://tamagitto.xyz/*",
        "https://github.com/*"
    ],
    
    "action": {
        "default_popup": "popup.html",
        "default_title": "Tamagitto",
        "default_icon": {
            "16": "icons/icon16.png",
            "32": "icons/icon32.png",
            "48": "icons/icon48.png", 
            "128": "icons/icon128.png"
        }
    },
    
    "background": {
        "service_worker": "background.js"
    },
    
    "content_security_policy": {
        "extension_pages": "script-src 'self'; object-src 'self'"
    }
}
```

## Popup Interface Contract

### HTML Structure
```html
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=320,height=480">
    <link rel="stylesheet" href="styles/popup.css">
</head>
<body>
    <div id="app-container">
        <!-- Authentication State -->
        <div id="auth-screen" class="screen">
            <div class="welcome">
                <img src="icons/mascot.png" alt="Tamagitto mascot">
                <h2>Welcome to Tamagitto!</h2>
                <p>Connect your GitHub to start caring for your code pet.</p>
                <button id="github-login-btn" class="primary-button">
                    Connect GitHub
                </button>
            </div>
        </div>
        
        <!-- Repository Selection State -->
        <div id="repo-selection-screen" class="screen hidden">
            <div class="header">
                <h3>Choose Repository</h3>
                <button id="logout-btn" class="icon-button">⚙️</button>
            </div>
            <div class="search-container">
                <input type="text" id="repo-search" placeholder="Search repositories...">
            </div>
            <div id="repo-list" class="repo-list">
                <!-- Dynamically populated -->
            </div>
        </div>
        
        <!-- Entity Dashboard State -->
        <div id="entity-screen" class="screen hidden">
            <div class="header">
                <h3 id="entity-name">CodeBuddy</h3>
                <div class="header-actions">
                    <button id="settings-btn" class="icon-button">⚙️</button>
                    <button id="info-btn" class="icon-button">ℹ️</button>
                </div>
            </div>
            
            <div class="entity-display">
                <div class="entity-visual">
                    <img id="entity-image" src="" alt="Your code pet">
                    <div class="health-indicator">
                        <div class="health-bar">
                            <div id="health-fill" class="health-fill"></div>
                        </div>
                        <span id="health-score">100</span>
                    </div>
                </div>
                
                <div class="entity-status">
                    <div class="status-item">
                        <span class="label">Status:</span>
                        <span id="entity-status" class="status-badge">Thriving</span>
                    </div>
                    <div class="status-item">
                        <span class="label">Repository:</span>
                        <span id="repo-name">username/repo</span>
                    </div>
                </div>
            </div>
            
            <div class="recent-activity">
                <h4>Recent Activity</h4>
                <div id="activity-list" class="activity-list">
                    <!-- Dynamically populated -->
                </div>
            </div>
            
            <div class="actions">
                <button id="view-history-btn" class="secondary-button">
                    View Health History
                </button>
                <button id="change-repo-btn" class="secondary-button">
                    Change Repository
                </button>
            </div>
        </div>
        
        <!-- Entity Death State -->
        <div id="death-screen" class="screen hidden">
            <div class="death-notice">
                <img src="icons/rip.png" alt="RIP">
                <h3>Your entity has passed away</h3>
                <p>Don't worry! You can create a new one after the cooldown period.</p>
                <div class="cooldown-timer">
                    <span id="cooldown-time">23:45:12</span>
                </div>
                <button id="create-new-btn" class="primary-button" disabled>
                    Create New Entity
                </button>
            </div>
        </div>
        
        <!-- Loading States -->
        <div id="loading-overlay" class="loading-overlay hidden">
            <div class="spinner"></div>
            <p id="loading-message">Loading...</p>
        </div>
    </div>
    
    <script src="popup.js"></script>
</body>
</html>
```

## JavaScript API Contract

### Storage Interface
```javascript
class ExtensionStorage {
    static async getSessionToken() {
        const result = await chrome.storage.local.get(['sessionToken']);
        return result.sessionToken;
    }
    
    static async setSessionToken(token) {
        await chrome.storage.local.set({ sessionToken: token });
    }
    
    static async getEntityCache() {
        const result = await chrome.storage.local.get(['entityCache']);
        return result.entityCache;
    }
    
    static async setEntityCache(entity) {
        await chrome.storage.local.set({ 
            entityCache: entity,
            lastCacheUpdate: Date.now()
        });
    }
    
    static async clearUserData() {
        await chrome.storage.local.clear();
    }
}
```

### API Client
```javascript
class TamagittoAPI {
    constructor() {
        this.baseURL = 'https://tamagitto.xyz/api';
        this.wsURL = 'wss://tamagitto.xyz/api/ws';
        this.ws = null;
    }
    
    async authenticatedRequest(endpoint, options = {}) {
        const token = await ExtensionStorage.getSessionToken();
        if (!token) {
            throw new Error('Not authenticated');
        }
        
        const response = await fetch(`${this.baseURL}${endpoint}`, {
            ...options,
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json',
                ...options.headers
            }
        });
        
        if (response.status === 401) {
            await this.logout();
            throw new Error('Session expired');
        }
        
        return response;
    }
    
    async initiateGitHubAuth() {
        const response = await fetch(`${this.baseURL}/auth/github/initiate`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                redirect_uri: chrome.runtime.getURL('oauth-callback.html')
            })
        });
        
        return response.json();
    }
    
    async completeGitHubAuth(code, state) {
        const response = await fetch(`${this.baseURL}/auth/github/callback`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ code, state })
        });
        
        const data = await response.json();
        if (data.session_token) {
            await ExtensionStorage.setSessionToken(data.session_token);
        }
        
        return data;
    }
    
    async getCurrentEntity() {
        const response = await this.authenticatedRequest('/entities/current');
        return response.json();
    }
    
    async getRepositories() {
        const response = await this.authenticatedRequest('/repositories');
        return response.json();
    }
    
    async startMonitoring(githubRepoId, preferences = {}) {
        const response = await this.authenticatedRequest(
            `/repositories/${githubRepoId}/monitor`, 
            {
                method: 'POST',
                body: JSON.stringify({ entity_preferences: preferences })
            }
        );
        return response.json();
    }
    
    connectWebSocket() {
        return new Promise((resolve, reject) => {
            ExtensionStorage.getSessionToken().then(token => {
                if (!token) {
                    reject(new Error('No session token'));
                    return;
                }
                
                this.ws = new WebSocket(`${this.wsURL}?token=${token}`);
                
                this.ws.onopen = () => resolve(this.ws);
                this.ws.onerror = reject;
                
                this.ws.onmessage = (event) => {
                    const data = JSON.parse(event.data);
                    this.handleWebSocketMessage(data);
                };
            });
        });
    }
    
    handleWebSocketMessage(data) {
        switch (data.type) {
            case 'health_update':
                this.updateEntityDisplay(data);
                break;
            case 'status_change':
                this.handleStatusChange(data);
                break;
            case 'analysis_complete':
                this.showAnalysisResult(data);
                break;
        }
    }
}
```

### OAuth Flow Implementation
```javascript
class GitHubOAuth {
    static async authenticate() {
        try {
            const api = new TamagittoAPI();
            const { oauth_url, state } = await api.initiateGitHubAuth();
            
            // Store state for verification
            await chrome.storage.local.set({ oauthState: state });
            
            // Launch OAuth flow
            const responseURL = await chrome.identity.launchWebAuthFlow({
                url: oauth_url,
                interactive: true
            });
            
            // Extract authorization code from redirect URL
            const url = new URL(responseURL);
            const code = url.searchParams.get('code');
            const returnedState = url.searchParams.get('state');
            
            // Verify state
            const { oauthState } = await chrome.storage.local.get(['oauthState']);
            if (returnedState !== oauthState) {
                throw new Error('OAuth state mismatch');
            }
            
            // Complete authentication
            const result = await api.completeGitHubAuth(code, returnedState);
            
            // Clean up
            await chrome.storage.local.remove(['oauthState']);
            
            return result;
            
        } catch (error) {
            console.error('OAuth flow failed:', error);
            throw error;
        }
    }
}
```

### UI State Management
```javascript
class PopupUI {
    constructor() {
        this.api = new TamagittoAPI();
        this.currentScreen = 'auth';
        this.entityUpdateInterval = null;
    }
    
    async init() {
        await this.loadInitialState();
        this.setupEventListeners();
        this.connectRealTimeUpdates();
    }
    
    async loadInitialState() {
        const token = await ExtensionStorage.getSessionToken();
        
        if (!token) {
            this.showScreen('auth');
            return;
        }
        
        try {
            const entityData = await this.api.getCurrentEntity();
            if (entityData.entity) {
                await ExtensionStorage.setEntityCache(entityData.entity);
                this.showScreen('entity');
                this.updateEntityDisplay(entityData.entity);
            } else {
                this.showScreen('repo-selection');
                await this.loadRepositories();
            }
        } catch (error) {
            console.error('Failed to load entity:', error);
            this.showScreen('auth');
        }
    }
    
    showScreen(screenName) {
        document.querySelectorAll('.screen').forEach(screen => {
            screen.classList.add('hidden');
        });
        document.getElementById(`${screenName}-screen`).classList.remove('hidden');
        this.currentScreen = screenName;
    }
    
    async updateEntityDisplay(entity) {
        document.getElementById('entity-name').textContent = entity.name;
        document.getElementById('entity-image').src = entity.visual_url;
        document.getElementById('health-score').textContent = entity.health_score;
        document.getElementById('entity-status').textContent = this.getStatusText(entity.health_score);
        document.getElementById('repo-name').textContent = entity.repository.full_name;
        
        // Update health bar
        const healthFill = document.getElementById('health-fill');
        healthFill.style.width = `${entity.health_score}%`;
        healthFill.className = `health-fill ${this.getHealthClass(entity.health_score)}`;
        
        // Check if entity is dead
        if (entity.status === 'dead') {
            this.showScreen('death');
        }
    }
    
    getStatusText(healthScore) {
        if (healthScore >= 80) return 'Thriving';
        if (healthScore >= 60) return 'Healthy';
        if (healthScore >= 40) return 'Okay';
        if (healthScore >= 20) return 'Poor';
        return 'Dying';
    }
    
    getHealthClass(healthScore) {
        if (healthScore >= 60) return 'healthy';
        if (healthScore >= 30) return 'warning';
        return 'critical';
    }
    
    setupEventListeners() {
        // GitHub login
        document.getElementById('github-login-btn').addEventListener('click', 
            () => this.handleGitHubLogin());
        
        // Repository selection
        document.getElementById('repo-search').addEventListener('input',
            (e) => this.filterRepositories(e.target.value));
        
        // Settings and actions
        document.getElementById('settings-btn').addEventListener('click',
            () => this.showSettings());
        document.getElementById('change-repo-btn').addEventListener('click',
            () => this.showRepositorySelection());
        
        // Entity reset
        document.getElementById('create-new-btn').addEventListener('click',
            () => this.resetEntity());
    }
    
    async connectRealTimeUpdates() {
        try {
            await this.api.connectWebSocket();
        } catch (error) {
            console.warn('WebSocket connection failed, falling back to polling:', error);
            this.startPolling();
        }
    }
    
    startPolling() {
        this.entityUpdateInterval = setInterval(async () => {
            if (this.currentScreen === 'entity') {
                try {
                    const entityData = await this.api.getCurrentEntity();
                    this.updateEntityDisplay(entityData.entity);
                } catch (error) {
                    console.error('Polling update failed:', error);
                }
            }
        }, 30000); // Poll every 30 seconds
    }
}

// Initialize popup when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    const popup = new PopupUI();
    popup.init();
});
```

## Background Service Worker

### Service Worker Contract
```javascript
// background.js
class TamagittoBackground {
    constructor() {
        this.api = new TamagittoAPI();
    }
    
    init() {
        // Listen for extension installation
        chrome.runtime.onInstalled.addListener((details) => {
            if (details.reason === 'install') {
                this.handleFirstInstall();
            }
        });
        
        // Handle periodic entity health checks
        chrome.alarms.onAlarm.addListener((alarm) => {
            if (alarm.name === 'entityHealthCheck') {
                this.checkEntityHealth();
            }
        });
        
        // Set up periodic health checks (every 5 minutes)
        chrome.alarms.create('entityHealthCheck', { 
            delayInMinutes: 5, 
            periodInMinutes: 5 
        });
    }
    
    async handleFirstInstall() {
        // Open welcome/onboarding page
        chrome.tabs.create({ 
            url: 'https://tamagitto.xyz/welcome' 
        });
    }
    
    async checkEntityHealth() {
        try {
            const token = await ExtensionStorage.getSessionToken();
            if (!token) return;
            
            const entityData = await this.api.getCurrentEntity();
            if (entityData.entity) {
                // Update cached entity data
                await ExtensionStorage.setEntityCache(entityData.entity);
                
                // Show notifications for critical health
                if (entityData.entity.health_score <= 20 && entityData.entity.status === 'alive') {
                    this.showHealthWarning(entityData.entity);
                }
                
                // Update extension badge
                this.updateBadge(entityData.entity);
            }
        } catch (error) {
            console.error('Health check failed:', error);
        }
    }
    
    showHealthWarning(entity) {
        chrome.notifications.create({
            type: 'basic',
            iconUrl: 'icons/icon48.png',
            title: 'Tamagitto Alert!',
            message: `${entity.name} is in critical condition! Make some quality commits soon.`,
            priority: 2
        });
    }
    
    updateBadge(entity) {
        const healthScore = entity.health_score;
        let badgeColor = '#4CAF50'; // Green
        let badgeText = '';
        
        if (entity.status === 'dead') {
            badgeColor = '#f44336'; // Red
            badgeText = '💀';
        } else if (healthScore <= 20) {
            badgeColor = '#f44336'; // Red
            badgeText = '!';
        } else if (healthScore <= 40) {
            badgeColor = '#FF9800'; // Orange
        }
        
        chrome.action.setBadgeText({ text: badgeText });
        chrome.action.setBadgeBackgroundColor({ color: badgeColor });
    }
}

// Initialize background service
const background = new TamagittoBackground();
background.init();
```

## Error Handling Contract

### Error Display Patterns
```javascript
class ErrorHandler {
    static showError(message, type = 'error') {
        const errorContainer = document.createElement('div');
        errorContainer.className = `error-message ${type}`;
        errorContainer.innerHTML = `
            <div class="error-content">
                <span class="error-text">${message}</span>
                <button class="error-close">&times;</button>
            </div>
        `;
        
        document.body.appendChild(errorContainer);
        
        // Auto-remove after 5 seconds
        setTimeout(() => {
            if (errorContainer.parentNode) {
                errorContainer.parentNode.removeChild(errorContainer);
            }
        }, 5000);
    }
    
    static handleAPIError(error) {
        if (error.message === 'Session expired') {
            this.showError('Your session has expired. Please log in again.', 'warning');
            // Redirect to auth screen
            return;
        }
        
        if (error.message === 'Rate limit exceeded') {
            this.showError('Too many requests. Please wait a moment.', 'warning');
            return;
        }
        
        this.showError('Something went wrong. Please try again.', 'error');
    }
}
```

## Testing Contracts

### Unit Test Requirements
```javascript
// Tests for API client
describe('TamagittoAPI', () => {
    test('should handle authentication flow', async () => {
        // Mock chrome.identity API
        // Test OAuth flow completion
        // Verify token storage
    });
    
    test('should handle entity updates via WebSocket', async () => {
        // Mock WebSocket connection
        // Test message handling
        // Verify UI updates
    });
    
    test('should fallback to polling on WebSocket failure', async () => {
        // Mock WebSocket failure
        // Verify polling initialization
        // Test periodic updates
    });
});

// Tests for UI components
describe('PopupUI', () => {
    test('should display correct screen based on auth state', async () => {
        // Test screen transitions
        // Verify conditional rendering
    });
    
    test('should update entity display correctly', async () => {
        // Test health bar updates
        // Verify status text changes
        // Check image updates
    });
});
```

### Integration Test Scenarios
1. **Complete User Flow**: Auth → Repo Selection → Entity Creation → Health Updates
2. **Offline Handling**: Network failures, API unavailability
3. **Session Management**: Token expiration, refresh handling
4. **Real-time Updates**: WebSocket connection, fallback polling
5. **Error States**: Dead entity, cooldown periods, rate limiting