// ── Notifications panel ───────────────────────────────────────────────────────

const notifPanel = new bootstrap.Offcanvas(document.getElementById('notifPanel'));

document.getElementById('btn-notif').addEventListener('click', () => {
  notifPanel.show();
  loadNotifications();
});

document.getElementById('btn-mark-all-read')?.addEventListener('click', async () => {
  await fetch('/api/notifications/read-all', { method: 'POST' });
  loadNotifications();
  updateNotifBadge();
});

async function loadNotifications() {
  try {
    const items = await apiGet('/api/notifications');
    const list = document.getElementById('notif-list');
    if (!items.length) {
      list.innerHTML = '<p class="text-muted text-center mt-4">Nenhuma notificação</p>';
      return;
    }
    const iconMap = { info: 'bi-info-circle text-info', success: 'bi-check-circle text-success',
                      warning: 'bi-exclamation-triangle text-warning', error: 'bi-x-circle text-danger' };
    list.innerHTML = items.map(n => `
      <div class="notif-item ${n.read ? '' : 'unread'}">
        <div class="d-flex align-items-start gap-2">
          <i class="bi ${iconMap[n.type] || 'bi-info-circle'} mt-1"></i>
          <div class="flex-grow-1">
            <p class="mb-0 small">${n.message}</p>
            <small class="text-muted">${formatDateTime(n.timestamp)}</small>
          </div>
        </div>
      </div>
    `).join('');
    updateNotifBadge();
  } catch (e) { console.error('loadNotifications error', e); }
}

async function updateNotifBadge() {
  try {
    const data = await apiGet('/api/notifications/count');
    const badge = document.getElementById('notif-badge');
    if (data.count > 0) {
      badge.textContent = data.count;
      badge.classList.remove('d-none');
    } else {
      badge.classList.add('d-none');
    }
  } catch (e) { /* silent */ }
}

// ── Date formatting ───────────────────────────────────────────────────────────

function formatDateTime(iso) {
  if (!iso) return '—';
  return new Date(iso).toLocaleString('pt-BR');
}

function formatTime(seconds) {
  if (seconds == null) return '—';
  const m = Math.floor(seconds / 60);
  const s = Math.floor(seconds % 60);
  return `${m}:${s.toString().padStart(2, '0')}`;
}

// ── Init ──────────────────────────────────────────────────────────────────────
updateNotifBadge();
setInterval(updateNotifBadge, 15000);
