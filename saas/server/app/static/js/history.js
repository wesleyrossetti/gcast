// History page (SaaS)
async function loadHistory() {
  const tbody = document.getElementById('history-body');
  tbody.innerHTML = '<tr><td colspan="5" class="text-center py-3"><div class="spinner-border spinner-border-sm me-2"></div>Carregando...</td></tr>';
  try {
    const entries = await apiGet('/api/history?limit=100');
    if (!entries.length) {
      tbody.innerHTML = '<tr><td colspan="5" class="text-center text-muted py-4">Sem registros</td></tr>';
      return;
    }
    tbody.innerHTML = entries.map(e => `
      <tr>
        <td class="text-muted small text-nowrap">${new Date(e.timestamp).toLocaleString('pt-BR')}</td>
        <td><span class="badge bg-secondary">${e.device_name || e.device_uuid || '—'}</span></td>
        <td class="small">${e.action}</td>
        <td class="small text-muted">${JSON.stringify(e.details)}</td>
        <td>${e.success
          ? '<span class="badge bg-success"><i class="bi bi-check"></i></span>'
          : `<span class="badge bg-danger" title="${e.error || ''}"><i class="bi bi-x"></i></span>`
        }</td>
      </tr>
    `).join('');
  } catch (e) { tbody.innerHTML = `<tr><td colspan="5" class="text-center text-danger">${e.message}</td></tr>`; }
}
loadHistory();
