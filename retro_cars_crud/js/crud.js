import { MAX_CHECKPOINTS, MAX_LENGTH, STORAGE_KEY, loadTracks, saveTracks, validateTrack } from './tracks.js';

const createForm = document.getElementById('create-track');
const editForm = document.getElementById('edit-track');
const tbody = document.querySelector('#tracks tbody');
const search = document.getElementById('search');
const maxLength = document.getElementById('max-length');
const count = document.getElementById('count');
const notice = document.getElementById('notice');
const numberFormat = new Intl.NumberFormat('ru-RU', { maximumFractionDigits: 12 });

let tracks = [];
let activeEdit = null;

function escapeHtml(value) {
  const entities = { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' };
  return String(value).replace(/[&<>"']/g, (character) => entities[character]);
}

function announce(message, isError = false) {
  notice.textContent = message;
  notice.dataset.error = String(isError);
}

function setErrors(form, scope, errors) {
  for (const span of scope.querySelectorAll('[data-error]')) {
    const key = span.dataset.error;
    const message = errors[key] ?? '';
    span.textContent = message;
    form.elements.namedItem(key).setAttribute('aria-invalid', String(Boolean(message)));
  }

  const firstError = Object.keys(errors)[0];
  if (firstError) form.elements.namedItem(firstError).focus();
  return Boolean(firstError);
}

function formTrack(form) {
  return validateTrack(Object.fromEntries(new FormData(form)));
}

function readRow(track) {
  const row = document.createElement('tr');
  row.dataset.id = track.id;
  const playUrl = '../retro_cars_widget/index.html?' + new URLSearchParams({ track: track.id });
  row.innerHTML = `
    <td><strong>${escapeHtml(track.name)}</strong></td>
    <td>${numberFormat.format(track.length)}</td>
    <td>${numberFormat.format(track.checkpoints)}</td>
    <td><code>${escapeHtml(JSON.stringify(track.corners))}</code></td>
    <td><div class="actions">
      <a class="game-link play-track" href="${escapeHtml(playUrl)}">Играть</a>
      <button type="button" data-action="edit">Изменить</button>
      <button type="button" data-action="delete" class="danger">Удалить</button>
    </div></td>`;
  return row;
}

function editRow(track) {
  const row = document.createElement('tr');
  row.className = 'editing';
  row.dataset.id = track.id;
  row.innerHTML = `
    <td><div class="field">
      <input form="edit-track" name="name" required maxlength="80" value="${escapeHtml(track.name)}"
        aria-label="Название трассы" aria-describedby="edit-name-error">
      <span id="edit-name-error" class="error" data-error="name"></span>
    </div></td>
    <td><div class="field">
      <input form="edit-track" name="length" type="number" min="0.01" max="${MAX_LENGTH}" step="any"
        required value="${track.length}" aria-label="Длина трассы, м" aria-describedby="edit-length-error">
      <span id="edit-length-error" class="error" data-error="length"></span>
    </div></td>
    <td><div class="field">
      <input form="edit-track" name="checkpoints" type="number" min="0" max="${MAX_CHECKPOINTS}" step="1"
        required value="${track.checkpoints}" aria-label="Количество чекпоинтов" aria-describedby="edit-checkpoints-error">
      <span id="edit-checkpoints-error" class="error" data-error="checkpoints"></span>
    </div></td>
    <td><div class="field">
      <textarea form="edit-track" name="corners" rows="3" required maxlength="4000"
        aria-label="Координаты углов трассы" aria-describedby="edit-corners-error">${escapeHtml(JSON.stringify(track.corners))}</textarea>
      <span id="edit-corners-error" class="error" data-error="corners"></span>
    </div></td>
    <td><div class="actions">
      <button type="submit" form="edit-track" class="primary">Сохранить</button>
      <button type="button" data-action="cancel">Отмена</button>
    </div></td>`;
  return row;
}

function render() {
  const query = search.value.trim().toLocaleLowerCase('ru-RU');
  const limit = maxLength.value === '' ? Infinity : maxLength.valueAsNumber;
  const visible = tracks.filter((track) =>
    track.name.toLocaleLowerCase('ru-RU').includes(query) && track.length <= limit);
  const rows = visible.map((track) =>
    track.id === activeEdit?.original.id ? activeEdit.row : readRow(track));

  // Черновик остаётся доступным даже при фильтре, скрывающем исходную запись.
  if (activeEdit && !rows.includes(activeEdit.row)) rows.unshift(activeEdit.row);

  if (rows.length === 0) {
    const row = document.createElement('tr');
    const cell = row.insertCell();
    cell.colSpan = 5;
    cell.className = 'empty';
    cell.textContent = tracks.length ? 'Трассы по этим условиям не найдены.' : 'Каталог пуст. Добавьте первую трассу.';
    rows.push(row);
  }
  tbody.replaceChildren(...rows);
  count.textContent = 'Показано ' + visible.length + ' из ' + tracks.length;
}

function refresh() {
  try {
    tracks = loadTracks();
    render();
  } catch (error) {
    announce('Не удалось прочитать каталог. ' + error.message, true);
  }
}

function mutate(change, message) {
  try {
    const next = change(loadTracks());
    saveTracks(next);
    tracks = next;
  } catch (error) {
    announce('Изменение не сохранено. ' + error.message, true);
    return false;
  }
  announce(message);
  return true;
}

createForm.addEventListener('submit', (event) => {
  event.preventDefault();
  const { errors, track } = formTrack(createForm);
  if (setErrors(createForm, createForm, errors)) return;

  if (mutate((items) => [...items, { id: crypto.randomUUID(), ...track }], 'Трасса добавлена.')) {
    createForm.reset();
    render();
    createForm.elements.namedItem('name').focus();
  }
});

editForm.addEventListener('submit', (event) => {
  event.preventDefault();
  if (!activeEdit) return;
  const { row, original } = activeEdit;
  const { errors, track } = formTrack(editForm);
  if (setErrors(editForm, row, errors)) return;

  const saved = mutate((items) => {
    const current = items.find(({ id }) => id === original.id);
    if (JSON.stringify(current) !== JSON.stringify(original)) {
      throw new Error('Запись изменилась в другой вкладке. Отмените правку и откройте запись заново.');
    }
    return items.map((item) => item.id === original.id ? { id: item.id, ...track } : item);
  }, 'Трасса обновлена.');
  if (saved) {
    activeEdit = null;
    render();
  }
});

tbody.addEventListener('click', (event) => {
  const button = event.target.closest('button[data-action]');
  if (!button) return;
  const id = button.closest('tr').dataset.id;

  if (button.dataset.action === 'cancel') {
    activeEdit = null;
    refresh();
    return;
  }

  const track = tracks.find((item) => item.id === id);
  if (!track) return;
  if (button.dataset.action === 'edit') {
    if (activeEdit) {
      announce('Сохраните или отмените текущую правку.', true);
      return;
    }
    activeEdit = { original: track, row: editRow(track) };
    render();
    editForm.elements.namedItem('name').focus();
  } else if (button.dataset.action === 'delete' && window.confirm('Удалить трассу «' + track.name + '»?')) {
    if (mutate((items) => items.filter((item) => item.id !== id), 'Трасса удалена.')) render();
  }
});

search.addEventListener('input', render);
maxLength.addEventListener('input', render);
window.addEventListener('storage', (event) => {
  if (event.storageArea === localStorage && (event.key === STORAGE_KEY || event.key === null)) refresh();
});
render();
refresh();
