// ── Schedule page ─────────────────────────────────────────────────────────────

const scheduleModal = new bootstrap.Modal(document.getElementById('scheduleModal'));

const recurrenceLabel = { once: 'Uma vez', daily: 'Diário', weekly: 'Semanal' };
const actionLabel = {
  play: 'Play', pause: 'Pause', stop: 'Stop',
  volume: 'Volume', mute: 'Mutar', unmute: 'Desmutar',
};

// Show/hide volume field
document.getElementById('sched-action').addEventListener('change', function () {
  document.getElementById('sched-volume-group').style.display =
    this.value === 'volume' ? 'block' : 'none';
});

async function loadSchedules() {
  try {
    const list = await apiGet('/api/schedule');
    const container = document.getElementById('schedules-list');
    if (!list.length) {
      container.innerHTML = `<div class="col-12 text-center text-muted py-5">
        <i class="bi bi-calendar-x display-4 d-block mb-3 opacity-25"></i>
        <p>Nenhum agendamento criado.</p>
      </div>`;
      return;
    }
    container.innerHTML = list.map(s => `
      <div class="col-md-4">
        <div class="card bg-secondary bg-opacity-10 border-secondary h-100">
          <div class="card-body">
            <div class="d-flex justify-content-between align-items-start">
              <div>
                <h6 class="mb-1">${actionLabel[s.action] || s.action}
                  <span class="badge bg-secondary ms-1">${recurrenceLabel[s.recurrence]}</span>
                </h6>
                <p class="text-secondary small mb-0">Device: ${s.device_id}</p>
              </div>
              <button class="btn btn-sm btn-outline-danger btn-delete-schedule" data-id="${s.id}">
                <i class="bi bi-trash"></i>
              </button>
            </div>
            <hr class="my-2">
            <p class="mb-0 small">
              <i class="bi bi-clock me-1"></i>${formatDateTime(s.run_at)}
            </p>
            ${s.last_run ? `<p class="mb-0 small text-secondary">
              Última execução: ${formatDateTime(s.last_run)}</p>` : ''}
            ${!s.enabled ? '<span class="badge bg-secondary mt-1">Concluído</span>' : ''}
          </div>
        </div>
      </div>
    `).join('');

    document.querySelectorAll('.btn-delete-schedule').forEach(btn => {
      btn.addEventListener('click', async () => {
        if (!confirm('Remover este agendamento?')) return;
        try {
          await fetch(`/api/schedule/${btn.dataset.id}`, { method: 'DELETE' });
          showToast('Agendamento removido', 'success');
          loadSchedules();
        } catch (e) { showToast('Erro: ' + e.message, 'error'); }
      });
    });
  } catch (e) { showToast('Erro ao carregar agendamentos', 'error'); }
}

async function loadDevices() {
  try {
    const devs = await apiGet('/api/devices');
    const sel = document.getElementById('sched-device-id');
    devs.forEach(d => {
      const opt = document.createElement('option');
      opt.value = d.device_id;
      opt.textContent = d.friendly_name;
      sel.appendChild(opt);
    });
  } catch (e) { /* ignore */ }
}

document.getElementById('btn-save-schedule').addEventListener('click', async () => {
  const deviceId = document.getElementById('sched-device-id').value;
  const action = document.getElementById('sched-action').value;
  const runAt = document.getElementById('sched-run-at').value;
  const recurrence = document.getElementById('sched-recurrence').value;

  if (!deviceId || !runAt) {
    showToast('Preencha device e data/hora', 'warning');
    return;
  }

  const details = {};
  if (action === 'volume') {
    details.level = parseFloat(document.getElementById('sched-volume-level').value);
  }

  try {
    await apiPost('/api/schedule', {
      device_id: deviceId,
      action,
      run_at: new Date(runAt).toISOString(),
      recurrence,
      details,
    });
    scheduleModal.hide();
    showToast('Agendamento criado!', 'success');
    loadSchedules();
  } catch (e) { showToast('Erro: ' + e.message, 'error'); }
});

// ── Init ──────────────────────────────────────────────────────────────────────
loadDevices();
loadSchedules();
