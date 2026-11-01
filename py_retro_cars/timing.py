"""Средняя линия дорожного кольца для замера секторов реального заезда."""
from collections import deque

def reference_route(rows):
    """Середина полосы вокруг внутреннего острова травы, по часовой стрелке.

    Поддерживается формат прямоугольного кольца ЛР 1–2. Проверяем весь
    маршрут; произвольный лабиринт не подменяется выдуманным треком.
    """
    if not 5 <= len(rows) <= 100 or not rows or not 5 <= len(rows[0]) <= 100:
        raise ValueError("Размер карты должен быть от 5×5 до 100×100.")
    h, w = len(rows), len(rows[0])
    if any(len(row) != w or set(row) - set(".#F") for row in rows):
        raise ValueError("Карта должна быть прямоугольной; допустимы только ., #, F.")
    road = {(x, y) for y, row in enumerate(rows) for x, cell in enumerate(row) if cell in "#F"}
    finish = {(x, y) for x, y in road if rows[y][x] == "F"}
    if not finish:
        raise ValueError("На трассе отсутствует финиш F.")
    # Отделяем внешнюю траву заливкой от границы карты.
    outside = {(x, y) for y in range(h) for x in range(w)
               if (x in {0, w-1} or y in {0, h-1}) and rows[y][x] == "."}
    queue = deque(outside)
    while queue:
        x, y = queue.popleft()
        for p in ((x-1,y), (x+1,y), (x,y-1), (x,y+1)):
            a, b = p
            if 0 <= a < w and 0 <= b < h and rows[b][a] == "." and p not in outside:
                outside.add(p)
                queue.append(p)
    inner = {(x,y) for y in range(h) for x in range(w)
             if rows[y][x] == "." and (x,y) not in outside}
    if not inner:
        raise ValueError("Ожидается замкнутое прямоугольное кольцо вокруг острова травы.")
    ix0, ix1 = min(x for x,y in inner), max(x for x,y in inner)
    iy0, iy1 = min(y for x,y in inner), max(y for x,y in inner)
    if len(inner) != (ix1-ix0+1)*(iy1-iy0+1):
        raise ValueError("Внутренний остров должен быть прямоугольным.")
    left = (min(x for x,y in road) + ix0-1)//2
    right = (max(x for x,y in road) + ix1+1)//2
    top = (min(y for x,y in road) + iy0-1)//2
    bottom = (max(y for x,y in road) + iy1+1)//2
    route = ([(x,top) for x in range(left,right)] +
             [(right,y) for y in range(top,bottom)] +
             [(x,bottom) for x in range(right,left,-1)] +
             [(left,y) for y in range(bottom,top,-1)])
    if len(route) < 12 or any(p not in road for p in route):
        raise ValueError("Разрыв дорожного кольца или неподдерживаемая форма трассы.")
    starts = [i for i,p in enumerate(route) if p in finish]
    if not starts:
        raise ValueError("Финиш должен пересекать среднюю линию дорожного кольца.")
    start = starts[0]
    return route[start:] + route[:start]
