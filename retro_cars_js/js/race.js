import { Car } from './car.js';
import { CHECKPOINT_Y, RACE_STATE, STEP_SECONDS, TOTAL_LAPS } from './constants.js';

export class Race {
  constructor(track) {
    this.track = track;
    this.reset();
  }

  reset() {
    this.car = new Car();
    this.state = RACE_STATE.READY;
    this.frame = 0;
    this.startFrame = null;
    this.lapStartFrame = null;
    this.lapTimes = [];
    this.events = [];
    this.passedCheckpoint = false;
    this.wasOnFinish = this.track.onFinish(this.car.x, this.car.y);
  }

  start() {
    if (this.state !== RACE_STATE.READY) return;
    this.state = RACE_STATE.RUNNING;
    this.record('race-start');
  }

  get bestLap() {
    return this.lapTimes.length === 0 ? null : Math.min(...this.lapTimes);
  }

  update(input = {}) {
    if (this.state !== RACE_STATE.RUNNING) return;

    this.frame += 1;
    const { drifting, onGrass } = this.car;
    this.car.update(input, this.track);
    if (this.car.drifting !== drifting) {
      this.record(this.car.drifting ? 'drift-start' : 'drift-end');
    }
    if (this.car.onGrass !== onGrass) {
      this.record(this.car.onGrass ? 'grass-enter' : 'grass-exit');
    }

    if (this.car.y > CHECKPOINT_Y) this.passedCheckpoint = true;
    const onFinish = this.track.onFinish(this.car.x, this.car.y);
    const crossed = onFinish && !this.wasOnFinish && this.car.vx > 0;
    this.wasOnFinish = onFinish;
    if (!crossed) return;

    if (this.startFrame === null) {
      this.startFrame = this.frame;
      this.lapStartFrame = this.frame;
      this.passedCheckpoint = false;
      this.record('timing-start');
      return;
    }
    if (!this.passedCheckpoint) return;

    const seconds = (this.frame - this.lapStartFrame) * STEP_SECONDS;
    this.lapTimes.push(seconds);
    this.lapStartFrame = this.frame;
    this.passedCheckpoint = false;
    this.record('lap', { number: this.lapTimes.length, seconds });

    if (this.lapTimes.length === TOTAL_LAPS) {
      this.state = RACE_STATE.FINISHED;
      this.record('race-finish', { seconds: (this.frame - this.startFrame) * STEP_SECONDS });
    }
  }

  record(type, details = {}) {
    this.events.push({ type, frame: this.frame, ...details });
  }
}
