function checkQAColumn() {
    console.log("[Extension] Starting QA column check process...");

    const cards = document.querySelectorAll('[data-testid="platform-board-kit.ui.card.card"]');
    
    let processedCount = 0;
    let skippedCount = 0;
    let totalQACards = 0;
    
    cards.forEach(card => {
        const columnContainer = card.closest('[data-testid^="platform-board-kit.ui.column"]');
        const columnTitleEl = columnContainer?.querySelector('[data-testid*="column-name"]');
        const columnTitle = columnTitleEl?.textContent?.trim();

        if (columnTitle === "QA") {
            totalQACards++;
            const issueKey = card.getAttribute("data-issue-key") || card.textContent?.match(/[A-Z]+-\d+/)?.[0];
            
            if (issueKey) {
                // Check for tested label
                const hasTestedLabel = checkForTestedLabel(card);
                
                chrome.runtime.sendMessage({
                    action: 'triggerAgent',
                    issueKey: issueKey,
                    hasTestedLabel: hasTestedLabel
                });
                
                processedCount++;
            } else {
                skippedCount++;
            }
        }
    });
    
    console.log(`[Extension] QA column check complete. Found ${totalQACards} QA cards: ${processedCount} processed, ${skippedCount} skipped (no issue key).`);
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

    // Look for any element containing text that might be a label
    const allElements = card.querySelectorAll('*');
    for (const element of allElements) {
        if (element.textContent?.trim().toLowerCase() === 'auto-tested') {
            return true;
        }
    }
    
    return false;
}

// Prevent duplicate event listener registration
let hasInitialized = false;

chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
    if (request.action === "checkQAColumn") {
        checkQAColumn();
    }
});

// Auto-trigger when the page loads, with safeguard against multiple executions
window.addEventListener("load", () => {
    if (!hasInitialized) {
        console.log("[Extension] Page loaded, initiating QA column check");
        chrome.runtime.sendMessage({ action: "checkQAColumn" });
        hasInitialized = true;
    }
});