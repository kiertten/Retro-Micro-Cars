const ACTION_KEYS = ['KeyW', 'KeyS', 'KeyA', 'KeyD', 'ArrowUp', 'ArrowDown', 'ArrowLeft', 'ArrowRight'];
const SCENARIO_KEYS = { KeyP: 'pause', KeyR: 'restart' };

export function createInput(scenarios) {
  const pressed = Object.create(null);
  const clear = () => ACTION_KEYS.forEach((key) => { pressed[key] = false; });

  window.addEventListener('keydown', (event) => {
    if (event.ctrlKey || event.altKey || event.metaKey) return;
    if (ACTION_KEYS.includes(event.code)) {
      event.preventDefault();
      pressed[event.code] = true;
    } else if (!event.repeat && Object.hasOwn(SCENARIO_KEYS, event.code)) {
      event.preventDefault();
      scenarios[SCENARIO_KEYS[event.code]]();
    }
  });
  window.addEventListener('keyup', (event) => {
    if (ACTION_KEYS.includes(event.code)) pressed[event.code] = false;
  });
  window.addEventListener('blur', clear);
  document.addEventListener('visibilitychange', clear);

  return {
    clear,
    read() {
      return {
        throttle: Boolean(pressed.KeyW || pressed.ArrowUp),
        brake: Boolean(pressed.KeyS || pressed.ArrowDown),
        steer: Number(Boolean(pressed.KeyD || pressed.ArrowRight))
          - Number(Boolean(pressed.KeyA || pressed.ArrowLeft)),
      };
    },
  };
}
