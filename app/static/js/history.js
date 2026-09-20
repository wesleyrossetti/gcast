// ── History page ──────────────────────────────────────────────────────────────

const actionLabels = {
  play: 'Play', pause: 'Pause', stop: 'Stop', seek: 'Seek',
  volume: 'Volume', mute: 'Mutar', unmute: 'Desmutar',
  discover: 'Descoberta', connect: 'Conectado', disconnect: 'Desconectado',
};

const actionIcons = {
  play: 'bi-play-fill text-success', pause: 'bi-pause-fill text-warning',
  stop: 'bi-stop-fill text-danger', seek: 'bi-skip-forward-fill text-info',
  volume: 'bi-volume-up-fill text-info', mute: 'bi-volume-mute-fill text-secondary',
  unmute: 'bi-volume-up text-secondary', discover: 'bi-search text-primary',
  connect: 'bi-plug text-success', disconnect: 'bi-plug text-danger',
};

async function loadHistory() {
  const deviceId = document.getElementById('filter-device').value;
  const limit = document.getElementById('filter-limit').value;
  let url = `/api/history?limit=${limit}`;
  if (deviceId) url += `&device_id=${encodeURIComponent(deviceId)}`;

  const tbody = document.getElementById('history-body');
  tbody.innerHTML = '<tr><td colspan="5" class="text-center text-muted py-3"><div class="spinner-border spinner-border-sm me-2"></div>Carregando...</td></tr>';

  try {
    const entries = await apiGet(url);
    if (!entries.length) {
      tbody.innerHTML = '<tr><td colspan="5" class="text-center text-muted py-4">Nenhum registro encontrado</td></tr>';
      return;
    }
    tbody.innerHTML = entries.map(e => `
      <tr>
        <td class="text-muted small text-nowrap">${formatDateTime(e.timestamp)}</td>
        <td><span class="badge bg-secondary">${e.device_name || e.device_id}</span></td>
        <td><i class="bi ${actionIcons[e.action] || 'bi-gear'} me-1"></i>${actionLabels[e.action] || e.action}</td>
        <td class="small text-muted">${formatDetails(e.details)}</td>
        <td>${e.success
          ? '<span class="badge bg-success"><i class="bi bi-check"></i></span>'
          : `<span class="badge bg-danger" title="${e.error || ''}"><i class="bi bi-x"></i></span>`
        }</td>
      </tr>
    `).join('');
  } catch (err) {
    tbody.innerHTML = `<tr><td colspan="5" class="text-center text-danger py-4">Erro: ${err.message}</td></tr>`;
  }
}

function formatDetails(details) {
  if (!details || !Object.keys(details).length) return '—';
  return Object.entries(details)
    .map(([k, v]) => `<span class="me-2"><b>${k}:</b> ${v}</span>`)
    .join('');
}

async function loadDeviceOptions() {
  try {
    const devs = await apiGet('/api/devices');
    const sel = document.getElementById('filter-device');
    devs.forEach(d => {
      const opt = document.createElement('option');
      opt.value = d.device_id;
      opt.textContent = d.friendly_name;
      sel.appendChild(opt);
    });
  } catch (e) { /* ignore */ }
}

document.getElementById('btn-filter').addEventListener('click', loadHistory);

// ── Init ──────────────────────────────────────────────────────────────────────
loadDeviceOptions();
loadHistory();
