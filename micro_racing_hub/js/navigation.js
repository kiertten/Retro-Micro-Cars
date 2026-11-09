const toggle = document.querySelector('.hub-menu-toggle');
const nav = document.getElementById(toggle.getAttribute('aria-controls'));

function setMenu(open) {
  toggle.setAttribute('aria-expanded', String(open));
}

toggle.addEventListener('click', () => setMenu(toggle.getAttribute('aria-expanded') !== 'true'));
nav.addEventListener('click', (event) => {
  if (event.target.closest('a')) setMenu(false);
});
document.addEventListener('keydown', (event) => {
  if (event.key === 'Escape' && toggle.getAttribute('aria-expanded') === 'true') {
    setMenu(false);
    if (toggle.getClientRects().length) toggle.focus();
  }
});
