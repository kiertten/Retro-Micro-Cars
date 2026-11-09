import { FPS, MAX_SPEED, RACE_STATE, STEP_SECONDS, TOTAL_LAPS } from '../../retro_cars_js/js/constants.js';

const MAX_DISPLAY_SPEED = MAX_SPEED * FPS;
const time = new Intl.NumberFormat('ru-RU', { minimumFractionDigits: 2, maximumFractionDigits: 2 });

function write(node, text) {
  if (node.textContent !== text) node.textContent = text;
}

export function createHud(panel) {
  const byId = (id) => panel.querySelector('#' + id);
  const needle = byId('speed-needle');
  const speedValue = byId('speed-value');
  const drift = byId('drift');
  const slip = byId('slip');
  const lap = byId('lap');
  const timer = byId('time');
  const best = byId('best');
  const status = byId('race-status');
  const hint = byId('race-hint');
  const start = byId('start');
  const pause = byId('pause');
  let displayedSpeed = -1;

  return ({ race, paused }) => {
    const { car, state, frame, startFrame, lapTimes, bestLap, track } = race;
    const running = state === RACE_STATE.RUNNING;
    const finished = state === RACE_STATE.FINISHED;
    const speed = Math.round(car.velocity * FPS);
    if (speed !== displayedSpeed) {
      const angle = -135 + 270 * Math.min(speed / MAX_DISPLAY_SPEED, 1);
      needle.style.transform = 'rotate(' + angle + 'deg)';
      write(speedValue, String(speed));
      displayedSpeed = speed;
    }

    drift.classList.toggle('active', car.drifting);
    write(drift, car.drifting ? 'Занос' : 'Сцепление');
    write(slip, Math.round(car.slipAngle * 180 / Math.PI) + '°');
    write(lap, Math.min(lapTimes.length + 1, TOTAL_LAPS) + ' / ' + TOTAL_LAPS);
    write(timer, time.format(startFrame === null ? 0 : (frame - startFrame) * STEP_SECONDS));
    write(best, bestLap === null ? '—' : time.format(bestLap));
    write(status, paused ? 'Пауза' : finished ? 'Финиш' : running ? 'В гонке' : 'Готов к старту');

    let instruction = 'Начните заезд и пересеките линию старта.';
    if (finished) {
      instruction = 'Все три круга зачтены.';
    } else if (running && startFrame === null) {
      instruction = track.finish ? 'Пересеките белую линию по ходу движения.'
        : 'Пересеките клетчатую линию вправо.';
    } else if (running) {
      instruction = track.finish ? 'Чекпоинты ' + race.nextCheckpoint + ' / ' + track.checkpoints.length
        : 'Пройдите нижнюю часть трассы и пересеките финиш вправо.';
    }
    write(hint, instruction);
    start.disabled = running;
    pause.disabled = !running;
    write(start, finished ? 'Новый заезд' : 'Старт');
    write(pause, paused ? 'Продолжить' : 'Пауза');
  };
}
