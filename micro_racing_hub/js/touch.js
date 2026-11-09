import { clamp } from '../../retro_cars_js/js/physics.js';

export function createTouchControls(panel) {
  const stick = panel.querySelector('.joystick');
  const throttle = panel.querySelector('[data-pedal="throttle"]');
  const brake = panel.querySelector('[data-pedal="brake"]');

  const steering = bindPointer(stick, (event) => {
    if (!event) {
      stick.style.removeProperty('--stick-offset');
      return 0;
    }
    const { left, width } = stick.getBoundingClientRect();
    const position = clamp((event.clientX - left - width / 2) / (width * 0.33), -1, 1);
    stick.style.setProperty('--stick-offset', (position * width * 0.28) + 'px');
    return Math.abs(position) < 0.12 ? 0 : position;
  });
  const gas = bindPointer(throttle, (event) => Boolean(event));
  const stop = bindPointer(brake, (event) => Boolean(event));

  return {
    get steer() { return steering.value; },
    get throttle() { return gas.value; },
    get brake() { return stop.value; },
    clear() {
      steering.clear();
      gas.clear();
      stop.clear();
    },
  };
}

function bindPointer(element, readValue) {
  let pointer = null;
  let value = readValue(null);

  function clear() {
    const id = pointer;
    pointer = null;
    value = readValue(null);
    element.removeAttribute('data-held');
    if (id !== null && element.hasPointerCapture(id)) element.releasePointerCapture(id);
  }

  element.addEventListener('pointerdown', (event) => {
    if (pointer !== null || event.button !== 0) return;
    event.preventDefault();
    pointer = event.pointerId;
    element.setPointerCapture(pointer);
    element.setAttribute('data-held', '');
    value = readValue(event);
  });
  element.addEventListener('pointermove', (event) => {
    if (event.pointerId === pointer) value = readValue(event);
  });
  for (const type of ['pointerup', 'pointercancel', 'lostpointercapture']) {
    element.addEventListener(type, (event) => {
      if (event.pointerId === pointer) clear();
    });
  }
  return { get value() { return value; }, clear };
}
