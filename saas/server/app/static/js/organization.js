const inviteModal = new bootstrap.Modal(document.getElementById('inviteModal'));

const roleBadge = (role) => {
  const map = { owner: 'bg-danger', admin: 'bg-warning text-dark', member: 'bg-secondary' };
  return `<span class="badge ${map[role] || 'bg-secondary'}">${role}</span>`;
};

async function loadOrg() {
  try {
    const org = await apiGet('/api/org');
    document.getElementById('org-name').textContent = org.name;
  } catch (e) { /* ignore */ }
}

async function loadUsers() {
  const list = document.getElementById('users-list');
  try {
    const users = await apiGet('/api/org/users');
    if (!users.length) {
      list.innerHTML = `<div class="col-12 text-center text-muted py-4">Nenhum usuário.</div>`;
      return;
    }
    list.innerHTML = users.map(u => `
      <div class="col-md-4">
        <div class="card bg-secondary bg-opacity-10 border-secondary h-100">
          <div class="card-body">
            <div class="d-flex justify-content-between align-items-start">
              <div>
                <h6 class="mb-1">${u.name || u.email}</h6>
                <p class="text-secondary small mb-1">${u.email}</p>
                ${roleBadge(u.role)}
              </div>
              ${(window.IS_ADMIN && u.id !== window.CURRENT_USER_ID) ? `
              <div class="d-flex flex-column gap-1 align-items-end">
                <select class="form-select form-select-sm btn-change-role" data-id="${u.id}" style="width:auto">
                  <option value="member" ${u.role === 'member' ? 'selected' : ''}>Member</option>
                  <option value="admin" ${u.role === 'admin' ? 'selected' : ''}>Admin</option>
                  <option value="owner" ${u.role === 'owner' ? 'selected' : ''}>Owner</option>
                </select>
                <button class="btn btn-sm btn-outline-danger btn-remove-user" data-id="${u.id}">
                  <i class="bi bi-trash"></i>
                </button>
              </div>` : ''}
            </div>
          </div>
        </div>
      </div>`).join('');

    document.querySelectorAll('.btn-change-role').forEach(sel => sel.addEventListener('change', async () => {
      try {
        await apiPatch(`/api/org/users/${sel.dataset.id}`, { role: sel.value });
        showToast('Papel atualizado', 'success');
      } catch (e) { showToast('Erro: ' + e.message, 'error'); loadUsers(); }
    }));
    document.querySelectorAll('.btn-remove-user').forEach(btn => btn.addEventListener('click', async () => {
      if (!confirm('Remover este usuário da organização?')) return;
      try {
        await apiDelete(`/api/org/users/${btn.dataset.id}`);
        showToast('Usuário removido', 'success');
        loadUsers();
      } catch (e) { showToast('Erro: ' + e.message, 'error'); }
    }));
  } catch (e) {
    list.innerHTML = `<div class="col-12 text-center text-muted py-4">Erro ao carregar usuários.</div>`;
  }
}

async function loadInvites() {
  const section = document.getElementById('invites-section');
  const list = document.getElementById('invites-list');
  try {
    const invites = await apiGet('/api/org/invites');
    if (!invites.length) { section.classList.add('d-none'); return; }
    section.classList.remove('d-none');
    list.innerHTML = invites.map(i => `
      <div class="col-md-4">
        <div class="card bg-secondary bg-opacity-10 border-secondary h-100">
          <div class="card-body">
            <h6 class="mb-1">${i.email}</h6>
            ${roleBadge(i.role)}
            <p class="text-secondary small mt-2 mb-0">Expira em ${new Date(i.expires_at).toLocaleDateString('pt-BR')}</p>
            ${window.IS_ADMIN ? `<button class="btn btn-sm btn-outline-danger mt-2 btn-revoke-invite" data-id="${i.id}">
              <i class="bi bi-x-circle me-1"></i>Revogar</button>` : ''}
          </div>
        </div>
      </div>`).join('');
    document.querySelectorAll('.btn-revoke-invite').forEach(btn => btn.addEventListener('click', async () => {
      if (!confirm('Revogar este convite?')) return;
      try {
        await apiDelete(`/api/org/invites/${btn.dataset.id}`);
        showToast('Convite revogado', 'success');
        loadInvites();
      } catch (e) { showToast('Erro: ' + e.message, 'error'); }
    }));
  } catch (e) { section.classList.add('d-none'); }
}

async function loadAudit() {
  const body = document.getElementById('audit-body');
  if (!body) return; // não é admin, seção não existe
  try {
    const rows = await apiGet('/api/org/audit?limit=100');
    if (!rows.length) {
      body.innerHTML = `<tr><td colspan="5" class="text-center text-muted py-3">Nenhum registro ainda.</td></tr>`;
      return;
    }
    body.innerHTML = rows.map(r => `
      <tr>
        <td>${new Date(r.created_at).toLocaleString('pt-BR')}</td>
        <td>${r.email_attempted}</td>
        <td>${r.success ? '<span class="badge bg-success">sucesso</span>' : '<span class="badge bg-danger">erro</span>'}</td>
        <td class="text-muted small">${r.reason || ''}</td>
        <td class="text-muted small">${r.ip_address || ''}</td>
      </tr>`).join('');
  } catch (e) {
    body.innerHTML = `<tr><td colspan="5" class="text-center text-muted py-3">Erro ao carregar auditoria.</td></tr>`;
  }
}

const renameBtn = document.getElementById('btn-rename-org');
if (renameBtn) {
  renameBtn.addEventListener('click', async () => {
    const current = document.getElementById('org-name').textContent;
    const name = prompt('Novo nome da organização:', current);
    if (!name || name.trim() === '' || name === current) return;
    try {
      await apiPatch('/api/org', { name: name.trim() });
      showToast('Organização renomeada', 'success');
      loadOrg();
    } catch (e) { showToast('Erro: ' + e.message, 'error'); }
  });
}

document.getElementById('btn-send-invite').addEventListener('click', async () => {
  const email = document.getElementById('invite-email').value.trim();
  const role = document.getElementById('invite-role').value;
  if (!email) { showToast('Informe um e-mail', 'warning'); return; }
  try {
    await apiPost('/api/org/invites', { email, role });
    inviteModal.hide();
    document.getElementById('invite-email').value = '';
    showToast('Convite enviado!', 'success');
    loadInvites();
  } catch (e) { showToast('Erro: ' + e.message, 'error'); }
});

loadOrg();
loadUsers();
loadInvites();
loadAudit();
