const QUEUE_BTN_CLASS = 'steamcmd-queue-btn';

function injectButtons() {
    // ── Single item page ────────────────────────────────────────────
    const workshopId = new URLSearchParams(window.location.search).get('id');

    if (workshopId) {
        const targetArea = document.querySelector('.game_area_purchase_margin') || document.querySelector('.workshopItemDetailsHeader');
        if (targetArea && !targetArea.querySelector('.' + QUEUE_BTN_CLASS)) {
            targetArea.appendChild(createQueueButton(workshopId));
        }
    }

    // ── Browse page ─────────────────────────────────────────────────
    const workshopItems = document.querySelectorAll('#profileBlock > div > div.workshopBrowseItems > div.workshopItem');

    for (const item of workshopItems) {
        if (item.querySelector('.' + QUEUE_BTN_CLASS)) continue;
        const link = item.querySelector('a[href*="filedetails/?id="]');
        if (!link) continue;
        const idMatch = new URL(link.href).searchParams.get('id');
        if (!idMatch) continue;
        item.appendChild(createQueueButton(idMatch));
    }
}

// Run on initial load
injectButtons();

// Re-run when Steam does client-side navigation (pushState/replaceState)
let lastUrl = location.href;
new MutationObserver(() => {
    if (location.href !== lastUrl) {
        lastUrl = location.href;
        // Retry several times — Steam can be slow to render the new page
        for (const delay of [300, 800, 1500, 3000]) {
            setTimeout(injectButtons, delay);
        }
    }
}).observe(document.body, { childList: true, subtree: true });

// ── Shared button factory ───────────────────────────────────────
function createQueueButton(wid) {
    const btn = document.createElement('a');
    btn.className = 'btn_green_white_innerfade btn_border_2px btn_medium ' + QUEUE_BTN_CLASS;
    btn.style.marginTop = '10px';
    btn.style.display = 'block';
    btn.style.textAlign = 'center';

    const span = document.createElement('span');
    span.innerText = 'Add to Download Queue';
    btn.appendChild(span);

    btn.onclick = async (e) => {
        e.preventDefault();
        span.innerText = 'Adding to queue...';

        try {
            const response = await browser.runtime.sendMessage({ action: 'addToQueue', workshopId: wid });
            if (response.success) {
                span.innerText = `✓ Queued: ${response.data.workshop_title}`;
                setTimeout(() => span.innerText = 'Add to Download Queue', 3000);
            } else {
                if (response.offline) {
                    span.innerText = '❌ Server Offline';
                } else {
                    span.innerText = '❌ Error (See Console)';
                }
                console.error("Queue Error:", response.error);
            }
        } catch (err) {
            span.innerText = '❌ Server Offline';
            console.error("Failed to communicate with background script:", err);
        }
    };

    return btn;
}