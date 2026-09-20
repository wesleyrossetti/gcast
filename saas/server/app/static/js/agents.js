// Agents page
const newAgentModal = new bootstrap.Modal(document.getElementById('newAgentModal'));
const tokenModal    = new bootstrap.Modal(document.getElementById('tokenModal'));

async function loadAgents() {
  try {
    const agents = await apiGet('/api/agents');
    const container = document.getElementById('agents-list');
    if (!agents.length) {
      container.innerHTML = `<div class="col-12 text-center text-muted py-5">
        <i class="bi bi-cpu display-4 d-block mb-3 opacity-25"></i>
        <p>Nenhum agente criado.</p>
      </div>`;
      return;
    }
    container.innerHTML = agents.map(a => `
      <div class="col-md-4">
        <div class="card bg-secondary bg-opacity-10 border-secondary h-100">
          <div class="card-body">
            <div class="d-flex justify-content-between align-items-start">
              <div>
                <h6 class="mb-1">${a.name}
                  <span class="badge ${a.is_online ? 'bg-success' : 'bg-secondary'} ms-1">
                    ${a.is_online ? 'Online' : 'Offline'}
                  </span>
                </h6>
                <small class="text-secondary">ID: <code class="text-secondary">${a.id.slice(0,12)}…</code></small>
              </div>
              <button class="btn btn-sm btn-outline-danger btn-delete-agent" data-id="${a.id}">
                <i class="bi bi-trash"></i>
              </button>
            </div>
            <hr class="border-secondary my-2">
            <p class="mb-0 small text-secondary">
              <i class="bi bi-clock me-1"></i>Criado: ${new Date(a.created_at).toLocaleDateString('pt-BR')}
            </p>
            ${a.last_seen ? `<p class="mb-0 small text-secondary">
              <i class="bi bi-activity me-1"></i>Visto: ${new Date(a.last_seen).toLocaleString('pt-BR')}</p>` : ''}
          </div>
        </div>
      </div>
    `).join('');

    document.querySelectorAll('.btn-delete-agent').forEach(btn => {
      btn.addEventListener('click', async () => {
        if (!confirm('Remover este agente?')) return;
        try {
          await fetch(`/api/agents/${btn.dataset.id}`, { method: 'DELETE' });
          showToast('Agente removido', 'success');
          loadAgents();
        } catch (e) { showToast('Erro: ' + e.message, 'error'); }
      });
    });
  } catch (e) { showToast('Erro ao carregar agentes', 'error'); }
}

document.getElementById('btn-create-agent').addEventListener('click', async () => {
  const name = document.getElementById('agent-name').value.trim();
  if (!name) { showToast('Informe um nome', 'warning'); return; }
  try {
    const agent = await apiPost('/api/agents', { name });
    newAgentModal.hide();

    const token = agent.token;
    document.getElementById('token-value').value = token;
    document.getElementById('docker-cmd').textContent =
      `docker run -d --restart unless-stopped \\\n  -e AGENT_TOKEN=${token} \\\n  -e SERVER_WS_URL=wss://SEU-SERVIDOR/ws/agent \\\n  --network host \\\n  chromecast-agent:latest`;

    tokenModal.show();
    loadAgents();
  } catch (e) { showToast('Erro: ' + e.message, 'error'); }
});

document.getElementById('btn-copy-token').addEventListener('click', () => {
  navigator.clipboard.writeText(document.getElementById('token-value').value);
  showToast('Token copiado!', 'success');
});

loadAgents();
