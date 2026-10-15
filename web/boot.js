/* The worker controls the very first runtime request, so a successful first run
   can cache both the game and its versioned WebAssembly dependencies. */
const info = document.getElementById('infobox');
const dialog = document.getElementById('install-dialog');
// Dialog keys must not trigger the game underneath it.
dialog.addEventListener('keydown', event => event.stopPropagation());
dialog.addEventListener('keyup', event => event.stopPropagation());
let installPrompt;
document.getElementById('install-help').onclick = () => dialog.showModal();
document.getElementById('close-install').onclick = () => dialog.close();
window.addEventListener('beforeinstallprompt', event => {
  event.preventDefault(); installPrompt = event;
  document.getElementById('install-now').hidden = false;
});
document.getElementById('install-now').onclick = async () => {
  if (!installPrompt) return;
  await installPrompt.prompt(); await installPrompt.userChoice;
  installPrompt = null; document.getElementById('install-now').hidden = true;
};
window.addEventListener('appinstalled', () => dialog.close());
navigator.serviceWorker?.addEventListener('message', ({data}) => {
  if (data.type === 'OFFLINE_READY') document.getElementById('offline-state').textContent =
    'Игра загружена и сохранена для запуска без интернета. Браузер может удалить эти данные при очистке хранилища.';
  if (data.type === 'CACHE_INCOMPLETE') document.getElementById('offline-state').textContent =
    'Игра запущена. Для следующего запуска пока сохрани подключение к интернету.';
});
function loadScript(url) {
  return new Promise((resolve, reject) => {
    const script = document.createElement('script'); script.src = url;
    script.onload = resolve; script.onerror = () => reject(new Error('Не удалось загрузить игру. Проверь интернет и обнови страницу.'));
    document.head.append(script);
  });
}
(async () => {
  try {
    if ('serviceWorker' in navigator && window.isSecureContext) {
      try {
        const registration = await navigator.serviceWorker.register('./sw.js');
        try { await registration.update(); } catch (_) { /* cached offline run */ }
        const updating = registration.installing || registration.waiting;
        if (updating && updating.state !== 'activated') await new Promise(resolve => {
          updating.addEventListener('statechange', () => {if (['activated','redundant'].includes(updating.state)) resolve();});
        });
        await navigator.serviceWorker.ready;
        if (!navigator.serviceWorker.controller) await new Promise(resolve => {
          navigator.serviceWorker.addEventListener('controllerchange', resolve, {once:true});
        });
      } catch (error) { console.warn('Offline cache unavailable', error); }
    }
    await loadScript('./vendor/browserfs.min.js');
    const script = document.createElement('script');
    script.onload = () => { if (document.readyState === 'complete') window.dispatchEvent(new Event('load')); };
    script.id = 'site'; script.type = 'module'; script.dataset.python = 'python3.12';
    script.dataset.os = 'gui'; script.dataset.lines = '42'; script.dataset.columns = '132';
    script.textContent = document.getElementById('python-source').textContent;
    script.src = 'https://pygame-web.github.io/cdn/0.9.3/pythons.js';
    script.onerror = () => {info.innerText='Не удалось загрузить игру. Проверь интернет и обнови страницу.';};
    document.head.append(script);
  } catch (error) { info.innerText = error.message; }
})();
