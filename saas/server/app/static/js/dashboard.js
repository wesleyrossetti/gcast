// Dashboard SaaS – polls /api/devices, sends commands via REST (JWT cookie auto-included)

let devices = [];
let statusMap = {};
let pollInterval = null;
const bufferingStartMap = {};
const BUFFERING_STUCK_SECS = 30;

const playModal = new bootstrap.Modal(document.getElementById('playModal'));

// ── Discovery ─────────────────────────────────────────────────────────────────
document.getElementById('btn-discover').addEventListener('click', async () => {
  setIndicator('loading', 'Descobrindo...');
  try {
    const r = await apiPost('/api/devices/discover', {});
    showToast(`Descoberta solicitada aos agentes online`, 'success');
  } catch (e) { showToast('Erro: ' + e.message, 'error'); }
  pollStatuses();
});

// ── Render ────────────────────────────────────────────────────────────────────
function renderDevices() {
  const grid = document.getElementById('devices-grid');
  if (!devices.length) {
    grid.innerHTML = `<div class="col-12 text-center text-muted py-5">
      <i class="bi bi-cast display-4 d-block mb-3 opacity-25"></i>
      <p>Nenhum device encontrado. Certifique-se que um <a href="/agents" class="text-danger">agente</a> está online e clique em <strong>Descobrir Devices</strong>.</p>
    </div>`;
    return;
  }
  grid.innerHTML = devices.map(deviceCard).join('');
  attachListeners();
}

function deviceCard(d) {
  const ps     = d.player_state || 'UNKNOWN';
  const isPlay = ps === 'PLAYING' || ps === 'BUFFERING';
  const volPct = Math.round((d.volume_level || 0) * 100);
  const prog   = (d.current_time && d.duration) ? Math.round((d.current_time / d.duration) * 100) : 0;

  const bufStart = bufferingStartMap[d.device_uuid];
  const bufSecs  = bufStart ? Math.round((Date.now() - bufStart) / 1000) : 0;
  const isStuck  = ps === 'BUFFERING' && bufSecs >= BUFFERING_STUCK_SECS;

  const onlineDot = d.is_online
    ? '<span class="badge bg-success ms-1" title="Agente online"><i class="bi bi-circle-fill" style="font-size:.5rem"></i></span>'
    : '<span class="badge bg-secondary ms-1" title="Agente offline"><i class="bi bi-circle-fill" style="font-size:.5rem"></i></span>';

  return `
  <div class="col-xl-3 col-lg-4 col-md-6">
    <div class="device-card p-0 h-100 d-flex flex-column ${isPlay ? 'playing' : ''}">
      ${d.thumbnail
        ? `<img src="${d.thumbnail}" class="device-thumb" alt="">`
        : `<div class="device-thumb-placeholder"><i class="bi bi-cast"></i></div>`}
      <div class="progress progress-thin rounded-0 bg-secondary">
        <div class="progress-bar bg-danger" style="width:${prog}%"></div>
      </div>
      <div class="p-3 flex-grow-1 d-flex flex-column">
        <div class="d-flex justify-content-between mb-2">
          <div>
            <h6 class="mb-0">${d.friendly_name || d.device_uuid}${onlineDot}</h6>
            <small class="text-muted">${d.host || ''} · ${d.model_name || 'Chromecast'}</small>
          </div>
          <div class="d-flex flex-column align-items-end gap-1">
            ${stateBadge(ps, isStuck)}
            ${ps === 'BUFFERING' ? `<small class="text-muted" style="font-size:.7rem">${bufSecs}s</small>` : ''}
          </div>
        </div>
        ${isStuck ? `<div class="alert alert-warning py-1 px-2 mb-2 d-flex align-items-center gap-2" style="font-size:.8rem">
          <i class="bi bi-exclamation-triangle-fill"></i><span>Buffering travado (${bufSecs}s)</span>
          <button class="btn btn-sm btn-warning ms-auto py-0 btn-stop" data-uuid="${d.device_uuid}">
            <i class="bi bi-stop-fill"></i> Parar
          </button></div>` : ''}
        ${d.title ? `<p class="small text-muted text-truncate mb-1"><i class="bi bi-music-note me-1"></i>${d.title}</p>` : ''}
        ${(d.current_time != null && d.duration) ? `<small class="text-muted mb-2">${formatTime(d.current_time)} / ${formatTime(d.duration)}</small>` : ''}
        <div class="d-flex align-items-center gap-2 mb-3 mt-auto">
          <button class="btn btn-sm btn-outline-secondary p-1 btn-mute" data-uuid="${d.device_uuid}" data-muted="${d.volume_muted ? '1' : '0'}">
            <i class="bi bi-volume-${d.volume_muted ? 'mute' : 'up'}-fill"></i>
          </button>
          <input type="range" min="0" max="100" value="${volPct}" class="volume-slider flex-grow-1 btn-volume" data-uuid="${d.device_uuid}">
          <small class="text-muted" style="min-width:30px">${volPct}%</small>
        </div>
        <div class="d-flex gap-1 justify-content-center flex-wrap">
          <button class="btn btn-sm btn-icon btn-play-url" data-uuid="${d.device_uuid}" title="Reproduzir">
            <i class="bi bi-play-circle"></i>
          </button>
          <button class="btn btn-sm btn-icon btn-play" data-uuid="${d.device_uuid}" title="Play"><i class="bi bi-play-fill"></i></button>
          <button class="btn btn-sm btn-icon btn-pause" data-uuid="${d.device_uuid}" title="Pause"><i class="bi bi-pause-fill"></i></button>
          <button class="btn btn-sm btn-outline-danger btn-stop" data-uuid="${d.device_uuid}" title="Stop"><i class="bi bi-stop-fill"></i></button>
        </div>
      </div>
    </div>
  </div>`;
}

function stateBadge(state, stuck = false) {
  const m = {
    PLAYING:   ['badge-playing', 'Reproduzindo'],
    PAUSED:    ['badge-paused', 'Pausado'],
    BUFFERING: ['badge-buffering', stuck ? 'Buffering travado!' : 'Buffering'],
    IDLE:      ['badge-idle', 'Inativo'],
    UNKNOWN:   ['badge-unknown', 'Desconhecido'],
  };
  const [cls, lbl] = m[state] || m.UNKNOWN;
  return `<span class="badge ${cls}${stuck ? ' stuck' : ''}">${lbl}</span>`;
}

function attachListeners() {
  document.querySelectorAll('.btn-play-url').forEach(b => b.addEventListener('click', () => {
    document.getElementById('play-device-uuid').value = b.dataset.uuid;
    playModal.show();
  }));
  document.querySelectorAll('.btn-play').forEach(b => b.addEventListener('click', () => mediaCmd('play', b.dataset.uuid)));
  document.querySelectorAll('.btn-pause').forEach(b => b.addEventListener('click', () => mediaCmd('pause', b.dataset.uuid)));
  document.querySelectorAll('.btn-stop').forEach(b => b.addEventListener('click', () => mediaCmd('stop', b.dataset.uuid)));
  document.querySelectorAll('.btn-mute').forEach(b => b.addEventListener('click', async () => {
    const muted = b.dataset.muted === '1';
    try { await apiPost(`/api/control/${muted ? 'unmute' : 'mute'}`, { device_uuid: b.dataset.uuid }); }
    catch (e) { showToast('Erro: ' + e.message, 'error'); }
  }));
  document.querySelectorAll('.btn-volume').forEach(s => s.addEventListener('change', async () => {
    try {
      await apiPost('/api/control/volume', { device_uuid: s.dataset.uuid, level: parseInt(s.value) / 100 });
      s.nextElementSibling.textContent = s.value + '%';
    } catch (e) { showToast('Erro volume: ' + e.message, 'error'); }
  }));
}

async function mediaCmd(action, uuid) {
  try { await apiPost(`/api/media/${action}`, { device_uuid: uuid }); pollStatuses(); }
  catch (e) { showToast(`Erro ${action}: ` + e.message, 'error'); }
}

// ── YouTube helpers ───────────────────────────────────────────────────────────
function extractYouTubeId(input) {
  input = input.trim();
  if (/^[A-Za-z0-9_-]{11}$/.test(input)) return input;
  try {
    const url = new URL(input);
    if (url.hostname === 'youtu.be') return url.pathname.slice(1).split('?')[0];
    if (url.searchParams.get('v')) return url.searchParams.get('v');
    const m = url.pathname.match(/\/(?:shorts|embed|v)\/([A-Za-z0-9_-]{11})/);
    if (m) return m[1];
  } catch (_) {}
  return null;
}

document.getElementById('play-yt-url').addEventListener('input', function () {
  const id = extractYouTubeId(this.value);
  const preview = document.getElementById('yt-preview');
  document.getElementById('yt-iframe').src = id ? `https://www.youtube.com/embed/${id}` : '';
  preview.classList.toggle('d-none', !id);
});

document.getElementById('btn-confirm-play').addEventListener('click', async () => {
  const uuid = document.getElementById('play-device-uuid').value;
  const tab  = document.querySelector('#playTabs .nav-link.active').dataset.bsTarget;
  try {
    if (tab === '#tab-youtube') {
      const id = extractYouTubeId(document.getElementById('play-yt-url').value);
      if (!id) { showToast('URL inválida', 'warning'); return; }
      await apiPost('/api/media/play-youtube', { device_uuid: uuid, video_id: id });
    } else {
      const url = document.getElementById('play-url').value.trim();
      if (!url) { showToast('Informe a URL', 'warning'); return; }
      await apiPost('/api/media/play-url', {
        device_uuid: uuid, url,
        content_type: document.getElementById('play-content-type').value,
        title: document.getElementById('play-title').value.trim() || null,
      });
    }
    playModal.hide();
    showToast('Reprodução iniciada!', 'success');
    pollStatuses();
  } catch (e) { showToast('Erro: ' + e.message, 'error'); }
});

// ── Polling ───────────────────────────────────────────────────────────────────
async function pollStatuses() {
  try {
    const list = await apiGet('/api/devices');
    for (const d of list) {
      const prev = devices.find(x => x.device_uuid === d.device_uuid);
      if (d.player_state === 'BUFFERING') {
        if (!prev || prev.player_state !== 'BUFFERING') {
          bufferingStartMap[d.device_uuid] = Date.now();
        }
        const secs = Math.round((Date.now() - bufferingStartMap[d.device_uuid]) / 1000);
        if (secs === BUFFERING_STUCK_SECS) {
          showToast(`⚠️ "${d.friendly_name}" em buffering há ${secs}s`, 'warning');
        }
      } else {
        delete bufferingStartMap[d.device_uuid];
      }
    }
    devices = list;
    renderDevices();
    setIndicator('ok', `${devices.length} device(s) · ${new Date().toLocaleTimeString('pt-BR')}`);
  } catch (e) { setIndicator('error', 'Erro de conexão'); }
}

function setIndicator(state, text) {
  const el = document.getElementById('status-indicator');
  el.className = 'badge';
  if (state === 'loading') el.classList.add('bg-warning', 'text-dark');
  else if (state === 'ok')  el.classList.add('bg-success');
  else                       el.classList.add('bg-danger');
  el.innerHTML = `<i class="bi bi-circle-fill me-1"></i>${text}`;
}

// ── Helpers ───────────────────────────────────────────────────────────────────
function formatTime(s) {
  if (s == null) return '—';
  return `${Math.floor(s/60)}:${String(Math.floor(s%60)).padStart(2,'0')}`;
}

// ── Init ──────────────────────────────────────────────────────────────────────
pollStatuses();
setInterval(pollStatuses, 5000);
