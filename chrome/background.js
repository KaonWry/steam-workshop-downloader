chrome.runtime.onInstalled.addListener(() => {
  chrome.contextMenus.create({
    id: 'add-to-workshop-queue',
    title: 'Add to Workshop Download Queue',
    contexts: ['link'],
    targetUrlPatterns: [
      '*://steamcommunity.com/sharedfiles/filedetails/*',
      '*://steamcommunity.com/workshop/filedetails/*',
    ],
  });
});

chrome.contextMenus.onClicked.addListener(async (info) => {
  if (info.menuItemId !== 'add-to-workshop-queue') return;

  const url = new URL(info.linkUrl);
  const workshopId = url.searchParams.get('id');
  if (!workshopId) return;

  try {
    const response = await fetch('http://127.0.0.1:5000/queue', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ workshop_id: workshopId }),
    });

    const data = await response.json();
    if (response.ok) {
      console.log(`Queued: ${data.workshop_title}`);
    } else {
      console.error('Queue error:', data.error);
    }
  } catch (err) {
    console.error('Server offline:', err);
  }
});
