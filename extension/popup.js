const API = 'http://127.0.0.1:5000';
const contentDiv = document.getElementById('content');
const statusDiv = document.getElementById('status');

async function loadQueue() {
  statusDiv.textContent = '';
  try {
    const resp = await fetch(`${API}/queue`);
    const items = await resp.json();
    render(items);
  } catch {
    contentDiv.innerHTML = '<p class="empty">Server offline</p>';
  }
}

function render(items) {
  if (!items.length) {
    contentDiv.innerHTML = '<p class="empty">Queue is empty. Visit a Workshop page and click "Add to Download Queue".</p>';
    return;
  }

  let html = `<table>
    <tr><th>Game</th><th>Workshop Item</th><th>Link</th><th></th></tr>`;

  for (const item of items) {
    html += `<tr>
      <td>${escapeHtml(item.game_name)}</td>
      <td>${escapeHtml(item.workshop_title)}</td>
      <td><a href="${escapeHtml(item.workshop_link)}" target="_blank">Open</a></td>
      <td><button class="remove-btn" data-id="${item.id}" title="Remove">✕</button></td>
    </tr>`;
  }

  html += '</table>';
  html += `<button id="download-all">Download All (${items.length} items)</button>`;
  contentDiv.innerHTML = html;

  // Remove buttons
  for (const btn of contentDiv.querySelectorAll('.remove-btn')) {
    btn.addEventListener('click', async () => {
      await fetch(`${API}/queue/${btn.dataset.id}`, { method: 'DELETE' });
      loadQueue();
    });
  }

  // Download All button
  document.getElementById('download-all').addEventListener('click', downloadAll);
}

async function downloadAll() {
  const btn = document.getElementById('download-all');
  btn.disabled = true;
  btn.textContent = 'Downloading...';
  statusDiv.textContent = 'Starting downloads...';

  let done = 0;
  let errors = 0;

  while (true) {
    let resp;
    try {
      resp = await fetch(`${API}/download-next`, { method: 'POST' });
    } catch {
      statusDiv.textContent = 'Server offline';
      break;
    }

    // Queue empty — we're done
    if (resp.status === 400) {
      break;
    }

    if (!resp.ok) {
      errors++;
      const data = await resp.json();
      console.error('Download error:', data.error);
      statusDiv.textContent = `Error on item: ${data.error}`;
      continue;
    }

    // Got result JSON — trigger browser download from server URL
    const result = await resp.json();
    chrome.downloads.download({
      url: `${API}/download-file/${result.workshop_id}`,
    });
    done++;
    statusDiv.textContent = `Downloaded ${done}...`;
  }

  statusDiv.textContent = `Done! ${done} downloaded` + (errors ? `, ${errors} failed` : '');
  loadQueue();
}

function escapeHtml(str) {
  const div = document.createElement('div');
  div.appendChild(document.createTextNode(str));
  return div.innerHTML;
}

loadQueue();
