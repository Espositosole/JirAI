function checkQAColumn() {
    console.log("[Extension] Checking for QA cards (new layout)...");

    const cards = document.querySelectorAll('[data-testid="platform-board-kit.ui.card.card"]');
    console.log(`[Extension] Found ${cards.length} cards`);

    cards.forEach(card => {
        const columnContainer = card.closest('[data-testid^="platform-board-kit.ui.column"]');
        const columnTitleEl = columnContainer?.querySelector('[data-testid*="column-name"]');
        const columnTitle = columnTitleEl?.textContent?.trim();

        console.log("[Extension] Column title:", columnTitle);

        if (columnTitle === "QA") {
            const issueKey = card.getAttribute("data-issue-key") || card.textContent?.match(/[A-Z]+-\d+/)?.[0];
            console.log("[Extension] Raw issueKey:", issueKey);

            if (issueKey) {
                // Check for tested label
                const hasTestedLabel = checkForTestedLabel(card);
                console.log(`[Extension] Issue ${issueKey} has tested label: ${hasTestedLabel}`);
                
                chrome.runtime.sendMessage({
                    action: 'triggerAgent',
                    issueKey: issueKey,
                    hasTestedLabel: hasTestedLabel
                });
            } else {
                console.warn("[Extension] No issue key found in card");
            }
        }
    });
}

// Check if card has a "tested" label
function checkForTestedLabel(card) {
    // First check for labels in the modern Jira UI
    const labels = card.querySelectorAll('.label');
    for (const label of labels) {
        const labelText = label.textContent?.trim().toLowerCase();
        if (labelText === 'tested' || labelText === 'auto-tested') {
            return true;
        }
    }
    
    // Also check for tags in the description (sometimes rendered in the card)
    const description = card.querySelector('.ghx-description');
    if (description && description.textContent) {
        const descText = description.textContent.toLowerCase();
        if (descText.includes('#tested') || descText.includes('auto-tested')) {
            return true;
        }
    }
    
    // Additional check for the lozenge elements that often contain labels
    const lozenges = card.querySelectorAll('.lozenge');
    for (const lozenge of lozenges) {
        const lozengeText = lozenge.textContent?.trim().toLowerCase();
        if (lozengeText === 'tested' || lozengeText === 'auto-tested') {
            return true;
        }
    }
    
    return false;
}

chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
    if (request.action === "checkQAColumn") {
        console.log("[Extension] checkQAColumn triggered");
        checkQAColumn();
    }
});

// Auto-trigger when the page loads
window.addEventListener("load", () => {
    console.log("[Extension] Auto-triggering QA column check");
    chrome.runtime.sendMessage({ action: "checkQAColumn" });
});