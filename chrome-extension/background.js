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
    if (request.action === "triggerAgent") {
        console.log("[Agent] Received triggerAgent for", request.issueKey, "with status:", request.status);

        let endpoint = "";
        if (request.status === "qa") {
        endpoint = "run-tests";
        } else if (request.status === "in progress") {
        endpoint = "suggest-scenarios";
        }

        const url = (AGENT_BACKEND_URL || 'http://localhost:5000') + '/' + endpoint;

        fetch(url, {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                issueKey: request.issueKey,
                status: request.status,
                hasTestedLabel: request.hasTestedLabel || false
            })
        })
        .then(res => res.json())
        .then(data => console.log("[Agent] ✅ Response:", data))
        .catch(err => console.error("[Agent] ❌ Error:", err));
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