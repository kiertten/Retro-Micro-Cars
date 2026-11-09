import { RACE_STATE } from '../../retro_cars_js/js/constants.js';

export function createScenarios(widget) {
  return Object.freeze({
    start() {
      if (widget.race.state === RACE_STATE.FINISHED) widget.resetRace();
      widget.race.start();
      widget.paused = false;
    },
    pause() {
      if (widget.race.state === RACE_STATE.RUNNING) {
        widget.paused = !widget.paused;
        widget.resetClock();
        widget.input.clear();
      }
    },
    restart() {
      widget.resetRace();
      widget.race.start();
    },
    toggleVisibility() {
      widget.limitedVisibility = !widget.limitedVisibility;
    },
    clearSkidMarks() {
      widget.skids.clear();
    },
  });
}
