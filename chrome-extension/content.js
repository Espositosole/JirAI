function checkInProgressColumn() {
    console.log("[checkInProgressColumn] Card found:", issueKey);
    console.log("[checkInProgressColumn] Column title:", columnTitle);
    const cards = document.querySelectorAll('[data-testid="platform-board-kit.ui.card.card"]');
    cards.forEach(card => {
        const columnContainer = card.closest('[data-testid^="platform-board-kit.ui.column"]');
        const columnTitleEl = columnContainer?.querySelector('[data-testid*="column-name"]');
        const columnTitle = columnTitleEl?.textContent?.trim();
        const normalized = columnTitle?.toLowerCase();

        const issueKey = card.getAttribute("data-issue-key") || card.textContent?.match(/[A-Z]+-\\d+/)?.[0];
        if (normalized?.includes("in progress") && issueKey) {
            chrome.runtime.sendMessage({
                action: "triggerAgent",
                issueKey: issueKey,
                status: "in progress"
            });
        }

        if (!seen.has(columnTitle)) {
            seen.add(columnTitle);
            console.log("[Extension] Column title seen:", columnTitle);
  }
    });
}

function checkQAColumn() {
    const cards = document.querySelectorAll('[data-testid="platform-board-kit.ui.card.card"]');
    cards.forEach(card => {
        const columnContainer = card.closest('[data-testid^="platform-board-kit.ui.column"]');
        const columnTitleEl = columnContainer?.querySelector('[data-testid*="column-name"]');
        const columnTitle = columnTitleEl?.textContent?.trim();
        const normalized = columnTitle?.toLowerCase();

        const issueKey = card.getAttribute("data-issue-key") || card.textContent?.match(/[A-Z]+-\\d+/)?.[0];
        if (normalized?.includes("qa") && issueKey) {
            const hasTestedLabel = checkForTestedLabel(card);
            chrome.runtime.sendMessage({
                action: "triggerAgent",
                issueKey: issueKey,
                status: "qa",
                hasTestedLabel: hasTestedLabel
            });
        }
    });
}

function checkForTestedLabel(card) {
    const labels = card.querySelectorAll('.label');
    for (const label of labels) {
        const labelText = label.textContent?.trim().toLowerCase();
        if (labelText === 'tested' || labelText === 'auto-tested') return true;
    }

    const description = card.querySelector('.ghx-description');
    if (description && description.textContent.toLowerCase().includes('auto-tested')) return true;

    const lozenges = card.querySelectorAll('.lozenge');
    for (const lozenge of lozenges) {
        const text = lozenge.textContent?.trim().toLowerCase();
        if (text === 'tested' || text === 'auto-tested') return true;
    }

    const allElements = card.querySelectorAll('*');
    for (const el of allElements) {
        if (el.textContent?.trim().toLowerCase() === 'auto-tested') return true;
    }

    return false;
}

function debounce(func, delay) {
    let timeout;
    return function () {
        clearTimeout(timeout);
        timeout = setTimeout(() => func(), delay);
    };
}

const debouncedCheckColumns = debounce(() => {
    checkInProgressColumn();
    checkQAColumn();
}, 500);

chrome.runtime.onMessage.addListener((request) => {
    if (request.action === "checkQAColumn") {
        checkQAColumn();
    }
    if (request.action === "checkInProgressColumn") {
        checkInProgressColumn();
    }
});

window.addEventListener("load", () => {
    console.log("[Extension] content.js loaded");
    checkInProgressColumn();  
    checkQAColumn();

    const observer = new MutationObserver((mutations) => {
        console.log("[Extension] DOM mutated — checking columns");
        debouncedCheckColumns();
    });

    observer.observe(document.body, {
        childList: true,
        subtree: true
    });
});

