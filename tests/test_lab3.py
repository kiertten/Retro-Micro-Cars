"""Проверки сервиса аналитики с настоящим Dispatcher aiogram 3."""
import asyncio
import itertools
import json
import os
from pathlib import Path
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch
from aiogram import Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.client.session.base import BaseSession
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramBadRequest
from aiogram.methods import AnswerCallbackQuery, EditMessageText, SendMessage
from aiogram.types import Message, Update
from py_bot import analytics
from py_bot.bot import create_dispatcher
from py_bot.config import TRACK_PATH
from py_bot.session import Store

class Transport(BaseSession):
    def __init__(self):
        super().__init__()
        self.calls = []
        self.next_id = 100
        self.edit_error = None

    async def close(self):
        pass

    async def make_request(self, bot, method, timeout=None):
        self.calls.append(method)
        if isinstance(method, EditMessageText) and self.edit_error:
            raise TelegramBadRequest(method=method,message=self.edit_error)
        if isinstance(method, AnswerCallbackQuery):
            return True
        if isinstance(method, (SendMessage, EditMessageText)):
            self.next_id += 1
            return Message.model_validate({"message_id":getattr(method,"message_id",None) or self.next_id,
                                           "date":1700000000,"chat":{"id":int(method.chat_id),"type":"private"},
                                           "text":method.text},context={"bot":bot})
        raise AssertionError(type(method))

    async def stream_content(self, *args, **kwargs):
        yield b""


def export(name="Анна",best=30,sectors=None):
    return json.dumps({"records":[{"name":name,"best_lap":best,"total_time":best*3,
                                   "sectors":sectors,"sector_version":2 if sectors else None,
                                   "date":"2026-11-01 20:00:00"}]},ensure_ascii=False)


class AnalyticsTests(unittest.TestCase):
    def setUp(self):
        self.track = analytics.parse_track(TRACK_PATH.read_text(encoding="utf-8"))

    def test_track_validation_and_canonical_id(self):
        text = TRACK_PATH.read_text(encoding="utf-8")
        self.assertEqual(self.track["id"],analytics.parse_track("\ufeff"+text.replace("\n","\r\n"))["id"])
        for bad in (text.replace("F","#"),text.replace("F","X"),text[:-20],"."*20+"\n"):
            with self.assertRaises(ValueError):
                analytics.parse_track(bad)
        rows = text.splitlines()
        rows[0] = "#"+rows[0][1:]
        with self.assertRaises(ValueError):
            analytics.parse_track("\n".join(rows))

    def test_records_strict_validation_partial_acceptance(self):
        good = json.loads(export(sectors=[9,10,11]))["records"][0]
        bads = [dict(good,best_lap=True),dict(good,best_lap=-1),dict(good,sectors=[1,2,3]),
                dict(good,sectors=[9,"10",11]),dict(good,track_id="wrong"),dict(good,name=""),dict(good,total_time=1)]
        valid,errors = analytics.parse_records(json.dumps({"records":[good]+bads}),self.track["id"])
        self.assertEqual((len(valid),len(errors)),(1,7))
        for text in ('{"records":[NaN]}','{"records":[]','[]'):
            with self.assertRaises(ValueError):
                analytics.parse_records(text,self.track["id"])

    def test_duplicates_track_isolation_and_metrics(self):
        with tempfile.TemporaryDirectory() as temp:
            records,_ = analytics.parse_records(export(sectors=[9,10,11]),self.track["id"])
            self.assertEqual(analytics.merge_records(temp,self.track["id"],records)[:2],(1,0))
            self.assertEqual(analytics.merge_records(temp,self.track["id"],records),(0,1,[]))
            self.assertEqual(analytics.load_records(temp,"a"*64),[])
            self.assertEqual(analytics.best_metrics(records),{"Круг":30,"S1":9,"S2":10,"S3":11})

    def test_rankings_unique_pilots_escape_and_legacy(self):
        old,_ = analytics.parse_records(export(name="<Анна>",best=35),self.track["id"])
        new,_ = analytics.parse_records(export(name="<Анна>",best=30,sectors=[9,10,11]),self.track["id"])
        text = analytics.leaderboard(old+new)
        self.assertEqual(text.count("&lt;Анна&gt;"),1)
        self.assertIn("30.000",text)
        self.assertNotIn("35.000",text)
        self.assertNotIn("35.000",analytics.leaderboard(old,"s1"))
        self.assertIn("среднее",analytics.statistics(old+new,"<Анна>"))

    def test_old_sector_boundaries_are_not_compared_with_new(self):
        raw = json.loads(export(name="Старый",sectors=[9,10,11]))
        raw["records"][0].pop("sector_version")
        rows,errors = analytics.parse_records(json.dumps(raw),self.track["id"])
        self.assertFalse(errors)
        self.assertIn("Старый",analytics.leaderboard(rows,"lap"))
        self.assertNotIn("Старый",analytics.leaderboard(rows,"s1"))


class BotTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.store = Store(self.temp.name)
        self.transport = Transport()
        self.bot = Bot("123456:TEST_TOKEN_FOR_OFFLINE_TESTS",session=self.transport,
                       default=DefaultBotProperties(parse_mode=ParseMode.HTML))
        self.dp = create_dispatcher(self.store)
        self.counter = itertools.count(10)
        self.clock = patch("py_bot.bot.time",SimpleNamespace(monotonic=lambda:next(self.counter)))
        self.clock.start()
        self.update_id = 0

    async def asyncTearDown(self):
        self.clock.stop()
        await self.dp.fsm.events_isolation.close()
        await self.bot.session.close()
        self.temp.cleanup()

    async def send(self,text=None,action=None,user_id=7,document=None,message_id=None):
        self.update_id += 1
        user = {"id":user_id,"is_bot":False,"first_name":"Test"}
        message = {"message_id":message_id or self.store.load_session(user_id).get("screen_message_id",1),
                   "date":1700000000,"chat":{"id":user_id,"type":"private"},"from":user}
        if document:
            message["document"] = document
        else:
            message["text"] = text or "screen"
        if action is None:
            raw = {"update_id":self.update_id,"message":message}
        else:
            raw = {"update_id":self.update_id,"callback_query":{"id":str(self.update_id),"from":user,
                    "chat_instance":"test","data":action,"message":message}}
        await self.dp.feed_update(self.bot,Update.model_validate(raw,context={"bot":self.bot}))

    async def upload(self,content,name="records.json",user_id=7,mime=None,size=None):
        payload = content.encode("utf-8") if isinstance(content,str) else content
        async def download(document,destination,**kwargs):
            destination.write(payload)
        document = {"file_id":"test","file_unique_id":"test", "file_name":name,
                    "mime_type":mime or ("text/plain" if name.endswith(".txt") else "application/json"),
                    "file_size":len(payload) if size is None else size}
        with patch.object(self.bot,"download",download):
            await self.send(document=document,user_id=user_id)

    def last_text(self):
        return next(c.text for c in reversed(self.transport.calls) if isinstance(c,(SendMessage,EditMessageText)))

    async def test_commands_upload_rankings_and_stats(self):
        await self.send(text="/start")
        await self.send(text="/upload")
        self.assertEqual(self.store.load_session(7)["state"],"Engineer:UPLOAD")
        await self.upload(TRACK_PATH.read_text(encoding="utf-8"),name="track.txt")
        self.assertIn("Трек принят",self.last_text())
        await self.upload(export(sectors=[9,10,11]))
        self.assertIn("Добавлено: 1",self.last_text())
        await self.upload(export(sectors=[9,10,11]))
        self.assertIn("дубликатов: 1",self.last_text())
        for command in ("/top","/top s1","/top s2","/top s3","/stats Анна","/help"):
            await self.send(text=command)
            self.assertNotIn("Ошибка",self.last_text())
        self.assertEqual(sum(isinstance(c,SendMessage) for c in self.transport.calls),1)

    async def test_watch_notification_duplicate_and_toggle(self):
        await self.send(text="/start",user_id=8)
        await self.send(text="/watch",user_id=8)
        self.assertIsNotNone(self.store.load_session(8).get("watch_track"))
        await self.send(text="/upload")
        await self.upload(export(sectors=[9,10,11]))
        notifications = [c for c in self.transport.calls if isinstance(c,SendMessage) and c.text.startswith("Новый рекорд")]
        self.assertEqual(len(notifications),1)
        self.assertEqual(notifications[0].chat_id,8)
        await self.upload(export(sectors=[9,10,11]))
        self.assertEqual(sum(isinstance(c,SendMessage) and c.text.startswith("Новый рекорд") for c in self.transport.calls),1)
        await self.send(text="/watch",user_id=8)
        self.assertNotIn("watch_track",self.store.load_session(8))

    async def test_invalid_upload_preserves_track_and_records(self):
        await self.send(text="/top")
        original = self.store.load_session(7)["track_id"]
        await self.send(text="/upload")
        for text,name in (("bad","track.txt"),("{}","records.json"),(b"\xff","track.txt")):
            await self.upload(text,name)
            self.assertIn("Файл не принят",self.last_text())
            self.assertEqual(self.store.load_session(7)["track_id"],original)
        await self.upload("x","program.exe",mime="application/octet-stream")
        self.assertIn("Нужен документ",self.last_text())
        await self.upload("x",size=1_000_001)
        self.assertIn("Размер файла",self.last_text())
        self.assertEqual(analytics.load_records(self.store.root,original),[])

    async def test_sessions_restart_and_different_tracks(self):
        await self.send(text="/upload")
        text = TRACK_PATH.read_text(encoding="utf-8")
        await self.upload(text,"track.txt")
        first = self.store.load_session(7)["track_id"]
        await self.send(text="/upload",user_id=8)
        # Связанное расширение дорожного покрытия меняет идентификатор трассы.
        rows = text.splitlines();rows[0] = rows[0][:5]+"#"+rows[0][6:]
        await self.upload("\n".join(rows),"track.txt",user_id=8)
        self.assertNotEqual(self.store.load_session(8)["track_id"],first)
        self.assertEqual(Store(self.temp.name).load_session(7)["state"],"Engineer:UPLOAD")
        self.store.path("sessions",7).write_text("{broken",encoding="utf-8")
        await self.send(text="/start")
        self.assertEqual(self.store.load_session(7)["state"],"Engineer:MENU")

    async def test_edit_errors_and_stale_callback(self):
        await self.send(text="/start")
        count = len([c for c in self.transport.calls if isinstance(c,SendMessage)])
        self.transport.edit_error = "Bad Request: message is not modified"
        await self.send(action="menu")
        self.assertEqual(len([c for c in self.transport.calls if isinstance(c,SendMessage)]),count)
        self.transport.edit_error = "Bad Request: message to edit not found"
        await self.send(action="menu")
        self.assertEqual(len([c for c in self.transport.calls if isinstance(c,SendMessage)]),count+1)
        self.transport.edit_error = None
        await self.send(action="watch",message_id=999)
        self.assertNotIn("watch_track",self.store.load_session(7))
        self.assertEqual(sum(isinstance(c,AnswerCallbackQuery) for c in self.transport.calls),3)

    async def test_import_local_game_and_antiflood(self):
        path = Path(self.temp.name)/"export.json"
        path.write_text(export(),encoding="utf-8")
        await self.send(text="/start")
        with patch("py_bot.bot.RECORDS_PATH",path):
            await self.send(action="import")
        self.assertIn("Добавлено: 1",self.last_text())
        with patch("py_bot.bot.time",SimpleNamespace(monotonic=lambda:100)):
            await self.send(action="watch")
            await self.send(action="watch")
        self.assertIsNotNone(self.store.load_session(7).get("watch_track"))


class GameExportTests(unittest.TestCase):
    def test_grass_shortcuts_restarts_and_sector_sums(self):
        """Три заезда с пересечением обоих секторных ворот по траве."""
        os.environ["SDL_VIDEODRIVER"] = "dummy"
        os.environ["SDL_AUDIODRIVER"] = "dummy"
        import pygame
        from py_retro_cars.game import Game
        pygame.init()
        pygame.display.set_mode((800,600))
        try:
            with tempfile.TemporaryDirectory() as temp:
                path = Path(temp)/"records.json"
                game = Game(records_path=path)
                for race in range(3):
                    game.reset()
                    game.state = "PLAY"
                    def step(x,y,frames=10):
                        game.car.x,game.car.y = x,y
                        game.car.vx = 1
                        if game.timing_started:
                            game.lap_frames += frames
                            game.total_frames += frames
                        game._check_laps()
                    step(450,100)
                    self.assertTrue(game.timing_started)
                    for lap in range(3):
                        # Старый алгоритм терял замеры на траве или при срезке
                        # нижнего поворота до прежних ворот на y=480.
                        step(500,250);step(500,350)
                        self.assertTrue(game.track.is_grass(500,350))
                        step(500,460);step(300,460);step(300,350);step(300,250)
                        self.assertTrue(game.track.is_grass(300,250))
                        self.assertEqual(len(game.sector_crossings),2)
                        step(300,100);step(450,100)
                    self.assertEqual(game.state,"NAME")
                    self.assertIsNotNone(game.best_lap_sectors)
                    game.name_input = f"Заезд {race+1}"
                    game._save_result()
                rows,errors = analytics.parse_records(path.read_text(encoding="utf-8"),game.track_id)
                self.assertFalse(errors)
                self.assertEqual(len(rows),3)
                for record in rows:
                    self.assertEqual(len(record["sectors"]),3)
                    self.assertAlmostEqual(sum(record["sectors"]),record["best_lap"],delta=0.01)
                self.assertEqual(analytics.leaderboard(rows,"s1").count("Заезд"),3)
        finally:
            pygame.quit()

    def test_real_lap_sector_timing_and_export(self):
        os.environ["SDL_VIDEODRIVER"] = "dummy"
        os.environ["SDL_AUDIODRIVER"] = "dummy"
        import pygame
        from py_retro_cars.game import Game
        pygame.init()
        pygame.display.set_mode((800,600))
        try:
            with tempfile.TemporaryDirectory() as temp:
                path = Path(temp)/"records.json"
                game = Game(records_path=path)
                game.state = "PLAY"
                def position(point):
                    game.car.x,game.car.y = (point[0]+0.5)*40,(point[1]+0.5)*40
                    game.car.vx = 1
                    game._check_laps()
                route = game.sector_route
                position(route[0])
                self.assertTrue(game.timing_started)
                for _ in range(3):
                    for point in route[1:]+route[:1]:
                        game.lap_frames += 10
                        game.total_frames += 10
                        position(point)
                self.assertEqual(game.state,"NAME")
                self.assertEqual(len(game.best_lap_sectors),3)
                game.name_input = "Тест"
                game._save_result()
                rows,errors = analytics.parse_records(path.read_text(encoding="utf-8"),game.track_id)
                self.assertFalse(errors)
                self.assertEqual(len(rows),1)
                self.assertAlmostEqual(sum(rows[0]["sectors"]),rows[0]["best_lap"],delta=0.01)
        finally:
            pygame.quit()


if __name__ == "__main__":
    unittest.main()
