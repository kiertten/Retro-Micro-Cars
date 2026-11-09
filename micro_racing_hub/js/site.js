import { CatalogTrack } from '../../retro_cars_widget/js/catalog-track.js';
import { loadDefaultTrack, mountRace } from '../../retro_cars_widget/js/race-widget.js';
import { createHud } from './hud.js';
import { mountHotbar } from './hotbar.js';
import { createTouchControls } from './touch.js';

const byId = (id) => document.getElementById(id);
const number = new Intl.NumberFormat('ru-RU', { maximumFractionDigits: 2 });

async function boot() {
  const standard = await loadDefaultTrack();
  const game = mountRace(byId('track'), {
    track: standard,
    updateHud: createHud(byId('telemetry')),
    controls: document.querySelectorAll('[data-scenario]'),
    touch: createTouchControls(byId('touch-controls')),
  });

  const hotbar = mountHotbar(byId('track-list'), byId('track-notice'), (record) => {
    game.setTrack(record ? new CatalogTrack(record) : standard);
    byId('track-name').textContent = record?.name ?? 'Кольцевая трасса';
    byId('track-details').textContent = record
      ? number.format(record.length) + ' м · КП ' + record.checkpoints : '3 круга';
    const url = new URL(window.location.href);
    if (record) url.searchParams.set('track', record.id);
    else url.searchParams.delete('track');
    history.replaceState(null, '', url);
  });

  const trackId = new URLSearchParams(window.location.search).get('track');
  if (trackId !== null) hotbar.select(trackId);
  // Тот же интерфейс сценариев, что у виджета ЛР 5.
  window.RetroMicroCars = Object.freeze({ widget: game.widget, scenarios: game.scenarios });
}

boot().catch((error) => {
  byId('race-status').textContent = 'Ошибка загрузки';
  byId('track-notice').textContent = error.message;
  console.error(error);
});
