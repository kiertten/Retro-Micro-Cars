export class Rect {
  constructor(x, y, width, height) {
    this.x = x;
    this.y = y;
    this.width = width;
    this.height = height;
  }

  get center() {
    return [this.x + this.width / 2, this.y + this.height / 2];
  }

  move(dx, dy) {
    return new Rect(this.x + dx, this.y + dy, this.width, this.height);
  }

  collidepoint(x, y) {
    return x >= this.x && x < this.x + this.width
      && y >= this.y && y < this.y + this.height;
  }

  colliderect(other) {
    return this.x < other.x + other.width && this.x + this.width > other.x
      && this.y < other.y + other.height && this.y + this.height > other.y;
  }
}
