// ── Single item page ────────────────────────────────────────────
const urlParams = new URLSearchParams(window.location.search);
const workshopId = urlParams.get('id');

if (workshopId) {
    const targetArea = document.querySelector('.game_area_purchase_margin') || document.querySelector('.workshopItemDetailsHeader');
    if (targetArea) {
        targetArea.appendChild(createQueueButton(workshopId));
    }
}

// ── Browse page ─────────────────────────────────────────────────
const workshopItems = document.querySelectorAll('#profileBlock > div > div.workshopBrowseItems > div.workshopItem');

for (const item of workshopItems) {
    const link = item.querySelector('a[href*="filedetails/?id="]');
    if (!link) continue;
    const idMatch = new URL(link.href).searchParams.get('id');
    if (!idMatch) continue;
    item.appendChild(createQueueButton(idMatch));
}

// ── Shared button factory ───────────────────────────────────────
function createQueueButton(wid) {
    const btn = document.createElement('a');
    btn.className = 'btn_green_white_innerfade btn_border_2px btn_medium';
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
            const response = await fetch('http://127.0.0.1:5000/queue', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ workshop_id: wid })
            });

            const data = await response.json();
            if (response.ok) {
                span.innerText = `✓ Queued: ${data.workshop_title}`;
                setTimeout(() => span.innerText = 'Add to Download Queue', 3000);
            } else {
                span.innerText = '❌ Error (See Console)';
                console.error("Queue Error:", data.error);
            }
        } catch (err) {
            span.innerText = '❌ Server Offline';
            console.error("Failed to connect to Python server:", err);
        }
    };

    return btn;
}