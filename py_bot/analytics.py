"""Проверка выгрузок игры, общий рейтинг отдельно для каждой трассы."""
from collections import deque
import hashlib
import json
import math
from pathlib import Path
from html import escape
from .session import atomic_json

MAX_FILE_SIZE = 1_000_000
SECTOR_VERSION = 2


def parse_track(text):
    rows = text.lstrip("\ufeff").splitlines()
    if len(rows) != 15 or any(len(row) != 20 for row in rows):
        raise ValueError("Трек игры должен содержать 15 строк по 20 символов.")
    if any(set(row)-set(".#F") for row in rows):
        raise ValueError("В треке допустимы только #, . и F.")
    road = {(x,y) for y,row in enumerate(rows) for x,c in enumerate(row) if c in "#F"}
    finish = {p for p in road if rows[p[1]][p[0]] == "F"}
    if not finish:
        raise ValueError("Нет финиша F.")
    if rows[2][7] == ".":
        raise ValueError("Старт игры (300, 100) должен находиться на дороге.")
    def flood(points, start):
        seen, queue = {start}, deque([start])
        while queue:
            x,y = queue.popleft()
            for p in ((x-1,y),(x+1,y),(x,y-1),(x,y+1)):
                if p in points and p not in seen:
                    seen.add(p); queue.append(p)
        return seen
    if flood(road,next(iter(road))) != road:
        raise ValueError("Дорожные клетки должны образовывать одну связанную область.")
    if flood(finish,next(iter(finish))) != finish:
        raise ValueError("Плитки F должны образовывать одну связанную линию финиша.")
    canonical = "\n".join(rows)
    track_id = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    return {"id":track_id,"rows":rows,"road_cells":len(road),"finish_cells":len(finish)}


def number(value):
    return type(value) in (int,float) and math.isfinite(value) and 0 < value <= 86400


def parse_records(text, track_id):
    try:
        raw = json.loads(text.lstrip("\ufeff"),parse_constant=lambda value: (_ for _ in ()).throw(ValueError("NaN/Infinity запрещены")))
    except (ValueError, RecursionError) as error:
        raise ValueError("Некорректный JSON: "+str(error)[:100]) from error
    if not isinstance(raw,dict) or not isinstance(raw.get("records"),list):
        raise ValueError('Ожидается объект {"records": [...]} из игры.')
    if len(raw["records"]) > 10000:
        raise ValueError("В одном файле допускается не более 10000 записей.")
    valid, errors = [], []
    for index,item in enumerate(raw["records"],1):
        try:
            if not isinstance(item,dict):
                raise ValueError("запись не является объектом")
            name = item.get("name")
            if not isinstance(name,str) or not 1 <= len(name.strip()) <= 64 or any(ord(c)<32 for c in name):
                raise ValueError("имя должно содержать от 1 до 64 печатных символов")
            best, total = item.get("best_lap"),item.get("total_time")
            if not number(best) or not number(total) or total < best:
                raise ValueError("неверное время круга или заезда")
            date = item.get("date","")
            if not isinstance(date,str) or len(date)>64 or any(ord(c)<32 for c in date):
                raise ValueError("неверная дата")
            if item.get("track_id",track_id) != track_id:
                raise ValueError("результат относится к другой трассе")
            sectors = item.get("sectors")
            if sectors is not None and (not isinstance(sectors,list) or len(sectors)!=3 or
                                        not all(number(s) for s in sectors) or abs(sum(sectors)-best)>0.1):
                raise ValueError("sectors: нужны 3 положительных времени с суммой best_lap (±0.1 с)")
            sector_version = item.get("sector_version",1) if sectors else None
            if sectors and (type(sector_version) is not int or sector_version not in (1,SECTOR_VERSION)):
                raise ValueError("неизвестная версия границ секторов")
            valid.append({"name":name.strip(),"best_lap":float(best),"total_time":float(total),
                          "date":date,"sectors":[float(s) for s in sectors] if sectors else None,
                          "sector_version":sector_version,"track_id":track_id})
        except ValueError as error:
            errors.append(f"Запись {index}: {error}")
    return valid,errors


def record_key(record):
    # Дедупликация одинаковой выгрузки, независимо от форматирования JSON.
    return json.dumps(record,sort_keys=True,ensure_ascii=False,separators=(",",":"))


def load_records(root, track_id):
    path = Path(root)/"leaderboards"/(track_id+".json")
    try:
        raw = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return []
    records,errors = parse_records(raw,track_id)
    if errors:
        raise ValueError("Повреждена база рейтинга; восстановите файл из резервной копии.")
    return records


def merge_records(root, track_id, incoming):
    records = load_records(root,track_id)
    seen = {record_key(r) for r in records}
    before = best_metrics(records)
    added = 0
    for record in incoming:
        key = record_key(record)
        if key not in seen:
            records.append(record); seen.add(key); added += 1
    if len(records)>10000:
        raise ValueError("База этой трассы заполнена (10000 записей).")
    if added:
        atomic_json(Path(root)/"leaderboards"/(track_id+".json"),{"records":records})
    after = best_metrics(records)
    improved = [label for label,value in after.items() if value < before.get(label,math.inf)]
    return added,len(incoming)-added,improved


def best_metrics(records):
    result = {}
    for record in records:
        result["Круг"] = min(result.get("Круг",math.inf),record["best_lap"])
        if record["sectors"] and record.get("sector_version")==SECTOR_VERSION:
            for i,value in enumerate(record["sectors"],1):
                label = f"S{i}"
                result[label] = min(result.get(label,math.inf),value)
    return result


def leaderboard(records, metric="lap"):
    if metric not in ("lap","s1","s2","s3"):
        raise ValueError("Неизвестная метрика")
    pilots = {}
    for r in records:
        if metric != "lap" and (not r["sectors"] or r.get("sector_version")!=SECTOR_VERSION):
            continue
        value = r["best_lap"] if metric=="lap" else r["sectors"][int(metric[1])-1]
        pilots[r["name"]] = min(pilots.get(r["name"],math.inf),value)
    rows = sorted(pilots.items(),key=lambda item:(item[1],item[0].casefold()))[:10]
    title = "Круг" if metric=="lap" else metric.upper()
    lines = [f"<b>Рейтинг — {title}</b>"]
    lines += [f"{i}. {escape(name)} — {value:.3f} с" for i,(name,value) in enumerate(rows,1)]
    if not rows:
        lines.append("Пока нет данных. Загрузите records.json игры через /upload.")
    if metric != "lap":
        lines.append("Показаны полные секторные замеры версии 2. Старые замеры и записи без секторов не включены.")
    return "\n".join(lines)


def statistics(records, name=None):
    selected = [r for r in records if name is None or r["name"]==name]
    if not selected:
        return "Результаты пилота не найдены." if name else "Статистики пока нет. Загрузите records.json."
    names = sorted({r["name"] for r in selected},key=str.casefold)
    lines = [f"<b>Статистика пилотов</b>\nЗаписей: {len(selected)}; пилотов: {len(names)}."]
    for pilot in names[:15]:
        rows = [r for r in selected if r["name"]==pilot]
        lines.append(f"\n{escape(pilot)}: заездов в выгрузках {len(rows)}; лучший круг {min(r['best_lap'] for r in rows):.3f} с; "
                     f"среднее лучших кругов {sum(r['best_lap'] for r in rows)/len(rows):.3f} с.")
        measured = [r for r in rows if r["sectors"] and r.get("sector_version")==SECTOR_VERSION]
        if measured:
            lines.append("Лучшие секторы: "+"; ".join(f"S{i+1}={min(r['sectors'][i] for r in measured):.3f} с" for i in range(3)))
    if len(names)>15:
        lines.append("Показаны первые 15 пилотов. /stats Имя — поиск точного имени.")
    lines.append("Это статистика загруженных рекордов, а не всех сыгранных заездов.")
    return "\n".join(lines)
