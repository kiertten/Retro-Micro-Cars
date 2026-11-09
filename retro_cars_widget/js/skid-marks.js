import { CAR_LENGTH, CAR_WIDTH } from '../../retro_cars_js/js/constants.js';

export const SKID_LIFETIME = 240;

function rearWheels({ x, y, theta }) {
  const back = -CAR_LENGTH / 2 + 5;
  const halfAxle = CAR_WIDTH / 2 - 2;
  const cos = Math.cos(theta);
  const sin = Math.sin(theta);
  return [-halfAxle, halfAxle].map((offset) => ({
    x: x + back * cos - offset * sin,
    y: y + back * sin + offset * cos,
  }));
}

export class SkidMarks {
  segments = [];
  previous = null;

  update(car, track, frame) {
    const wheels = rearWheels(car);
    const onRoad = !track.isGrass(car.x, car.y);
    this.segments = this.segments.filter(({ born }) => frame - born < SKID_LIFETIME);

    if (car.drifting && onRoad && this.previous?.onRoad) {
      wheels.forEach((end, index) => {
        const start = this.previous.wheels[index];
        if (Math.hypot(end.x - start.x, end.y - start.y) > 0.05) {
          this.segments.push({ start, end, born: frame });
        }
      });
    }
    this.previous = { wheels, onRoad };
  }

  clear() {
    this.segments = [];
    this.previous = null;
  }
}
