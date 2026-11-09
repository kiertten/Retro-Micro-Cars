// Параметры из Python-версии. Скорость и её приращение заданы на кадр.
export const FPS = 60;
export const STEP_SECONDS = 1 / FPS;
export const WINDOW_WIDTH = 800;
export const WINDOW_HEIGHT = 600;
export const TILE_SIZE = 40;
export const CAR_LENGTH = 30;
export const CAR_WIDTH = 16;
export const START_POSITION = Object.freeze([300, 100]);
export const START_ANGLE = 0;

export const MAX_SPEED = 7;
export const MAX_REVERSE_SPEED = -2.5;
export const ACCELERATION = 0.12;
export const BRAKE_POWER = 0.25;
export const ROLLING_FRICTION = 0.04;
export const TURN_RATE = 0.055;
export const MIN_STEER_SPEED = 2;
export const GRIP_K = 0.1;
export const GRASS_GRIP_K = 0.04;
export const GRASS_MAX_SPEED = 3;
export const OVERSPEED_DECEL = 0.3;
export const DRIFT_ANGLE_THRESHOLD = 0.3;
export const DRIFT_MIN_SPEED = 2;
export const DRIFT_SPEED_LOSS = 0.012;

export const TOTAL_LAPS = 3;
export const CHECKPOINT_Y = 440;
export const RACE_STATE = Object.freeze({
  READY: 'ready',
  RUNNING: 'running',
  FINISHED: 'finished',
});
