"""
Математика движения машины (без зависимости от Pygame).

Вынесена в отдельный модуль, чтобы формулы дрифта можно было
проверять обычными тестами без запуска окна.

Модель:
    theta  - угол кузова (куда «смотрит» нос машины)
    speed  - линейная скорость вдоль кузова (может быть < 0 при заднем ходе)
    vx, vy - ФАКТИЧЕСКИЙ вектор движения (куда машина реально едет)

Каждый кадр вектор движения плавно приближается к «идеальному» вектору,
направленному по кузову:
    target = (cos(theta) * speed, sin(theta) * speed)
    v += (target - v) * K
Чем меньше K, тем дольше машина «помнит» прежнее направление - это и есть занос.
"""

import math

from py_retro_cars.constants import (
    ACCELERATION,
    BRAKE_POWER,
    DRIFT_ANGLE_THRESHOLD,
    DRIFT_MIN_SPEED,
    DRIFT_SPEED_LOSS,
    MAX_REVERSE_SPEED,
    MAX_SPEED,
    MIN_STEER_SPEED,
    OVERSPEED_DECEL,
    ROLLING_FRICTION,
    TURN_RATE,
)


def clamp(value, low, high):
    """Ограничивает значение диапазоном [low, high]."""
    return max(low, min(high, value))


def normalize_angle(angle):
    """Приводит угол к диапазону (-pi, pi]."""
    while angle > math.pi:
        angle -= 2 * math.pi
    while angle <= -math.pi:
        angle += 2 * math.pi
    return angle


def update_speed(speed, throttle, brake, max_speed=MAX_SPEED):
    """
    Обновляет линейную скорость за один кадр.

    throttle - True, если нажата W (разгон)
    brake    - True, если нажата S (тормоз, а затем задний ход)
    max_speed - предел скорости на текущем покрытии (на траве он ниже)
    """
    if throttle and not brake:
        speed += ACCELERATION
    elif brake and not throttle:
        # Тормозим сильнее, чем разгоняемся; после остановки - задний ход.
        speed -= BRAKE_POWER if speed > 0 else ACCELERATION
    else:
        # Газ не нажат: машина плавно катится до остановки.
        if speed > 0:
            speed = max(0.0, speed - ROLLING_FRICTION)
        elif speed < 0:
            speed = min(0.0, speed + ROLLING_FRICTION)
    # Ограничение максимальной скорости. Если машина заехала на траву на
    # большой скорости, превышение предела гасится быстро, но не мгновенно.
    if speed > max_speed:
        speed = max(max_speed, speed - OVERSPEED_DECEL)
    return clamp(speed, MAX_REVERSE_SPEED, MAX_SPEED)


def update_heading(theta, speed, steer):
    """
    Поворачивает кузов. steer: -1 (влево, A), 0, +1 (вправо, D).

    Руль зависит от скорости: на месте машина не поворачивается, при
    заднем ходе направление руля инвертируется (как у настоящей машины).
    """
    if steer == 0:
        return theta
    steer_factor = clamp(speed / MIN_STEER_SPEED, -1.0, 1.0)
    return normalize_angle(theta + steer * TURN_RATE * steer_factor)


def update_velocity(vx, vy, theta, speed, grip_k):
    """
    Плавно приближает вектор движения к направлению кузова.

    grip_k - коэффициент сцепления K (0..1). Возвращает новые (vx, vy).
    """
    target_x = math.cos(theta) * speed
    target_y = math.sin(theta) * speed
    vx += (target_x - vx) * grip_k
    vy += (target_y - vy) * grip_k
    return vx, vy


def slip_angle(vx, vy, theta):
    """
    Угол заноса - модуль угла между направлением движения и кузовом (рад).
    Если машина почти стоит, угол считается нулевым.
    """
    if math.hypot(vx, vy) < 0.1:
        return 0.0
    move_angle = math.atan2(vy, vx)
    return abs(normalize_angle(move_angle - theta))


def is_drifting(vx, vy, theta):
    """True, если машина быстро едет и угол заноса превышает порог."""
    return (
        math.hypot(vx, vy) >= DRIFT_MIN_SPEED
        and slip_angle(vx, vy, theta) > DRIFT_ANGLE_THRESHOLD
    )


def apply_drift_loss(speed, drifting):
    """В заносе часть скорости теряется (боковое скольжение тормозит)."""
    if drifting and speed > 0:
        return speed * (1.0 - DRIFT_SPEED_LOSS)
    return speed
