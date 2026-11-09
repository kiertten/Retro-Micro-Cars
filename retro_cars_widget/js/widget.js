import { FPS, RACE_STATE, STEP_SECONDS, TOTAL_LAPS } from '../../retro_cars_js/js/constants.js';
import { loadTracks } from '../../retro_cars_crud/js/tracks.js';
import { CatalogTrack } from './catalog-track.js';
import { loadDefaultTrack, mountRace } from './race-widget.js';

const byId = (id) => document.getElementById(id);

function writeText(node, value) {
  if (node.textContent !== value) node.textContent = value;
}

function createHud() {
  const nodes = Object.fromEntries(
    ['race-status', 'race-hint', 'lap', 'speed', 'time', 'best', 'slip', 'surface'].map((id) => [id, byId(id)]),
  );
  const number = new Intl.NumberFormat('ru-RU', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
  const startButton = document.querySelector('[data-scenario="start"]');
  const pauseButton = document.querySelector('[data-scenario="pause"]');
  const viewButton = document.querySelector('[data-scenario="toggleVisibility"]');

  return ({ race, paused, limitedVisibility }) => {
    const { car, state, frame, startFrame, lapTimes, bestLap } = race;
    const running = state === RACE_STATE.RUNNING;
    const finished = state === RACE_STATE.FINISHED;
    const timed = startFrame !== null;
    const elapsed = timed ? (frame - startFrame) * STEP_SECONDS : 0;
    const title = paused ? 'Пауза' : finished ? 'Заезд завершён'
      : running ? timed ? 'Заезд идёт' : 'Разгон к старту' : 'Готов к старту';
    let hint;
    if (finished) {
      hint = 'Три круга зачтены. Итоговое время указано ниже.';
    } else if (race.track.finish) {
      hint = timed
        ? 'Чекпоинты за круг ' + race.nextCheckpoint + ' / ' + race.track.checkpoints.length
        : 'Пересеките белую линию по ходу движения, чтобы запустить отсчёт.';
    } else {
      hint = running && !timed
        ? 'Пересеките клетчатую линию вправо, чтобы запустить отсчёт.'
        : 'Пройдите нижнюю часть трассы и пересеките финиш вправо.';
    }

    writeText(nodes['race-status'], title);
    writeText(nodes['race-hint'], hint);
    writeText(nodes.lap, Math.min(lapTimes.length + 1, TOTAL_LAPS) + ' / ' + TOTAL_LAPS);
    writeText(nodes.speed, String(Math.round(car.velocity * FPS)));
    writeText(nodes.time, number.format(elapsed));
    writeText(nodes.best, bestLap === null ? '—' : number.format(bestLap));
    writeText(nodes.slip, Math.round(car.slipAngle * 180 / Math.PI) + '°');
    writeText(nodes.surface, car.onGrass ? 'Трава' : 'Асфальт');

    startButton.disabled = running;
    pauseButton.disabled = !running;
    writeText(startButton, finished ? 'Новый заезд' : 'Начать заезд');
    writeText(pauseButton, paused ? 'Продолжить' : 'Пауза');
    viewButton.setAttribute('aria-pressed', String(limitedVisibility));
    writeText(viewButton, limitedVisibility ? 'Вернуть полный обзор' : 'Ограничить обзор');
  };
}

async function loadTrack() {
  const id = new URLSearchParams(window.location.search).get('track');
  if (id !== null) {
    const record = loadTracks().find((track) => track.id === id);
    if (!record) throw new Error('Трасса не найдена. Выберите её в каталоге');
    writeText(byId('track-name'), record.name);
    writeText(byId('track-details'), record.length + ' м · чекпоинтов ' + record.checkpoints);
    return new CatalogTrack(record);
  }
  return loadDefaultTrack();
}

async function boot() {
  const track = await loadTrack();
  const { widget, scenarios } = mountRace(byId('track'), {
    track,
    updateHud: createHud(),
    controls: document.querySelectorAll('[data-scenario]'),
  });
  window.RetroMicroCars = Object.freeze({ widget, scenarios });
}

boot().catch((error) => {
  writeText(byId('race-status'), 'Ошибка загрузки');
  writeText(byId('race-hint'), error.message + '.');
  console.error(error);
});
