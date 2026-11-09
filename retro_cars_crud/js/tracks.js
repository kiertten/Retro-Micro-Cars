import { WINDOW_WIDTH, WINDOW_HEIGHT } from '../../retro_cars_js/js/constants.js';

export const STORAGE_KEY = 'retro_micro_cars_tracks';
export const MAX_LENGTH = 100000;
export const MAX_CHECKPOINTS = 100;

function boundedNumber(value, min, max) {
  if (typeof value !== 'number' && (typeof value !== 'string' || !value.trim())) return NaN;
  const number = Number(value);
  return Number.isFinite(number) && number >= min && number <= max ? number : NaN;
}

export function validateTrack(fields) {
  const errors = {};
  const name = typeof fields.name === 'string' ? fields.name.trim() : '';
  if (!name || name.length > 80) errors.name = 'Введите от 1 до 80 символов.';

  const length = boundedNumber(fields.length, 0.01, MAX_LENGTH);
  if (Number.isNaN(length)) errors.length = 'Укажите длину от 0,01 до 100 000 м.';

  const checkpoints = boundedNumber(fields.checkpoints, 0, MAX_CHECKPOINTS);
  if (!Number.isInteger(checkpoints)) errors.checkpoints = 'Введите целое число от 0 до 100.';

  let corners = fields.corners;
  if (typeof corners === 'string') {
    try {
      corners = JSON.parse(corners);
    } catch {
      errors.corners = 'Введите координаты в формате JSON.';
    }
  }

  if (!errors.corners) {
    const validPoint = (point) => Array.isArray(point) && point.length === 2
      && Number.isFinite(point[0]) && point[0] >= 0 && point[0] <= WINDOW_WIDTH
      && Number.isFinite(point[1]) && point[1] >= 0 && point[1] <= WINDOW_HEIGHT;
    if (!Array.isArray(corners) || corners.length < 3 || corners.length > 100
      || !corners.every(validPoint) || new Set(corners.map((point) => point.join(','))).size < 3) {
      errors.corners = 'Нужны 3–100 пар [x, y] в пределах 800 × 600 и хотя бы три разные точки.';
    }
  }

  return { errors, track: { name, length, checkpoints, corners } };
}

export function loadTracks() {
  const raw = localStorage.getItem(STORAGE_KEY);
  if (raw === null) return [];

  let tracks;
  try {
    tracks = JSON.parse(raw);
  } catch {
    throw new Error('Каталог в localStorage содержит некорректный JSON.');
  }

  const ids = new Set();
  if (!Array.isArray(tracks) || tracks.some((track) => {
    if (!track || typeof track.id !== 'string' || !track.id || ids.has(track.id)
      || typeof track.length !== 'number' || typeof track.checkpoints !== 'number'
      || !Array.isArray(track.corners) || Object.keys(validateTrack(track).errors).length) {
      return true;
    }
    ids.add(track.id);
    return false;
  })) {
    throw new Error('Записи каталога в localStorage имеют неверный формат.');
  }
  return tracks;
}

export function saveTracks(tracks) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(tracks));
}
