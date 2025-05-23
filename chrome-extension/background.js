let AGENT_BACKEND_URL = '';

chrome.storage.sync.get('backendUrl', (result) => {
    if (result.backendUrl) {
        AGENT_BACKEND_URL = result.backendUrl;
    }
});

// Check for notification permission on startup
chrome.runtime.onInstalled.addListener(() => {
    // Ensure we have notification permission
    chrome.permissions.contains({ permissions: ['notifications'] }, (result) => {
        if (!result) {
            console.log('[Agent] Notifications permission not available');
        } else {
            console.log('[Agent] Notifications permission available');
        }
    });
});

// Store tested issue keys to prevent duplicate tests
const testedIssueKeys = new Set();

chrome.tabs.onUpdated.addListener((tabId, changeInfo, tab) => {
    if (changeInfo.status === 'complete' && tab.url?.includes('atlassian.net')) {
        chrome.tabs.sendMessage(tabId, { action: 'checkQAColumn' });
    }
});

chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
    if (request.action === 'triggerAgent') {
        const { issueKey, hasTestedLabel } = request;
        
        // Skip if already labeled as tested
        if (hasTestedLabel) {
            console.log(`[Agent] 🔄 Skipping ${issueKey} as it's already labeled as tested`);
            return;
        }
        
        // Skip if we've already tested this in the current session
        if (testedIssueKeys.has(issueKey)) {
            console.log(`[Agent] 🔄 Skipping ${issueKey} as it was already tested in this session`);
            return;
        }
        
        console.log(`[Agent] 🚀 Test started for ${issueKey}`);
        testedIssueKeys.add(issueKey); // Add to our in-memory set of tested issues

        // Create notification for test start
        try {
            chrome.notifications.create(`test-start-${issueKey}`, {
                type: "basic",
                iconUrl: chrome.runtime.getURL("icon.png"),
                title: "Jira Agent Running",
                message: `Running tests for ${issueKey}...`,
                priority: 2
            });
        } catch (error) {
            console.error('[Agent] Failed to create notification:', error);
        }

        fetch(AGENT_BACKEND_URL || 'http://localhost:5000/run-tests', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ issueKey })
        })
        .then(response => response.json())
        .then(data => {
            console.log(`[Agent] ✅ Testing complete for ${issueKey}`, data);

            // Create notification for test complete
            try {
                chrome.notifications.create(`test-complete-${issueKey}`, {
                    type: "basic",
                    iconUrl: chrome.runtime.getURL("icon.png"),
                    title: "Jira Agent ✅",
                    message: `Test complete for ${issueKey}`,
                    priority: 2
                });
            } catch (error) {
                console.error('[Agent] Failed to create completion notification:', error);
            }
        })
        .catch(error => {
            console.error(`[Agent] ❌ Testing failed for ${issueKey}`, error);
            // Remove from tested set since it failed
            testedIssueKeys.delete(issueKey);

            // Create notification for test failure
            try {
                chrome.notifications.create(`test-error-${issueKey}`, {
                    type: "basic",
                    iconUrl: chrome.runtime.getURL("icon.png"),
                    title: "Jira Agent ❌",
                    message: `Test failed for ${issueKey}`,
                    priority: 2
                });
            } catch (error) {
                console.error('[Agent] Failed to create error notification:', error);
            }
        });
    } else if (request.action === 'suggestScenarios') {
        const { issueKey } = request;

        fetch(AGENT_BACKEND_URL || 'http://localhost:5000/suggest-scenarios', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ issueKey })
        })
        .then(response => response.json())
        .then(data => {
            console.log(`[Agent] ✅ Scenarios suggested for ${issueKey}`, data);
        })
        .catch(error => {
            console.error(`[Agent] ❌ Failed to suggest scenarios for ${issueKey}`, error);
        });
    }
});

// Add a listener for notification click
chrome.notifications.onClicked.addListener((notificationId) => {
    console.log(`[Agent] Notification clicked: ${notificationId}`);
    
    // Extract issue key from notification ID
    const match = notificationId.match(/-([A-Z]+-\d+)$/);
    if (match && match[1]) {
        const issueKey = match[1];
        // Open Jira issue in new tab
        chrome.tabs.create({
            url: `https://agentjirai.atlassian.net/browse/${issueKey}`
        });
    }
    
    // Clear the notification
    chrome.notifications.clear(notificationId);
});