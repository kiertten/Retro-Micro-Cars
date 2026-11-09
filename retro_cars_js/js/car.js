import {
  CAR_LENGTH, CAR_WIDTH, DRIFT_SPEED_LOSS, GRASS_GRIP_K, GRASS_MAX_SPEED,
  GRIP_K, MAX_SPEED, START_ANGLE, START_POSITION, STEP_SECONDS,
} from './constants.js';
import {
  angularVelocity, clamp, isDrifting, normalizeAngle, slipAngle, updateSpeed, velocityCorrection,
} from './physics.js';

export class Car {
  constructor(x = START_POSITION[0], y = START_POSITION[1], theta = START_ANGLE) {
    this.x = x;
    this.y = y;
    this.theta = normalizeAngle(theta);
    this.speed = 0;
    this.vx = 0;
    this.vy = 0;
    this.omega = 0;
    this.ax = 0;
    this.ay = 0;
    this.onGrass = false;
    this.drifting = false;
    this.gripK = GRIP_K;
  }

  get velocity() {
    return Math.hypot(this.vx, this.vy);
  }

  get lateralSpeed() {
    return -this.vx * Math.sin(this.theta) + this.vy * Math.cos(this.theta);
  }

  get slipAngle() {
    return slipAngle(this.vx, this.vy, this.theta);
  }

  corners() {
    const halfLength = CAR_LENGTH / 2;
    const halfWidth = CAR_WIDTH / 2;
    const cos = Math.cos(this.theta);
    const sin = Math.sin(this.theta);
    return [
      [halfLength, halfWidth], [halfLength, -halfWidth],
      [-halfLength, halfWidth], [-halfLength, -halfWidth],
    ].map(([x, y]) => [this.x + x * cos - y * sin, this.y + x * sin + y * cos]);
  }

  // Один вызов соответствует одному кадру физики при 60 Гц.
  update({ throttle = false, brake = false, steer = 0 } = {}, track) {
    this.onGrass = track.isGrass(this.x, this.y);
    this.gripK = this.onGrass ? GRASS_GRIP_K : GRIP_K;
    const maxSpeed = this.onGrass ? GRASS_MAX_SPEED : MAX_SPEED;

    this.speed = updateSpeed(this.speed, throttle, brake, maxSpeed);
    this.omega = angularVelocity(this.speed, clamp(steer, -1, 1));
    this.theta = normalizeAngle(this.theta + this.omega * STEP_SECONDS);

    const correction = velocityCorrection(this.vx, this.vy, this.theta, this.speed, this.gripK);
    // Скорость хранится в px/кадр, ускорение от сцепления — в px/с².
    this.ax = correction.x / STEP_SECONDS ** 2;
    this.ay = correction.y / STEP_SECONDS ** 2;
    this.vx += correction.x;
    this.vy += correction.y;
    this.drifting = isDrifting(this.vx, this.vy, this.theta);
    if (this.drifting && this.speed > 0) this.speed *= 1 - DRIFT_SPEED_LOSS;

    this.move(track.bounds);
  }

  move(bounds) {
    const margin = Math.max(CAR_LENGTH, CAR_WIDTH) / 2;
    const nextX = this.x + this.vx;
    const nextY = this.y + this.vy;
    this.x = clamp(nextX, bounds.x + margin, bounds.x + bounds.width - margin);
    this.y = clamp(nextY, bounds.y + margin, bounds.y + bounds.height - margin);
    if (this.x !== nextX) this.vx = 0;
    if (this.y !== nextY) this.vy = 0;
  }
}
