import { STORAGE_KEY, loadTracks } from '../../retro_cars_crud/js/tracks.js';

const number = new Intl.NumberFormat('ru-RU', { maximumFractionDigits: 2 });
const svgNamespace = 'http://www.w3.org/2000/svg';
const standardCorners = [[120, 100], [680, 100], [680, 500], [120, 500]];

function createCard({ name, description, corners }) {
  const button = document.createElement('button');
  button.type = 'button';
  button.className = 'track-card';
  const preview = document.createElementNS(svgNamespace, 'svg');
  preview.setAttribute('viewBox', '-50 -50 900 700');
  preview.setAttribute('aria-hidden', 'true');
  const outline = document.createElementNS(svgNamespace, 'polygon');
  outline.setAttribute('points', corners.map(([x, y]) => x + ',' + y).join(' '));
  preview.append(outline);

  const label = document.createElement('span');
  const title = document.createElement('strong');
  title.textContent = name;
  title.title = name;
  const details = document.createElement('small');
  details.textContent = description;
  label.append(title, details);
  button.append(preview, label);
  return button;
}

export function mountHotbar(container, notice, selectTrack) {
  let selectedId = null;
  let tracks = [];
  let snapshot;
  let cards = new Map();

  function markSelected(id) {
    selectedId = id;
    for (const [cardId, card] of cards) {
      card.setAttribute('aria-pressed', String(cardId === selectedId));
    }
  }

  function select(id) {
    const record = tracks.find((track) => track.id === id);
    if (id !== null && !record) {
      notice.textContent = 'Трасса не найдена в каталоге.';
      return false;
    }
    try {
      selectTrack(record);
    } catch (error) {
      notice.textContent = error.message;
      return false;
    }
    markSelected(id);
    notice.textContent = '';
    return true;
  }

  function refresh() {
    let storageError = '';
    try {
      tracks = loadTracks();
    } catch (error) {
      tracks = [];
      storageError = error.message;
    }
    const current = JSON.stringify([tracks, storageError]);
    if (snapshot === current) return;
    snapshot = current;

    const focusId = [...cards].find(([, card]) => card === document.activeElement)?.[0];
    cards = new Map();
    function add(id, info) {
      const card = createCard(info);
      card.addEventListener('click', () => select(id));
      cards.set(id, card);
    }
    add(null, { name: 'Стандартная трасса', description: 'Кольцо · 3 круга', corners: standardCorners });
    for (const track of tracks) {
      add(track.id, {
        name: track.name,
        description: number.format(track.length) + ' м · КП ' + track.checkpoints,
        corners: track.corners,
      });
    }
    container.replaceChildren(...cards.values());
    markSelected(selectedId);
    (cards.get(focusId) ?? (focusId !== undefined ? cards.get(null) : null))?.focus({ preventScroll: true });
    notice.textContent = storageError || (selectedId !== null && !cards.has(selectedId)
      ? 'Текущая трасса удалена из каталога. Вы можете закончить заезд.' : '');
  }

  refresh();
  window.addEventListener('storage', (event) => {
    if (event.key === STORAGE_KEY || event.key === null) refresh();
  });
  window.addEventListener('pageshow', refresh);
  window.addEventListener('focus', refresh);

  return {
    select(id) {
      if (select(id)) cards.get(id).scrollIntoView({ block: 'nearest', inline: 'nearest' });
    },
  };
}
