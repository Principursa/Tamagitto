// Tamagitto Extension Content Script for GitHub Integration
console.log("🐙 Tamagitto GitHub Content Script Loaded");

class TamagittoGitHubIntegration {
    constructor() {
        this.currentRepo = null;
        this.entityData = null;
        this.isAuthenticated = false;
        this.healthIndicator = null;

        this.init();
    }

    async init() {
        console.log("🚀 Initializing GitHub integration");

        // Check if user is authenticated with Tamagitto
        await this.checkTamagittoAuth();

        if (this.isAuthenticated) {
            // Extract repository information
            this.extractRepoInfo();

            // Check if this repo has a Tamagitto entity
            await this.checkRepoEntity();

            // Add Tamagitto UI elements to GitHub
            this.injectTamagittoUI();

            // Set up observers for dynamic content
            this.setupObservers();
        }

        // Listen for messages from background/popup
        chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
            this.handleMessage(request, sender, sendResponse);
        });
    }

    async checkTamagittoAuth() {
        try {
            const stored = await chrome.storage.local.get(['tamagitto_token', 'tamagitto_user']);
            this.isAuthenticated = !!stored.tamagitto_token;

            if (this.isAuthenticated) {
                console.log("✅ User is authenticated with Tamagitto");
            }
        } catch (error) {
            console.error("❌ Auth check failed:", error);
        }
    }

    extractRepoInfo() {
        // Extract repository info from GitHub URL
        const pathParts = window.location.pathname.split('/').filter(part => part);

        if (pathParts.length >= 2) {
            this.currentRepo = {
                owner: pathParts[0],
                name: pathParts[1],
                fullName: `${pathParts[0]}/${pathParts[1]}`
            };

            console.log("📁 Current repository:", this.currentRepo.fullName);
        }
    }

    async checkRepoEntity() {
        if (!this.currentRepo || !this.isAuthenticated) return;

        try {
            const stored = await chrome.storage.local.get(['tamagitto_token']);
            const response = await fetch(`https://tamagitto.xyz/api/repositories/by-name/${this.currentRepo.fullName}`, {
                headers: {
                    'Authorization': `Bearer ${stored.tamagitto_token}`
                }
            });

            if (response.ok) {
                const data = await response.json();
                if (data.entity) {
                    this.entityData = data.entity;
                    console.log("🐾 Found Tamagitto entity for this repo:", this.entityData.name);
                } else {
                    console.log("📝 No Tamagitto entity found for this repository");
                }
            }
        } catch (error) {
            console.error("❌ Failed to check repo entity:", error);
        }
    }

    injectTamagittoUI() {
        // Add Tamagitto indicator to repository header
        this.addRepoHeaderIndicator();

        // Add commit quality indicators if on commits page
        if (window.location.pathname.includes('/commits')) {
            this.addCommitQualityIndicators();
        }

        // Add pull request health indicators if on PR page
        if (window.location.pathname.includes('/pull/')) {
            this.addPRHealthIndicator();
        }
    }

    addRepoHeaderIndicator() {
        const repoHeader = document.querySelector('[data-testid="breadcrumb"]') ||
                          document.querySelector('.pagehead h1') ||
                          document.querySelector('.Header-item--full h1');

        if (!repoHeader) return;

        // Remove existing indicator if present
        const existing = document.getElementById('tamagitto-repo-indicator');
        if (existing) existing.remove();

        // Create indicator
        const indicator = document.createElement('div');
        indicator.id = 'tamagitto-repo-indicator';
        indicator.className = 'tamagitto-repo-indicator';

        if (this.entityData) {
            const healthPercent = Math.max(0, Math.min(100, this.entityData.health_score));
            const healthClass = this.getHealthClass(healthPercent);

            indicator.innerHTML = `
                <div class="tamagitto-health-badge ${healthClass}" title="Tamagitto Health: ${Math.round(healthPercent)}/100">
                    <span class="tamagitto-icon">🐾</span>
                    <span class="tamagitto-health">${Math.round(healthPercent)}</span>
                    <div class="tamagitto-tooltip">
                        <strong>${this.entityData.name}</strong><br>
                        Health: ${Math.round(healthPercent)}/100<br>
                        Status: ${this.entityData.status}<br>
                        <small>Click to view in Tamagitto</small>
                    </div>
                </div>
            `;

            indicator.addEventListener('click', () => {
                chrome.runtime.sendMessage({ action: 'open_popup' });
            });
        } else {
            indicator.innerHTML = `
                <div class="tamagitto-setup-badge" title="Set up Tamagitto for this repository">
                    <span class="tamagitto-icon">🐾</span>
                    <span class="tamagitto-text">Setup</span>
                    <div class="tamagitto-tooltip">
                        <strong>Create a Tamagitto pet</strong><br>
                        Monitor your code quality!<br>
                        <small>Click to get started</small>
                    </div>
                </div>
            `;

            indicator.addEventListener('click', () => {
                chrome.runtime.sendMessage({ action: 'setup_repo', repo: this.currentRepo });
            });
        }

        // Insert after the repo header
        repoHeader.parentNode.insertBefore(indicator, repoHeader.nextSibling);
    }

    addCommitQualityIndicators() {
        const commitElements = document.querySelectorAll('[data-testid="commit-row-item"], .js-navigation-item');

        commitElements.forEach(async (commitEl) => {
            // Skip if already processed
            if (commitEl.querySelector('.tamagitto-commit-indicator')) return;

            const commitSha = this.extractCommitSha(commitEl);
            if (!commitSha) return;

            // Check if this commit has been analyzed
            const analysis = await this.getCommitAnalysis(commitSha);

            if (analysis) {
                this.addCommitIndicator(commitEl, analysis);
            }
        });
    }

    extractCommitSha(commitElement) {
        // Try different selectors for commit SHA
        const shaElement = commitElement.querySelector('[data-testid="commit-sha"]') ||
                          commitElement.querySelector('.commit-sha') ||
                          commitElement.querySelector('[href*="/commit/"]');

        if (shaElement) {
            const href = shaElement.getAttribute('href');
            if (href) {
                const shaMatch = href.match(/\/commit\/([a-f0-9]{40})/);
                return shaMatch ? shaMatch[1] : null;
            }
        }

        return null;
    }

    async getCommitAnalysis(commitSha) {
        if (!this.isAuthenticated || !this.entityData) return null;

        try {
            const stored = await chrome.storage.local.get(['tamagitto_token']);
            const response = await fetch(`https://tamagitto.xyz/api/entities/${this.entityData.id}/commits/${commitSha}/analysis`, {
                headers: {
                    'Authorization': `Bearer ${stored.tamagitto_token}`
                }
            });

            if (response.ok) {
                return await response.json();
            }
        } catch (error) {
            console.error("❌ Failed to get commit analysis:", error);
        }

        return null;
    }

    addCommitIndicator(commitElement, analysis) {
        const indicator = document.createElement('span');
        indicator.className = 'tamagitto-commit-indicator';

        const qualityScore = analysis.quality_score || 0;
        const healthImpact = analysis.health_impact || 0;

        const qualityClass = qualityScore >= 80 ? 'excellent' :
                           qualityScore >= 60 ? 'good' :
                           qualityScore >= 40 ? 'warning' : 'danger';

        const impactIcon = healthImpact > 0 ? '📈' : healthImpact < 0 ? '📉' : '➖';

        indicator.innerHTML = `
            <div class="tamagitto-commit-badge ${qualityClass}" title="Code Quality: ${Math.round(qualityScore)}/100, Health Impact: ${healthImpact > 0 ? '+' : ''}${healthImpact}">
                <span class="tamagitto-quality">${Math.round(qualityScore)}</span>
                <span class="tamagitto-impact">${impactIcon}</span>
            </div>
        `;

        // Find a good place to insert the indicator
        const commitMessage = commitElement.querySelector('.commit-message') ||
                             commitElement.querySelector('[data-testid="commit-message"]') ||
                             commitElement.querySelector('.message');

        if (commitMessage) {
            commitMessage.appendChild(indicator);
        }
    }

    addPRHealthIndicator() {
        const prHeader = document.querySelector('.gh-header-meta') ||
                        document.querySelector('.pull-request-tab-content .TableObject');

        if (!prHeader || !this.entityData) return;

        // Remove existing indicator
        const existing = document.getElementById('tamagitto-pr-indicator');
        if (existing) existing.remove();

        const indicator = document.createElement('div');
        indicator.id = 'tamagitto-pr-indicator';
        indicator.className = 'tamagitto-pr-indicator';

        indicator.innerHTML = `
            <div class="tamagitto-pr-health">
                <span class="tamagitto-icon">🐾</span>
                <span class="tamagitto-text">Potential Health Impact</span>
                <div class="tamagitto-pr-details">
                    <div class="tamagitto-loading">Analyzing changes...</div>
                </div>
            </div>
        `;

        prHeader.appendChild(indicator);

        // Analyze PR impact
        this.analyzePRImpact();
    }

    async analyzePRImpact() {
        const prNumber = this.extractPRNumber();
        if (!prNumber || !this.entityData) return;

        try {
            const stored = await chrome.storage.local.get(['tamagitto_token']);
            const response = await fetch(`https://tamagitto.xyz/api/entities/${this.entityData.id}/pr/${prNumber}/impact`, {
                headers: {
                    'Authorization': `Bearer ${stored.tamagitto_token}`
                }
            });

            if (response.ok) {
                const impact = await response.json();
                this.updatePRIndicator(impact);
            } else {
                this.updatePRIndicator({ error: 'Analysis not available' });
            }
        } catch (error) {
            console.error("❌ Failed to analyze PR impact:", error);
            this.updatePRIndicator({ error: 'Analysis failed' });
        }
    }

    extractPRNumber() {
        const match = window.location.pathname.match(/\/pull\/(\d+)/);
        return match ? match[1] : null;
    }

    updatePRIndicator(impact) {
        const detailsEl = document.querySelector('.tamagitto-pr-details');
        if (!detailsEl) return;

        if (impact.error) {
            detailsEl.innerHTML = `<div class="tamagitto-error">${impact.error}</div>`;
            return;
        }

        const estimatedImpact = impact.estimated_health_impact || 0;
        const impactClass = estimatedImpact > 0 ? 'positive' : estimatedImpact < 0 ? 'negative' : 'neutral';
        const impactIcon = estimatedImpact > 0 ? '📈' : estimatedImpact < 0 ? '📉' : '➖';

        detailsEl.innerHTML = `
            <div class="tamagitto-impact ${impactClass}">
                <span class="impact-icon">${impactIcon}</span>
                <span class="impact-text">${estimatedImpact > 0 ? '+' : ''}${estimatedImpact} health points</span>
            </div>
            <div class="tamagitto-summary">
                ${impact.summary || 'Changes analyzed'}
            </div>
        `;
    }

    setupObservers() {
        // Watch for navigation changes (GitHub uses PJAX)
        const observer = new MutationObserver((mutations) => {
            let shouldUpdate = false;

            mutations.forEach((mutation) => {
                if (mutation.type === 'childList') {
                    // Check if we've navigated to a new page
                    if (mutation.target === document.body ||
                        mutation.addedNodes.length > 0) {
                        shouldUpdate = true;
                    }
                }
            });

            if (shouldUpdate) {
                // Debounce updates
                clearTimeout(this.updateTimeout);
                this.updateTimeout = setTimeout(() => {
                    this.handleNavigation();
                }, 500);
            }
        });

        observer.observe(document.body, {
            childList: true,
            subtree: true
        });
    }

    async handleNavigation() {
        console.log("🔄 GitHub navigation detected, updating Tamagitto UI");

        // Re-extract repo info
        const oldRepo = this.currentRepo;
        this.extractRepoInfo();

        // If repo changed, check for entity
        if (!oldRepo || oldRepo.fullName !== this.currentRepo?.fullName) {
            await this.checkRepoEntity();
        }

        // Re-inject UI elements
        this.injectTamagittoUI();
    }

    handleMessage(request, sender, sendResponse) {
        switch (request.action) {
            case 'update_entity_data':
                this.entityData = request.data;
                this.injectTamagittoUI();
                sendResponse({ success: true });
                break;

            case 'get_current_repo':
                sendResponse({
                    repo: this.currentRepo,
                    hasEntity: !!this.entityData
                });
                break;

            default:
                sendResponse({ error: 'Unknown action' });
        }
    }

    getHealthClass(health) {
        if (health >= 80) return 'excellent';
        if (health >= 60) return 'good';
        if (health >= 40) return 'warning';
        if (health >= 20) return 'danger';
        return 'critical';
    }
}

// Initialize GitHub integration
new TamagittoGitHubIntegration();