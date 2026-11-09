import { RACE_STATE, STEP_SECONDS } from '../../retro_cars_js/js/constants.js';
import { Race } from '../../retro_cars_js/js/race.js';
import { Track } from '../../retro_cars_js/js/track.js';
import { createInput } from './input.js';
import { createRenderer } from './renderer.js';
import { createScenarios } from './scenarios.js';
import { SkidMarks } from './skid-marks.js';

const STEP_MS = STEP_SECONDS * 1000;
const MAX_DELTA_MS = 100;

export async function loadDefaultTrack() {
  const response = await fetch(new URL('../../retro_cars_js/track.json', import.meta.url));
  if (!response.ok) throw new Error('Не удалось загрузить карту трассы (' + response.status + ')');
  return Track.fromJSON(await response.text());
}

export function mountRace(canvas, { track, updateHud, controls, touch }) {
  let render = createRenderer(canvas, track);
  let accumulator = 0;
  let lastTime = null;

  const widget = {
    race: new Race(track),
    skids: new SkidMarks(),
    paused: false,
    limitedVisibility: false,
    resetClock() {
      accumulator = 0;
      lastTime = null;
    },
    resetRace() {
      this.race.reset();
      this.skids.clear();
      this.input.clear();
      this.paused = false;
      this.resetClock();
    },
  };
  const scenarios = createScenarios(widget);
  widget.input = createInput(scenarios, touch);

  for (const button of controls) {
    button.disabled = false;
    button.addEventListener('click', () => scenarios[button.dataset.scenario]());
  }
  document.addEventListener('visibilitychange', () => widget.resetClock());

  function setTrack(nextTrack) {
    render = createRenderer(canvas, nextTrack);
    widget.race = new Race(nextTrack);
    widget.resetRace();
  }

  function loop(now) {
    const { race } = widget;
    const delta = lastTime === null ? 0 : Math.min(now - lastTime, MAX_DELTA_MS);
    lastTime = now;
    if (race.state === RACE_STATE.RUNNING && !widget.paused) {
      accumulator += delta;
      while (accumulator >= STEP_MS && race.state === RACE_STATE.RUNNING) {
        race.update(widget.input.read());
        widget.skids.update(race.car, race.track, race.frame);
        accumulator -= STEP_MS;
      }
    }
    render(widget);
    updateHud(widget);
    requestAnimationFrame(loop);
  }
  requestAnimationFrame(loop);
  return { widget, scenarios, setTrack };
}
