import { Car } from './car.js';
import { CHECKPOINT_Y, RACE_STATE, STEP_SECONDS, TOTAL_LAPS } from './constants.js';

export class Race {
  constructor(track) {
    this.track = track;
    this.reset();
  }

  reset() {
    this.car = new Car(...(this.track.startPosition ?? []));
    this.state = RACE_STATE.READY;
    this.frame = 0;
    this.startFrame = null;
    this.lapStartFrame = null;
    this.lapTimes = [];
    this.events = [];
    this.passedCheckpoint = false;
    this.wasOnFinish = this.track.onFinish?.(this.car.x, this.car.y) ?? false;
    this.nextCheckpoint = 0;
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
    const { drifting, onGrass, x, y } = this.car;
    this.car.update(input, this.track);
    if (this.car.drifting !== drifting) {
      this.record(this.car.drifting ? 'drift-start' : 'drift-end');
    }
    if (this.car.onGrass !== onGrass) {
      this.record(this.car.onGrass ? 'grass-enter' : 'grass-exit');
    }

    if (!this.crossedFinish({ x, y })) return;

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
    this.nextCheckpoint = 0;
    this.record('lap', { number: this.lapTimes.length, seconds });

    if (this.lapTimes.length === TOTAL_LAPS) {
      this.state = RACE_STATE.FINISHED;
      this.record('race-finish', { seconds: (this.frame - this.startFrame) * STEP_SECONDS });
    }
  }

  crossedFinish(previous) {
    if (this.track.finish) {
      const finish = this.track.crossing(previous, this.car, this.track.finish);
      if (this.startFrame !== null) {
        let lastCrossing = -1;
        while (this.nextCheckpoint < this.track.checkpoints.length) {
          const gate = this.track.checkpoints[this.nextCheckpoint];
          const time = this.track.crossing(previous, this.car, gate);
          if (time === null || time <= lastCrossing || time >= (finish ?? Infinity)) break;
          this.nextCheckpoint += 1;
          lastCrossing = time;
        }
      }
      this.passedCheckpoint = this.nextCheckpoint === this.track.checkpoints.length;
      return finish !== null;
    }

    if (this.car.y > CHECKPOINT_Y) this.passedCheckpoint = true;
    const onFinish = this.track.onFinish(this.car.x, this.car.y);
    const crossed = onFinish && !this.wasOnFinish && this.car.vx > 0;
    this.wasOnFinish = onFinish;
    return crossed;
  }

  record(type, details = {}) {
    this.events.push({ type, frame: this.frame, ...details });
  }
}
