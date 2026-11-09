import { Rect } from './rect.js';
import { START_POSITION, TILE_SIZE, WINDOW_HEIGHT, WINDOW_WIDTH } from './constants.js';

const ROWS = WINDOW_HEIGHT / TILE_SIZE;
const COLUMNS = WINDOW_WIDTH / TILE_SIZE;

export class Track {
  constructor(tiles) {
    if (!Array.isArray(tiles) || tiles.length !== ROWS
      || tiles.some((row) => typeof row !== 'string' || row.length !== COLUMNS || /[^#.F]/.test(row))) {
      throw new Error('Ожидаются 15 строк по 20 символов из набора #.F.');
    }
    this.tiles = Object.freeze([...tiles]);
    this.bounds = new Rect(0, 0, WINDOW_WIDTH, WINDOW_HEIGHT);
    this.finishZones = [];
    for (const [row, line] of this.tiles.entries()) {
      for (let column = 0; column < COLUMNS; column += 1) {
        if (line[column] === 'F') {
          this.finishZones.push(new Rect(column * TILE_SIZE, row * TILE_SIZE, TILE_SIZE, TILE_SIZE));
        }
      }
    }
    if (this.finishZones.length === 0) throw new Error('На трассе нужна финишная плитка F.');
    if (this.isGrass(...START_POSITION)) throw new Error('Стартовая позиция должна быть на дороге.');
  }

  static fromJSON(text) {
    let config;
    try {
      config = JSON.parse(text);
    } catch (error) {
      throw new Error('Ошибка JSON трассы: ' + error.message);
    }
    return new Track(config?.tiles);
  }

  tileAt(x, y) {
    if (!this.bounds.collidepoint(x, y)) return '.';
    return this.tiles[Math.floor(y / TILE_SIZE)][Math.floor(x / TILE_SIZE)];
  }

  isGrass(x, y) {
    return this.tileAt(x, y) === '.';
  }

  onFinish(x, y) {
    return this.finishZones.some((zone) => zone.collidepoint(x, y));
  }
}
