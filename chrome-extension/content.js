function checkQAColumn() {
    const qaColumns = document.querySelectorAll('.js-column[data-column-name="QA"] .js-card');
    
    qaColumns.forEach(card => {
        const issueKey = card.getAttribute('data-issue-key');
        if (issueKey) {
            chrome.runtime.sendMessage({
                action: 'triggerAgent', 
                issueKey: issueKey
            });
        }
    });
}

chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
    if (request.action === 'checkQAColumn') {
        checkQAColumn();
    }
});
    