// Tamagitto Extension Background Service Worker
console.log("🌟 Tamagitto Background Service Worker Started");

class TamagittoBackgroundService {
    constructor() {
        this.apiBaseUrl = 'https://tamagitto.xyz/api';
        this.websocket = null;
        this.isAuthenticated = false;
        this.currentUser = null;
        this.healthCheckInterval = null;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 5;

        this.init();
    }

    async init() {
        console.log("🚀 Initializing Tamagitto Background Service");

        // Check authentication on startup
        await this.checkAuthStatus();

        // Set up periodic health checks
        this.startHealthCheckInterval();

        // Set up message listeners
        this.setupMessageListeners();

        // Set up alarm for periodic tasks
        chrome.alarms.create('tamagitto-health-check', {
            periodInMinutes: 15 // Check health every 15 minutes
        });

        // Listen for alarms
        chrome.alarms.onAlarm.addListener((alarm) => {
            if (alarm.name === 'tamagitto-health-check') {
                this.performHealthCheck();
            }
        });

        console.log("✅ Background service initialized");
    }

    async checkAuthStatus() {
        try {
            const stored = await chrome.storage.local.get(['tamagitto_token', 'tamagitto_user']);

            if (stored.tamagitto_token) {
                const response = await this.apiCall('/auth/me', 'GET', null, stored.tamagitto_token);

                if (response.ok) {
                    this.isAuthenticated = true;
                    this.currentUser = await response.json();
                    console.log("✅ User authenticated in background:", this.currentUser.username);

                    // Initialize WebSocket connection for real-time updates
                    await this.connectWebSocket();
                } else {
                    // Token invalid, clear storage
                    await chrome.storage.local.remove(['tamagitto_token', 'tamagitto_user']);
                    this.isAuthenticated = false;
                    this.currentUser = null;
                }
            }
        } catch (error) {
            console.error("❌ Background auth check failed:", error);
        }
    }

    async connectWebSocket() {
        if (!this.isAuthenticated || this.websocket) return;

        try {
            const stored = await chrome.storage.local.get(['tamagitto_token']);
            const wsUrl = `wss://tamagitto.xyz/api/ws?token=${stored.tamagitto_token}`;

            this.websocket = new WebSocket(wsUrl);

            this.websocket.onopen = () => {
                console.log("🔗 WebSocket connected");
                this.reconnectAttempts = 0;

                // Send heartbeat every 30 seconds
                this.heartbeatInterval = setInterval(() => {
                    if (this.websocket.readyState === WebSocket.OPEN) {
                        this.websocket.send(JSON.stringify({ type: 'ping' }));
                    }
                }, 30000);
            };

            this.websocket.onmessage = (event) => {
                try {
                    const data = JSON.parse(event.data);
                    this.handleWebSocketMessage(data);
                } catch (error) {
                    console.error("❌ WebSocket message parse error:", error);
                }
            };

            this.websocket.onclose = () => {
                console.log("🔌 WebSocket disconnected");
                this.websocket = null;

                if (this.heartbeatInterval) {
                    clearInterval(this.heartbeatInterval);
                    this.heartbeatInterval = null;
                }

                // Attempt to reconnect if authenticated
                if (this.isAuthenticated && this.reconnectAttempts < this.maxReconnectAttempts) {
                    this.reconnectAttempts++;
                    console.log(`🔄 Attempting WebSocket reconnect (${this.reconnectAttempts}/${this.maxReconnectAttempts})`);
                    setTimeout(() => this.connectWebSocket(), 5000 * this.reconnectAttempts);
                }
            };

            this.websocket.onerror = (error) => {
                console.error("❌ WebSocket error:", error);
            };

        } catch (error) {
            console.error("❌ WebSocket connection failed:", error);
        }
    }

    handleWebSocketMessage(data) {
        console.log("📨 WebSocket message received:", data);

        switch (data.type) {
            case 'entity_health_update':
                this.handleHealthUpdate(data);
                break;
            case 'new_commit_analyzed':
                this.handleCommitAnalyzed(data);
                break;
            case 'entity_status_change':
                this.handleStatusChange(data);
                break;
            case 'pong':
                // Heartbeat response
                break;
            default:
                console.log("Unknown message type:", data.type);
        }
    }

    async handleHealthUpdate(data) {
        // Store latest health data
        await chrome.storage.local.set({
            latest_health_update: {
                ...data,
                timestamp: Date.now()
            }
        });

        // Send notification for significant health changes
        if (data.health_change && Math.abs(data.health_change) >= 10) {
            this.sendNotification(
                data.health_change > 0 ? "🎉 Code Pet Thriving!" : "⚠️ Code Pet Needs Attention",
                `Health ${data.health_change > 0 ? 'increased' : 'decreased'} by ${Math.abs(data.health_change)} points`
            );
        }

        // Update badge with health status
        this.updateBadge(data.current_health);
    }

    async handleCommitAnalyzed(data) {
        console.log("📊 New commit analyzed:", data);

        // Send notification for commit analysis
        if (data.quality_score !== undefined) {
            const quality = data.quality_score >= 80 ? "Excellent" :
                           data.quality_score >= 60 ? "Good" :
                           data.quality_score >= 40 ? "Fair" : "Needs Work";

            this.sendNotification(
                "📝 Commit Analyzed",
                `Quality: ${quality} (${Math.round(data.quality_score)}/100)`
            );
        }
    }

    async handleStatusChange(data) {
        console.log("🔄 Entity status changed:", data);

        // Send notification for status changes
        if (data.new_status) {
            this.sendNotification(
                "🐾 Pet Status Changed",
                `Your code pet is now ${data.new_status}`
            );
        }
    }

    async performHealthCheck() {
        if (!this.isAuthenticated) return;

        try {
            console.log("🏥 Performing health check...");

            const stored = await chrome.storage.local.get(['tamagitto_token']);
            const response = await this.apiCall('/entities/health-check', 'POST', {}, stored.tamagitto_token);

            if (response.ok) {
                const data = await response.json();
                console.log("✅ Health check complete:", data);

                // Update stored health data
                if (data.entities && data.entities.length > 0) {
                    await chrome.storage.local.set({
                        latest_entities: data.entities,
                        last_health_check: Date.now()
                    });

                    // Update badge with primary entity health
                    const primaryEntity = data.entities[0];
                    this.updateBadge(primaryEntity.health_score);
                }
            }
        } catch (error) {
            console.error("❌ Health check failed:", error);
        }
    }

    startHealthCheckInterval() {
        // Clear existing interval
        if (this.healthCheckInterval) {
            clearInterval(this.healthCheckInterval);
        }

        // Set up new interval for every 5 minutes when authenticated
        this.healthCheckInterval = setInterval(() => {
            if (this.isAuthenticated) {
                this.performHealthCheck();
            }
        }, 5 * 60 * 1000); // 5 minutes
    }

    setupMessageListeners() {
        // Listen for messages from popup or content scripts
        chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
            console.log("📨 Message received:", request);

            try {
                switch (request.action) {
                    case 'authenticate':
                        this.handleAuthMessage(request.data)
                            .then(sendResponse)
                            .catch(error => sendResponse({ success: false, error: error.message }));
                        return true; // Keep message channel open for async response

                    case 'logout':
                        this.handleLogoutMessage()
                            .then(sendResponse)
                            .catch(error => sendResponse({ success: false, error: error.message }));
                        return true;

                    case 'get_health_status':
                        this.getHealthStatus()
                            .then(sendResponse)
                            .catch(error => sendResponse({ success: false, error: error.message }));
                        return true;

                    case 'force_health_check':
                        this.performHealthCheck()
                            .then(() => sendResponse({ success: true }))
                            .catch(error => sendResponse({ success: false, error: error.message }));
                        return true;

                    case 'open_popup':
                        // Handle request to open popup (from content script)
                        sendResponse({ success: true });
                        break;

                    case 'setup_repo':
                        // Handle repo setup request
                        sendResponse({ success: true, message: 'Use popup to setup repository' });
                        break;

                    default:
                        sendResponse({ error: 'Unknown action' });
                }
            } catch (error) {
                console.error("❌ Message handler error:", error);
                sendResponse({ success: false, error: error.message });
            }
        });
    }

    async handleAuthMessage(data) {
        try {
            this.isAuthenticated = true;
            this.currentUser = data.user;

            // Connect WebSocket
            await this.connectWebSocket();

            // Start health monitoring
            this.startHealthCheckInterval();

            // Perform initial health check
            await this.performHealthCheck();

            return { success: true };
        } catch (error) {
            console.error("❌ Auth handling failed:", error);
            return { success: false, error: error.message };
        }
    }

    async handleLogoutMessage() {
        try {
            this.isAuthenticated = false;
            this.currentUser = null;

            // Close WebSocket
            if (this.websocket) {
                this.websocket.close();
                this.websocket = null;
            }

            // Clear intervals
            if (this.healthCheckInterval) {
                clearInterval(this.healthCheckInterval);
                this.healthCheckInterval = null;
            }

            if (this.heartbeatInterval) {
                clearInterval(this.heartbeatInterval);
                this.heartbeatInterval = null;
            }

            // Clear badge
            chrome.action.setBadgeText({ text: '' });

            // Clear stored data
            await chrome.storage.local.clear();

            return { success: true };
        } catch (error) {
            console.error("❌ Logout handling failed:", error);
            return { success: false, error: error.message };
        }
    }

    async getHealthStatus() {
        try {
            console.log("🔍 Getting health status...");

            const stored = await chrome.storage.local.get([
                'latest_health_update',
                'latest_entities',
                'last_health_check'
            ]);

            console.log("✅ Health status retrieved:", stored);

            return {
                success: true,
                data: stored
            };
        } catch (error) {
            console.error("❌ getHealthStatus error:", error);
            return { success: false, error: error.message };
        }
    }

    updateBadge(healthScore) {
        if (typeof healthScore !== 'number') return;

        // Set badge text with health score
        const badgeText = Math.round(healthScore).toString();
        chrome.action.setBadgeText({ text: badgeText });

        // Set badge color based on health
        let badgeColor = '#22c55e'; // Green for good health
        if (healthScore < 80) badgeColor = '#f59e0b'; // Yellow for warning
        if (healthScore < 60) badgeColor = '#ef4444'; // Red for danger
        if (healthScore < 40) badgeColor = '#dc2626'; // Dark red for critical

        chrome.action.setBadgeBackgroundColor({ color: badgeColor });
    }

    sendNotification(title, message) {
        // Check if notifications are enabled
        chrome.storage.local.get(['notifications_enabled'], (result) => {
            if (result.notifications_enabled !== false) { // Default to enabled
                chrome.notifications.create({
                    type: 'basic',
                    iconUrl: 'icons/icon-48.png',
                    title: title,
                    message: message
                });
            }
        });
    }

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
}

// Initialize background service
new TamagittoBackgroundService();