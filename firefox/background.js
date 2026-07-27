async function addToQueue(workshopId) {
  try {
    const response = await fetch('http://127.0.0.1:5000/queue', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ workshop_id: workshopId }),
    });

    const data = await response.json();
    if (response.ok) {
      return { success: true, data };
    } else {
      return { success: false, error: data.error };
    }
  } catch (err) {
    return { success: false, offline: true, error: err.message || err };
  }
}

browser.action.onClicked.addListener(() => {
  browser.tabs.create({ url: 'http://localhost:5000' });
});

browser.runtime.onInstalled.addListener(() => {
  browser.contextMenus.create({
    id: 'add-to-workshop-queue',
    title: 'Add to Workshop Download Queue',
    contexts: ['link'],
    targetUrlPatterns: [
      '*://steamcommunity.com/sharedfiles/filedetails/*',
      '*://steamcommunity.com/workshop/filedetails/*',
    ],
  });
});

browser.contextMenus.onClicked.addListener(async (info) => {
  if (info.menuItemId !== 'add-to-workshop-queue') return;

  const url = new URL(info.linkUrl);
  const workshopId = url.searchParams.get('id');
  if (!workshopId) return;

  const res = await addToQueue(workshopId);
  if (res.success) {
    console.log(`Queued: ${res.data.workshop_title}`);
  } else {
    console.error('Queue error:', res.error);
  }
});

browser.runtime.onMessage.addListener((message, sender) => {
  if (message.action === 'addToQueue') {
    return addToQueue(message.workshopId);
  }
});
