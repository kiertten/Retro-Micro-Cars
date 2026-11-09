import { WINDOW_HEIGHT, WINDOW_WIDTH } from '../../retro_cars_js/js/constants.js';
import { Rect } from '../../retro_cars_js/js/rect.js';

const ROAD_WIDTH = 72;
const MARGIN = ROAD_WIDTH / 2 + 18;

export class CatalogTrack {
  constructor(record) {
    this.name = record.name;
    this.roadWidth = ROAD_WIDTH;
    this.bounds = new Rect(0, 0, WINDOW_WIDTH, WINDOW_HEIGHT);

    const xs = record.corners.map(([x]) => x);
    const ys = record.corners.map(([, y]) => y);
    const minX = Math.min(...xs);
    const minY = Math.min(...ys);
    const width = Math.max(...xs) - minX;
    const height = Math.max(...ys) - minY;
    const scale = Math.min((WINDOW_WIDTH - 2 * MARGIN) / width, (WINDOW_HEIGHT - 2 * MARGIN) / height);
    if (!Number.isFinite(scale)) throw new Error('Масштаб контура трассы слишком мал');
    this.corners = record.corners.map(([x, y]) => ({
      x: (x - minX - width / 2) * scale + WINDOW_WIDTH / 2,
      y: (y - minY - height / 2) * scale + WINDOW_HEIGHT / 2,
    }));

    let distance = 0;
    this.segments = [];
    for (const [index, from] of this.corners.entries()) {
      const to = this.corners[(index + 1) % this.corners.length];
      const dx = to.x - from.x;
      const dy = to.y - from.y;
      const length = Math.hypot(dx, dy);
      if (length === 0) continue;
      this.segments.push({ from, length, distance, dx: dx / length, dy: dy / length });
      distance += length;
    }

    const first = this.segments.reduce((longest, edge) => edge.length > longest.length ? edge : longest);
    if (this.corners.every(({ x, y }) =>
      Math.abs((y - first.from.y) * first.dx - (x - first.from.x) * first.dy) < 1e-6)) {
      throw new Error('Для заезда нужны углы трассы, которые образуют контур');
    }

    const finishDistance = first.distance + first.length / 2;
    this.finish = this.pointAt(finishDistance);
    this.checkpoints = Array.from({ length: record.checkpoints }, (_, index) =>
      this.pointAt((finishDistance + distance * (index + 1) / (record.checkpoints + 1)) % distance));

    const start = this.pointAt(finishDistance - Math.min(70, first.length / 4));
    this.startPosition = [start.x, start.y, Math.atan2(start.dy, start.dx)];
  }

  pointAt(distance) {
    const edge = this.segments.find((segment) => distance < segment.distance + segment.length)
      ?? this.segments.at(-1);
    const offset = distance - edge.distance;
    return { x: edge.from.x + edge.dx * offset, y: edge.from.y + edge.dy * offset, dx: edge.dx, dy: edge.dy };
  }

  isGrass(x, y) {
    return !this.segments.some(({ from, dx, dy, length }) => {
      const localX = x - from.x;
      const localY = y - from.y;
      const along = Math.min(length, Math.max(0, localX * dx + localY * dy));
      return Math.hypot(localX - along * dx, localY - along * dy) <= this.roadWidth / 2;
    });
  }

  crossing(from, to, gate) {
    const start = (from.x - gate.x) * gate.dx + (from.y - gate.y) * gate.dy;
    const end = (to.x - gate.x) * gate.dx + (to.y - gate.y) * gate.dy;
    if (start >= 0 || end < 0) return null;
    const time = -start / (end - start);
    const x = from.x + (to.x - from.x) * time - gate.x;
    const y = from.y + (to.y - from.y) * time - gate.y;
    return Math.abs(y * gate.dx - x * gate.dy) <= this.roadWidth / 2 ? time : null;
  }
}
