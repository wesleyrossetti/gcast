// ── State ─────────────────────────────────────────────────────────────────────
let devices = [];
let statusMap = {};
let pollInterval = null;
// Track when each device entered buffering: { device_id: timestamp }
const bufferingStartMap = {};
const BUFFERING_STUCK_SECS = 30;

// ── Bootstrap modals ──────────────────────────────────────────────────────────
const playModal = new bootstrap.Modal(document.getElementById('playModal'));

// ── Discovery ─────────────────────────────────────────────────────────────────
document.getElementById('btn-discover').addEventListener('click', () => {
  document.getElementById('discover-options').classList.toggle('show');
});

document.getElementById('btn-start-discover').addEventListener('click', discoverDevices);

async function discoverDevices() {
  const hostsRaw = document.getElementById('known-hosts').value.trim();
  const known_hosts = hostsRaw ? hostsRaw.split(',').map(h => h.trim()).filter(Boolean) : null;

  setStatusIndicator('loading', 'Descobrindo...');
  try {
    const body = known_hosts ? JSON.stringify(known_hosts) : '[]';
    const res = await fetch('/api/devices/discover', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: body,
    });
    if (!res.ok) throw new Error(res.statusText);
    devices = await res.json();
    renderDevices();
    setStatusIndicator('ok', `${devices.length} device(s)`);
    showToast(`${devices.length} device(s) encontrado(s)`, 'success');
    document.getElementById('discover-options').classList.remove('show');
    startPolling();
  } catch (e) {
    showToast('Erro na descoberta: ' + e.message, 'error');
    setStatusIndicator('error', 'Erro');
  }
}

// ── Rendering ─────────────────────────────────────────────────────────────────
function renderDevices() {
  const grid = document.getElementById('devices-grid');
  if (!devices.length) {
    grid.innerHTML = `<div class="col-12 text-center text-muted py-5" id="empty-state">
      <i class="bi bi-cast display-4 d-block mb-3 opacity-25"></i>
      <p>Nenhum device encontrado. Clique em <strong>Descobrir Devices</strong> para buscar Chromecasts na rede.</p>
    </div>`;
    return;
  }
  grid.innerHTML = devices.map(d => deviceCard(d)).join('');
  attachCardListeners();
}

function deviceCard(device) {
  const st = statusMap[device.device_id];
  const media = st?.media;
  const playerState = media?.player_state || 'UNKNOWN';
  const thumb = media?.thumbnail;
  const isPlaying = playerState === 'PLAYING' || playerState === 'BUFFERING';
  const volPct = st ? Math.round((st.volume_level || 0) * 100) : 50;
  const current = media?.current_time;
  const duration = media?.duration;
  const progress = (current && duration) ? Math.round((current / duration) * 100) : 0;

  // Buffering stuck detection
  const bufStart = bufferingStartMap[device.device_id];
  const bufferingSecs = bufStart ? Math.round((Date.now() - bufStart) / 1000) : 0;
  const isStuck = playerState === 'BUFFERING' && bufferingSecs >= BUFFERING_STUCK_SECS;

  return `
  <div class="col-xl-3 col-lg-4 col-md-6">
    <div class="device-card p-0 h-100 d-flex flex-column ${isPlaying ? 'playing' : ''}">
      <!-- Thumbnail / Placeholder -->
      ${thumb
        ? `<img src="${thumb}" class="device-thumb" alt="Thumbnail">`
        : `<div class="device-thumb-placeholder"><i class="bi bi-cast"></i></div>`
      }
      <!-- Progress bar -->
      <div class="progress progress-thin rounded-0 bg-secondary">
        <div class="progress-bar bg-danger" style="width:${progress}%"></div>
      </div>
      <!-- Body -->
      <div class="p-3 flex-grow-1 d-flex flex-column">
        <div class="d-flex justify-content-between align-items-start mb-2">
          <div>
            <h6 class="mb-0">${device.friendly_name}</h6>
            <small class="text-muted">${device.host} · ${device.model_name || 'Chromecast'}</small>
          </div>
          <div class="d-flex flex-column align-items-end gap-1">
            ${stateBadge(playerState, isStuck)}
            ${playerState === 'BUFFERING' ? `<small class="text-muted" style="font-size:0.7rem">${bufferingSecs}s</small>` : ''}
          </div>
        </div>

        ${isStuck ? `<div class="alert alert-warning alert-sm py-1 px-2 mb-2 d-flex align-items-center gap-2" style="font-size:0.8rem">
          <i class="bi bi-exclamation-triangle-fill"></i>
          <span>Buffering por ${bufferingSecs}s — pode estar travado</span>
          <button class="btn btn-sm btn-warning ms-auto py-0 btn-stop" data-id="${device.device_id}" title="Parar">
            <i class="bi bi-stop-fill"></i> Parar
          </button>
        </div>` : ''}

        ${media?.title ? `<p class="small mb-1 text-truncate text-muted">
          <i class="bi bi-music-note me-1"></i>${media.title}
          ${media.artist ? `<span class="opacity-50">– ${media.artist}</span>` : ''}
        </p>` : ''}

        ${(current != null && duration) ? `<small class="text-muted mb-2">
          ${formatTime(current)} / ${formatTime(duration)}
        </small>` : ''}

        <!-- Volume -->
        <div class="d-flex align-items-center gap-2 mb-3 mt-auto">
          <button class="btn btn-sm btn-outline-secondary p-1 btn-mute" data-id="${device.device_id}" data-muted="${st?.volume_muted ? '1':'0'}" title="${st?.volume_muted ? 'Desmutar':'Mutar'}">
            <i class="bi bi-volume-${st?.volume_muted ? 'mute' : 'up'}-fill"></i>
          </button>
          <input type="range" min="0" max="100" value="${volPct}"
                 class="volume-slider flex-grow-1 btn-volume"
                 data-id="${device.device_id}">
          <small class="text-muted" style="min-width:30px">${volPct}%</small>
        </div>

        <!-- Controls -->
        <div class="d-flex gap-1 justify-content-center flex-wrap">
          <button class="btn btn-sm btn-icon btn-play-url" data-id="${device.device_id}" title="Reproduzir URL">
            <i class="bi bi-link-45deg"></i>
          </button>
          <button class="btn btn-sm btn-icon btn-play" data-id="${device.device_id}" title="Play">
            <i class="bi bi-play-fill"></i>
          </button>
          <button class="btn btn-sm btn-icon btn-pause" data-id="${device.device_id}" title="Pause">
            <i class="bi bi-pause-fill"></i>
          </button>
          <button class="btn btn-sm btn-outline-danger btn-stop" data-id="${device.device_id}" title="Stop">
            <i class="bi bi-stop-fill"></i>
          </button>
        </div>
      </div>
    </div>
  </div>`;
}

function stateBadge(state, stuck = false) {
  const map = {
    PLAYING:   ['badge-playing', 'Reproduzindo'],
    PAUSED:    ['badge-paused', 'Pausado'],
    BUFFERING: ['badge-buffering', stuck ? 'Buffering travado!' : 'Buffering'],
    IDLE:      ['badge-idle', 'Inativo'],
    UNKNOWN:   ['badge-unknown', 'Desconhecido'],
  };
  const [cls, label] = map[state] || map.UNKNOWN;
  return `<span class="badge ${cls}${stuck ? ' stuck' : ''}">${label}</span>`;
}

// ── Event Listeners ───────────────────────────────────────────────────────────
function attachCardListeners() {
  // Play URL
  document.querySelectorAll('.btn-play-url').forEach(btn => {
    btn.addEventListener('click', () => {
      document.getElementById('play-device-id').value = btn.dataset.id;
      playModal.show();
    });
  });

  // Play / Pause / Stop
  document.querySelectorAll('.btn-play').forEach(btn => {
    btn.addEventListener('click', () => mediaAction('play', btn.dataset.id));
  });
  document.querySelectorAll('.btn-pause').forEach(btn => {
    btn.addEventListener('click', () => mediaAction('pause', btn.dataset.id));
  });
  document.querySelectorAll('.btn-stop').forEach(btn => {
    btn.addEventListener('click', () => mediaAction('stop', btn.dataset.id));
  });

  // Volume
  document.querySelectorAll('.btn-volume').forEach(slider => {
    slider.addEventListener('change', async () => {
      const level = parseInt(slider.value) / 100;
      try {
        await apiPost('/api/control/volume', { device_id: slider.dataset.id, level });
        slider.nextElementSibling.textContent = slider.value + '%';
      } catch (e) { showToast('Erro volume: ' + e.message, 'error'); }
    });
  });

  // Mute
  document.querySelectorAll('.btn-mute').forEach(btn => {
    btn.addEventListener('click', async () => {
      const muted = btn.dataset.muted === '1';
      const action = muted ? 'unmute' : 'mute';
      try {
        await apiPost(`/api/control/${action}`, { device_id: btn.dataset.id });
        // status will update on next poll
      } catch (e) { showToast('Erro mute: ' + e.message, 'error'); }
    });
  });
}

async function mediaAction(action, deviceId) {
  try {
    await apiPost(`/api/media/${action}`, { device_id: deviceId });
    showToast(action.charAt(0).toUpperCase() + action.slice(1) + ' enviado', 'info');
    pollStatuses();
  } catch (e) { showToast(`Erro ${action}: ` + e.message, 'error'); }
}

// ── YouTube helpers ───────────────────────────────────────────────────────────
function extractYouTubeId(input) {
  input = input.trim();
  // Already a bare ID (11 chars, alphanumeric + - _)
  if (/^[A-Za-z0-9_-]{11}$/.test(input)) return input;
  try {
    const url = new URL(input);
    if (url.hostname === 'youtu.be') return url.pathname.slice(1).split('?')[0];
    if (url.searchParams.get('v')) return url.searchParams.get('v');
    // /shorts/ID or /embed/ID
    const m = url.pathname.match(/\/(?:shorts|embed|v)\/([A-Za-z0-9_-]{11})/);
    if (m) return m[1];
  } catch (_) { /* not a URL */ }
  return null;
}

// Preview thumbnail when user types a YouTube URL
document.getElementById('play-yt-url').addEventListener('input', function () {
  const id = extractYouTubeId(this.value);
  const preview = document.getElementById('yt-preview');
  const iframe = document.getElementById('yt-iframe');
  if (id) {
    iframe.src = `https://www.youtube.com/embed/${id}`;
    preview.classList.remove('d-none');
  } else {
    iframe.src = '';
    preview.classList.add('d-none');
  }
});


async function confirmPlay() {
  try {
    const deviceId = document.getElementById('play-device-id').value;
    const activeTabEl = document.querySelector('#playTabs .nav-link.active');
    const activeTab = activeTabEl ? activeTabEl.dataset.bsTarget : null;

    if (activeTab === '#tab-youtube') {
      const raw = document.getElementById('play-yt-url').value.trim();
      const videoId = extractYouTubeId(raw);
      if (!videoId) { showToast('URL do YouTube inválida', 'warning'); return; }
      await apiPost('/api/media/play-youtube', { device_id: deviceId, video_id: videoId });
    } else if (activeTab === '#tab-web') {
      const url = document.getElementById('cast-web-url').value.trim();
      if (!url) { showToast('Informe a URL da página', 'warning'); return; }
      await apiPost('/api/media/cast-web', {
        device_id: deviceId,
        url,
        force: document.getElementById('cast-web-force').checked,
        reload_seconds: parseInt(document.getElementById('cast-web-reload').value) || 0,
      });
    } else {
      const url = document.getElementById('play-url').value.trim();
      if (!url) { showToast('Informe a URL da mídia', 'warning'); return; }
      await apiPost('/api/media/play-url', {
        device_id: deviceId,
        url,
        content_type: document.getElementById('play-content-type').value,
        title: document.getElementById('play-title').value.trim() || null,
        thumb: document.getElementById('play-thumb').value.trim() || null,
      });
    }
    playModal.hide();
    showToast('Reprodução iniciada!', 'success');
    pollStatuses();
  } catch (e) {
    console.error('[confirmPlay] falhou:', e);
    showToast('Erro ao reproduzir: ' + e.message, 'error');
  }
}

document.getElementById('btn-confirm-play').addEventListener('click', confirmPlay);

// Atalho: apertar Enter em qualquer campo de URL do modal também dispara a reprodução,
// como caminho alternativo ao clique no botão.
['play-yt-url', 'play-url', 'cast-web-url'].forEach((id) => {
  document.getElementById(id).addEventListener('keydown', (ev) => {
    if (ev.key === 'Enter') {
      ev.preventDefault();
      confirmPlay();
    }
  });
});

// ── Polling ───────────────────────────────────────────────────────────────────
function startPolling() {
  if (pollInterval) clearInterval(pollInterval);
  pollStatuses();
  pollInterval = setInterval(pollStatuses, 5000);
}

async function pollStatuses() {
  // Refresh device list so auto-discovered devices appear without manual trigger
  try {
    const latest = await apiGet('/api/devices');
    const prevIds = devices.map(d => d.device_id).sort().join();
    const newIds  = latest.map(d => d.device_id).sort().join();
    if (prevIds !== newIds) {
      devices = latest;
    }
  } catch (e) { /* skip */ }

  if (!devices.length) {
    setStatusIndicator('loading', 'Aguardando dispositivos...');
    return;
  }

  for (const d of devices) {
    try {
      const st = await apiGet(`/api/devices/${d.device_id}/status`);
      const prevState = statusMap[d.device_id]?.media?.player_state;
      statusMap[d.device_id] = st;

      const newState = st?.media?.player_state;
      if (newState === 'BUFFERING') {
        if (prevState !== 'BUFFERING') {
          // Just entered buffering — record start time
          bufferingStartMap[d.device_id] = Date.now();
        }
        const secs = Math.round((Date.now() - bufferingStartMap[d.device_id]) / 1000);
        if (secs === BUFFERING_STUCK_SECS) {
          showToast(
            `⚠️ "${d.friendly_name}" está em buffering há ${secs}s. Clique em <strong>Parar</strong> no card para forçar parada.`,
            'warning'
          );
        }
      } else {
        delete bufferingStartMap[d.device_id];
      }
    } catch (e) { /* skip if device unreachable */ }
  }
  renderDevices();
  setStatusIndicator('ok', `${devices.length} device(s) · ${new Date().toLocaleTimeString('pt-BR')}`);
}

// ── Status indicator ──────────────────────────────────────────────────────────
function setStatusIndicator(state, text) {
  const el = document.getElementById('status-indicator');
  el.className = 'badge';
  if (state === 'loading') el.classList.add('bg-warning', 'text-dark');
  else if (state === 'ok')  el.classList.add('bg-success');
  else                       el.classList.add('bg-danger');
  el.innerHTML = `<i class="bi bi-circle-fill me-1"></i>${text}`;
}

// ── Init ──────────────────────────────────────────────────────────────────────
(async () => {
  // load whatever is already cached (fast path)
  try {
    devices = await apiGet('/api/devices');
    if (devices.length) renderDevices();
  } catch (e) { /* empty */ }
  // always start polling so auto-discovered devices appear automatically
  startPolling();
})();
