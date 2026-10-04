(() => {
  const shell = document.querySelector('.account-shell');
  const csrf = shell.dataset.csrf;
  const message = document.getElementById('profileMessage');
  const panel = document.getElementById('editPanel');
  const deleteDialog = document.getElementById('deleteAccountDialog');

  document.getElementById('editToggle').addEventListener('click', () => panel.classList.toggle('hidden'));

  async function send(url, form) {
    const body = Object.fromEntries(new FormData(form));
    const response = await fetch(url, {
      method: 'POST',
      headers: {'Content-Type': 'application/json', 'X-CSRF-Token': csrf},
      body: JSON.stringify(body),
    });
    const data = await response.json();
    message.textContent = data.error || 'Değişiklik kaydedildi.';
    message.className = `notice${data.error ? ' error' : ''}`;
    if (data.success && url === '/api/profile') setTimeout(() => window.MobileBridge ? window.MobileBridge.reload() : location.reload(), 500);
    return data;
  }

  document.getElementById('profileForm').addEventListener('submit', event => {
    event.preventDefault();
    send('/api/profile', event.target);
  });
  document.getElementById('passwordForm').addEventListener('submit', event => {
    event.preventDefault();
    send('/api/profile/password', event.target);
  });
  document.getElementById('privacyOptionsButton').addEventListener('click', async () => {
    const opened = await window.FootballAdProvider?.privacyOptions?.();
    message.textContent = opened
      ? 'Reklam gizlilik tercihleri açıldı.'
      : 'Reklam tercihleri yalnızca iOS uygulamasında kullanılabilir.';
    message.className = `notice${opened ? '' : ' error'}`;
  });
  document.getElementById('deleteAccountOpen').addEventListener('click', () => deleteDialog.showModal());
  document.getElementById('deleteAccountCancel').addEventListener('click', () => deleteDialog.close());
  document.getElementById('deleteAccountForm').addEventListener('submit', async event => {
    event.preventDefault();
    if (!window.confirm('Hesabın kalıcı olarak silinecek. Son kez onaylıyor musun?')) return;
    const data = await send('/api/profile/delete', event.target);
    if (data.success && window.MobileBridge) window.MobileBridge.navigate(data.redirect || '/login');
    else if (data.success) window.location.replace(data.redirect || '/login');
  });
})();
