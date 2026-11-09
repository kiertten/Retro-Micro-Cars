import {
  CAR_LENGTH, CAR_WIDTH, RACE_STATE, TILE_SIZE, WINDOW_HEIGHT, WINDOW_WIDTH,
} from '../../retro_cars_js/js/constants.js';
import { SKID_LIFETIME } from './skid-marks.js';

export const VISIBLE_RADIUS = 270;

function checker(ctx, x, y) {
  const square = TILE_SIZE / 5;
  for (let row = 0; row < 5; row += 1) {
    for (let col = 0; col < 5; col += 1) {
      ctx.fillStyle = (row + col) % 2 ? '#273038' : '#e3e8e3';
      ctx.fillRect(x + col * square, y + row * square, square, square);
    }
  }
}

function drawCatalogTrack(ctx, track) {
  ctx.fillStyle = '#365b47';
  ctx.fillRect(0, 0, WINDOW_WIDTH, WINDOW_HEIGHT);
  ctx.beginPath();
  for (const [index, { x, y }] of track.corners.entries()) {
    if (index === 0) ctx.moveTo(x, y);
    else ctx.lineTo(x, y);
  }
  ctx.closePath();
  ctx.lineJoin = 'round';
  ctx.strokeStyle = '#e4e0d3';
  ctx.lineWidth = track.roadWidth + 4;
  ctx.stroke();
  ctx.strokeStyle = '#87929a';
  ctx.lineWidth = track.roadWidth;
  ctx.stroke();

  const gates = [...track.checkpoints, track.finish];
  for (const gate of gates) {
    const half = track.roadWidth / 2;
    const isFinish = gate === track.finish;
    ctx.setLineDash(isFinish ? [] : [5, 5]);
    ctx.strokeStyle = isFinish ? '#f5f1e6' : '#ffdf7e';
    ctx.lineWidth = isFinish ? 5 : 2;
    ctx.beginPath();
    ctx.moveTo(gate.x - gate.dy * half, gate.y + gate.dx * half);
    ctx.lineTo(gate.x + gate.dy * half, gate.y - gate.dx * half);
    ctx.stroke();
  }
  ctx.setLineDash([]);
}

function buildTrack(track) {
  const canvas = document.createElement('canvas');
  canvas.width = WINDOW_WIDTH;
  canvas.height = WINDOW_HEIGHT;
  const ctx = canvas.getContext('2d');
  if (track.finish) {
    drawCatalogTrack(ctx, track);
    return canvas;
  }

  track.tiles.forEach((row, rowIndex) => {
    [...row].forEach((tile, colIndex) => {
      const x = colIndex * TILE_SIZE;
      const y = rowIndex * TILE_SIZE;
      const dark = (rowIndex + colIndex) % 2 === 0;
      if (tile === '.') {
        ctx.fillStyle = dark ? '#365b47' : '#3a614d';
        ctx.fillRect(x, y, TILE_SIZE, TILE_SIZE);
        return;
      }

      ctx.fillStyle = '#87929a';
      ctx.fillRect(x, y, TILE_SIZE, TILE_SIZE);
      if (tile === 'F') checker(ctx, x, y);

      // Бордюры рисуются только со стороны травы.
      const edges = [
        [x - 1, y, x, y, false], [x + TILE_SIZE, y, x + TILE_SIZE - 4, y, false],
        [x, y - 1, x, y, true], [x, y + TILE_SIZE, x, y + TILE_SIZE - 4, true],
      ];
      for (const [testX, testY, edgeX, edgeY, horizontal] of edges) {
        if (!track.isGrass(testX, testY)) continue;
        for (let offset = 0; offset < TILE_SIZE; offset += 10) {
          ctx.fillStyle = offset % 20 === 0 ? '#e9e8df' : '#ae473f';
          ctx.fillRect(
            edgeX + (horizontal ? offset : 0),
            edgeY + (horizontal ? 0 : offset),
            horizontal ? 10 : 4,
            horizontal ? 4 : 10,
          );
        }
      }
    });
  });

  ctx.fillStyle = 'rgba(232, 242, 228, .68)';
  ctx.textAlign = 'center';
  ctx.font = '700 42px system-ui';
  ctx.fillText('RETRO CIRCUIT', WINDOW_WIDTH / 2, WINDOW_HEIGHT / 2 - 4);
  ctx.font = '600 15px monospace';
  ctx.fillText('01  /  TIME TRIAL', WINDOW_WIDTH / 2, WINDOW_HEIGHT / 2 + 28);
  return canvas;
}

function drawSkids(ctx, segments, frame) {
  ctx.lineWidth = 2.8;
  ctx.lineCap = 'round';
  for (const { start, end, born } of segments) {
    const alpha = 0.88 * (1 - (frame - born) / SKID_LIFETIME);
    ctx.strokeStyle = 'rgba(0, 0, 0, ' + alpha + ')';
    ctx.beginPath();
    ctx.moveTo(start.x, start.y);
    ctx.lineTo(end.x, end.y);
    ctx.stroke();
  }
}

function drawCar(ctx, car, frame) {
  ctx.save();
  ctx.translate(car.x, car.y);
  ctx.rotate(car.theta);

  ctx.fillStyle = '#171a1c';
  for (const wheelX of [-11, 5]) {
    for (const wheelY of [-CAR_WIDTH / 2, CAR_WIDTH / 2 - 4]) {
      ctx.fillRect(wheelX, wheelY, 6, 4);
    }
  }

  ctx.fillStyle = '#f5c75d';
  ctx.fillRect(-CAR_LENGTH / 2, -6, CAR_LENGTH, 12);
  ctx.fillStyle = '#533c23';
  ctx.fillRect(-5, -5, 10, 10);
  ctx.fillStyle = '#93b7c3';
  ctx.fillRect(3, -4, 5, 8);
  ctx.fillStyle = '#fff5c7';
  ctx.fillRect(12, -5, 3, 3);
  ctx.fillRect(12, 2, 3, 3);
  ctx.restore();

  if (car.drifting) {
    const lift = Math.sin(frame / 5) * 3;
    ctx.textAlign = 'center';
    ctx.font = '700 14px system-ui';
    ctx.lineWidth = 3;
    ctx.strokeStyle = '#181a1b';
    ctx.fillStyle = '#ffdf7e';
    ctx.strokeText('ЗАНОС', car.x, car.y - 22 + lift);
    ctx.fillText('ЗАНОС', car.x, car.y - 22 + lift);
  }
}

export function createRenderer(canvas, track) {
  const ctx = canvas.getContext('2d');
  if (!ctx) throw new Error('Контекст Canvas недоступен');
  const map = buildTrack(track);

  return ({ race, paused, limitedVisibility, skids }) => {
    const { car, frame, state } = race;
    ctx.fillStyle = '#101a16';
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    ctx.save();
    if (limitedVisibility) {
      ctx.beginPath();
      ctx.arc(car.x, car.y, VISIBLE_RADIUS, 0, 2 * Math.PI);
      ctx.clip();
    }
    ctx.drawImage(map, 0, 0);
    drawSkids(ctx, skids.segments, frame);
    drawCar(ctx, car, frame);
    ctx.restore();

    if (paused || state === RACE_STATE.FINISHED) {
      ctx.fillStyle = 'rgba(12, 16, 20, .74)';
      ctx.fillRect(0, 0, canvas.width, canvas.height);
      ctx.textAlign = 'center';
      ctx.font = '700 48px system-ui';
      ctx.fillStyle = '#fff1cf';
      ctx.fillText(paused ? 'Пауза' : 'Финиш', canvas.width / 2, canvas.height / 2);
    }
  };
}
