let AGENT_BACKEND_URL = '';

chrome.storage.sync.get('backendUrl', (result) => {
    if (result.backendUrl) {
        AGENT_BACKEND_URL = result.backendUrl;
    }
});

chrome.tabs.onUpdated.addListener((tabId, changeInfo, tab) => {
    if (changeInfo.status === 'complete' && tab.url?.includes('atlassian.net')) {
        chrome.tabs.sendMessage(tabId, { action: 'checkQAColumn' });
    }
});

chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
    if (request.action === 'triggerAgent') {
        const { issueKey } = request;
        console.log(`[Agent] 🚀 Test started for ${issueKey}`);

        chrome.notifications?.create({
            type: "basic",
            iconUrl: "icon.png",
            title: "Jira Agent Running",
            message: `Running tests for ${issueKey}...`
        });

        fetch(AGENT_BACKEND_URL, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ issueKey })
        })
        .then(response => response.json())
        .then(data => {
            console.log(`[Agent] ✅ Testing complete for ${issueKey}`, data);

            chrome.notifications?.create({
                type: "basic",
                iconUrl: "icon.png",
                title: "Jira Agent ✅",
                message: `Test complete for ${issueKey}`
            });
        })
        .catch(error => {
            console.error(`[Agent] ❌ Testing failed for ${issueKey}`, error);

            chrome.notifications?.create({
                type: "basic",
                iconUrl: "icon.png",
                title: "Jira Agent ❌",
                message: `Test failed for ${issueKey}`
            });
        });
    }
});
