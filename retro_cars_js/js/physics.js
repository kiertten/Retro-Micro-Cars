import {
  ACCELERATION, BRAKE_POWER, DRIFT_ANGLE_THRESHOLD, DRIFT_MIN_SPEED,
  MAX_REVERSE_SPEED, MAX_SPEED, MIN_STEER_SPEED, OVERSPEED_DECEL,
  ROLLING_FRICTION, STEP_SECONDS, TURN_RATE,
} from './constants.js';

export function clamp(value, low, high) {
  return Math.max(low, Math.min(high, value));
}

export function normalizeAngle(angle) {
  const fullTurn = 2 * Math.PI;
  const wrapped = angle % fullTurn;
  if (wrapped > Math.PI) return wrapped - fullTurn;
  if (wrapped <= -Math.PI) return wrapped + fullTurn;
  return wrapped;
}

export function updateSpeed(speed, throttle, brake, maxSpeed) {
  if (throttle && !brake) {
    speed += ACCELERATION;
  } else if (brake && !throttle) {
    speed -= speed > 0 ? BRAKE_POWER : ACCELERATION;
  } else {
    speed = Math.sign(speed) * Math.max(0, Math.abs(speed) - ROLLING_FRICTION);
  }

  // После въезда на траву превышение гасится постепенно.
  if (speed > maxSpeed) {
    speed = Math.max(maxSpeed, speed - OVERSPEED_DECEL);
  }
  return clamp(speed, MAX_REVERSE_SPEED, MAX_SPEED);
}

export function angularVelocity(speed, steer) {
  return steer * TURN_RATE * clamp(speed / MIN_STEER_SPEED, -1, 1) / STEP_SECONDS;
}

export function velocityCorrection(vx, vy, theta, speed, grip) {
  const forwardX = Math.cos(theta);
  const forwardY = Math.sin(theta);
  const longitudinal = vx * forwardX + vy * forwardY;
  const lateral = -vx * forwardY + vy * forwardX;

  // Разгон вдоль кузова и сила сцепления поперёк кузова.
  // Для единичной массы компоненты силы пропорциональны этим приращениям.
  const forwardDelta = grip * (speed - longitudinal);
  const lateralDelta = -grip * lateral;
  return {
    x: forwardDelta * forwardX - lateralDelta * forwardY,
    y: forwardDelta * forwardY + lateralDelta * forwardX,
  };
}

export function slipAngle(vx, vy, theta) {
  if (Math.hypot(vx, vy) < 0.1) return 0;
  return Math.abs(normalizeAngle(Math.atan2(vy, vx) - theta));
}

export function isDrifting(vx, vy, theta) {
  return Math.hypot(vx, vy) >= DRIFT_MIN_SPEED
    && slipAngle(vx, vy, theta) > DRIFT_ANGLE_THRESHOLD;
}
