import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { Car } from './js/car.js';
import {
  CAR_LENGTH, DRIFT_ANGLE_THRESHOLD, DRIFT_MIN_SPEED, GRASS_GRIP_K, GRASS_MAX_SPEED,
  GRIP_K, MAX_REVERSE_SPEED, MAX_SPEED, RACE_STATE, START_POSITION, STEP_SECONDS, TOTAL_LAPS,
} from './js/constants.js';
import { isDrifting, normalizeAngle, slipAngle, velocityCorrection } from './js/physics.js';
import { Race } from './js/race.js';
import { Rect } from './js/rect.js';
import { Track } from './js/track.js';

const trackText = readFileSync(new URL('./track.json', import.meta.url), 'utf8');
const track = Track.fromJSON(trackText);
let passed = 0;
let failed = 0;

function check(name, test) {
  try {
    test();
    passed += 1;
    console.log('OK   ' + name);
  } catch (error) {
    failed += 1;
    console.error('FAIL ' + name + '\n     ' + error.message);
  }
}

function close(actual, expected) {
  assert.ok(Math.abs(actual - expected) < 1e-9, actual + ' ≠ ' + expected);
}

check('Rect: центр прямоугольника', () => {
  assert.deepEqual(new Rect(10, 20, 30, 40).center, [25, 40]);
});

check('Rect: сдвиг создаёт копию', () => {
  const rect = new Rect(10, 20, 30, 40);
  const moved = rect.move(5, -10);
  assert.deepEqual(moved.center, [30, 30]);
  assert.deepEqual(rect.center, [25, 40]);
});

check('Rect: левая граница включена, правая исключена', () => {
  const rect = new Rect(10, 20, 30, 40);
  assert.ok(rect.collidepoint(10, 20));
  assert.ok(!rect.collidepoint(40, 20));
  assert.ok(!rect.collidepoint(10, 60));
});

check('Rect: пересечение требует ненулевой площади', () => {
  const rect = new Rect(0, 0, 10, 10);
  assert.ok(rect.colliderect(new Rect(9, 9, 10, 10)));
  assert.ok(!rect.colliderect(new Rect(10, 0, 10, 10)));
});

check('Track: распознаёт асфальт, траву, финиш и внешнюю область', () => {
  assert.equal(track.tileAt(...START_POSITION), '#');
  assert.ok(track.isGrass(400, 300));
  assert.ok(track.onFinish(440, 100));
  assert.ok(!track.onFinish(480, 100));
  assert.ok(track.isGrass(-1, 100));
});

check('Track: сообщает об ошибке синтаксиса JSON', () => {
  assert.throws(() => Track.fromJSON('{'), /Ошибка JSON трассы/);
});

check('Track: требует поле tiles', () => {
  assert.throws(() => Track.fromJSON('{}'), /15 строк/);
});

check('Track: отклоняет неправильную длину строки', () => {
  const tiles = [...track.tiles];
  tiles[0] = '.';
  assert.throws(() => Track.fromJSON(JSON.stringify({ tiles })), /20 символов/);
});

check('Track: отклоняет неизвестный символ', () => {
  const tiles = [...track.tiles];
  tiles[0] = 'X' + tiles[0].slice(1);
  assert.throws(() => new Track(tiles), /набора/);
});

check('Track: требует финиш', () => {
  assert.throws(() => new Track(track.tiles.map((row) => row.replaceAll('F', '#'))), /финишная плитка/);
});

check('Track: требует стартовую позицию на дороге', () => {
  const tiles = [...track.tiles];
  tiles[2] = tiles[2].slice(0, 7) + '.' + tiles[2].slice(8);
  assert.throws(() => new Track(tiles), /Стартовая позиция/);
});

check('Угол: нормализация через границу ±π', () => {
  close(normalizeAngle(-Math.PI), Math.PI);
  close(normalizeAngle(2 * Math.PI + 0.25), 0.25);
  close(slipAngle(-1, 0, -Math.PI + 0.2), 0.2);
});

check('Car: первый кадр разгона и ускорение', () => {
  const car = new Car();
  car.update({ throttle: true }, track);
  close(car.speed, 0.12);
  close(car.vx, 0.012);
  close(car.x, 300.012);
  close(car.ax, 43.2);
  close(car.ay, 0);
});

check('Car: тормоз уменьшает положительную скорость', () => {
  const car = new Car();
  car.speed = 1;
  car.update({ brake: true }, track);
  close(car.speed, 0.75);
});

check('Car: накат останавливает без смены направления', () => {
  const car = new Car();
  car.speed = 0.02;
  car.update({}, track);
  close(car.speed, 0);
});

check('Car: предел скорости вперёд', () => {
  const car = new Car();
  car.speed = MAX_SPEED;
  car.update({ throttle: true }, track);
  close(car.speed, MAX_SPEED);
});

check('Car: предел заднего хода', () => {
  const car = new Car();
  car.speed = MAX_REVERSE_SPEED;
  car.update({ brake: true }, track);
  close(car.speed, MAX_REVERSE_SPEED);
  assert.ok(car.x < START_POSITION[0]);
});

check('Car: руль на месте не меняет угол', () => {
  const car = new Car();
  car.update({ steer: 1 }, track);
  close(car.omega, 0);
  close(car.theta, 0);
});

check('Car: угловая скорость интегрируется за кадр', () => {
  const car = new Car();
  car.speed = 4;
  car.update({ steer: 1 }, track);
  close(car.omega, 3.3);
  close(car.theta, 0.055);
});

check('Car: на заднем ходу направление поворота меняется', () => {
  const car = new Car();
  car.speed = -1;
  car.update({ brake: true, steer: 1 }, track);
  assert.ok(car.omega < 0 && car.theta < 0);
});

check('Физика: боковое сцепление затухает с множителем 1 − K', () => {
  const asphalt = velocityCorrection(0, 4, 0, 0, GRIP_K);
  const grass = velocityCorrection(0, 4, 0, 0, GRASS_GRIP_K);
  close(4 + asphalt.y, 3.6);
  close(4 + grass.y, 3.84);
  close(asphalt.x, 0);
});

check('Физика: проекции сохраняют векторную формулу Python', () => {
  const theta = Math.PI / 3;
  const delta = velocityCorrection(3, -2, theta, 4, GRIP_K);
  close(delta.x, GRIP_K * (4 * Math.cos(theta) - 3));
  close(delta.y, GRIP_K * (4 * Math.sin(theta) + 2));
});

check('Физика: порог заноса строгий по углу и включительный по скорости', () => {
  assert.ok(!isDrifting(DRIFT_MIN_SPEED - 0.01, 0, 0.5));
  assert.ok(!isDrifting(DRIFT_MIN_SPEED, 0, DRIFT_ANGLE_THRESHOLD));
  assert.ok(isDrifting(DRIFT_MIN_SPEED, 0, DRIFT_ANGLE_THRESHOLD + 0.01));
});

check('Car: занос тормозит машину, а поперечная скорость сохраняет знак', () => {
  const car = new Car();
  car.speed = 4;
  car.vy = 5;
  car.update({ throttle: true }, track);
  assert.ok(car.drifting);
  close(car.speed, 4.12 * 0.988);
  close(car.lateralSpeed, 4.5);
});

check('Car: трава проезжаема, предел скорости достигается постепенно', () => {
  const car = new Car(400, 300);
  car.speed = MAX_SPEED;
  car.update({ throttle: true }, track);
  assert.ok(car.onGrass && car.x > 400);
  assert.equal(car.gripK, GRASS_GRIP_K);
  assert.ok(car.speed < MAX_SPEED && car.speed > GRASS_MAX_SPEED);
  for (let frame = 0; frame < 30; frame += 1) car.update({ throttle: true }, track);
  close(car.speed, GRASS_MAX_SPEED);
});

check('Car: граница останавливает только движение наружу', () => {
  const car = new Car(784, 100);
  car.vx = 6;
  car.vy = 1;
  car.update({}, track);
  close(car.x, 800 - CAR_LENGTH / 2);
  close(car.vx, 0);
  assert.ok(car.y > 100 && car.vy > 0);
});

check('Car: углы кузова вращаются вместе с автомобилем', () => {
  const car = new Car(100, 100, Math.PI / 2);
  const [x, y] = car.corners()[0];
  close(x, 92);
  close(y, 115);
});

check('Race: до старта физический шаг не выполняется', () => {
  const race = new Race(track);
  race.update({ throttle: true });
  assert.equal(race.frame, 0);
  assert.equal(race.state, RACE_STATE.READY);
});

check('Race: первое пересечение финиша начинает отсчёт без зачёта круга', () => {
  const race = new Race(track);
  race.start();
  for (let frame = 0; frame < 100 && race.startFrame === null; frame += 1) {
    race.update({ throttle: true });
  }
  assert.ok(race.startFrame > 0);
  assert.equal(race.lapTimes.length, 0);
  assert.equal(race.events.at(-1).type, 'timing-start');
});

check('Race: повторный проезд финиша без нижней контрольной зоны не засчитывается', () => {
  const race = new Race(track);
  race.start();
  for (let frame = 0; frame < 100 && race.startFrame === null; frame += 1) {
    race.update({ throttle: true });
  }
  assert.ok(race.startFrame > 0);
  race.car.x = 437;
  race.car.vx = 5;
  race.wasOnFinish = false;
  race.update({ throttle: true });
  assert.ok(track.onFinish(race.car.x, race.car.y));
  assert.equal(race.lapTimes.length, 0);
});

check('Race: пересечение финиша задним ходом не запускает хронометраж', () => {
  const race = new Race(track);
  race.start();
  race.car.x = 481;
  race.car.speed = -2;
  race.car.vx = -2;
  race.update({ brake: true });
  assert.ok(track.onFinish(race.car.x, race.car.y));
  assert.equal(race.startFrame, null);
});

check('Race: три круга на обычных командах управления и полный цикл заезда', () => {
  const race = new Race(track);
  race.start();
  const waypoints = [[690, 100], [690, 500], [100, 500], [100, 100]];
  let waypoint = 0;

  for (let frame = 0; frame < 5000 && race.state !== RACE_STATE.FINISHED; frame += 1) {
    let [targetX, targetY] = waypoints[waypoint];
    if (Math.hypot(targetX - race.car.x, targetY - race.car.y) < 55) {
      waypoint = (waypoint + 1) % waypoints.length;
      [targetX, targetY] = waypoints[waypoint];
    }
    const heading = Math.atan2(targetY - race.car.y, targetX - race.car.x);
    const error = normalizeAngle(heading - race.car.theta);
    race.update({
      throttle: race.car.speed < 4,
      steer: Math.abs(error) < 0.035 ? 0 : Math.sign(error),
    });
  }

  assert.equal(race.state, RACE_STATE.FINISHED);
  assert.equal(race.lapTimes.length, TOTAL_LAPS);
  assert.ok(race.lapTimes.every((time) => time > 0));
  close(race.bestLap, Math.min(...race.lapTimes));
  assert.equal(race.events.filter(({ type }) => type === 'lap').length, TOTAL_LAPS);
  assert.equal(race.events.at(-1).type, 'race-finish');
  close(race.events.at(-1).seconds, (race.frame - race.startFrame) * STEP_SECONDS);
  close(race.lapTimes.reduce((sum, time) => sum + time, 0), race.events.at(-1).seconds);

  const finishFrame = race.frame;
  race.update({ throttle: true });
  assert.equal(race.frame, finishFrame);
  race.reset();
  assert.equal(race.state, RACE_STATE.READY);
  assert.equal(race.events.length, 0);
  assert.equal(race.lapTimes.length, 0);
});

console.log('\nСамопроверка: ' + passed + '/' + (passed + failed) + ' пройдено.');
if (failed) process.exitCode = 1;
