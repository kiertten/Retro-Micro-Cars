"""ЛР 3, вариант 21: сервис аналитики Pygame-игры."""
import asyncio
from html import escape
import io
import json
import logging
from logging.handlers import RotatingFileHandler
import os
from pathlib import Path
import sys
import time
if __package__ in {None, ""}:
    sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
from aiogram import Bot, Dispatcher, F, Router
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError, TelegramRetryAfter
from aiogram.filters import Command, CommandStart, StateFilter
from aiogram.filters.command import CommandObject
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import SimpleEventIsolation
from aiogram.types import BotCommand, CallbackQuery, ErrorEvent, Message
from dotenv import load_dotenv
from py_bot import analytics, keyboards
from py_bot.config import BASE_DIR, DATA_DIR, TRACK_PATH, RECORDS_PATH
from py_bot.session import Store, atomic_json
from py_bot.storage import JsonStorage

logger = logging.getLogger(__name__)
HELP = ("<b>Гоночный инженер — аналитика игры</b>\n"
        "/top — рейтинг по кругу; /top s1, /top s2, /top s3 — по секторам.\n"
        "/upload — отправить track.txt или records.json документом.\n"
        "/stats — статистика пилотов; /stats Имя — точное имя.\n"
        "/watch — включить или выключить уведомления о новых рекордах текущей трассы.\n"
        "/start — меню; /help — справка.\n\n"
        "Сначала загрузите трек, затем JSON рекордов из игры. По умолчанию используется трек проекта. "
        "Кнопка импорта читает выгрузку игры на компьютере, где запущен бот. "
        "Результаты разных трасс учитываются отдельно. Новые рекорды определяются при загрузке или импорте JSON. "
        "Игра и симуляция внутри Telegram не запускаются.")

class Engineer(StatesGroup):
    MENU = State()
    UPLOAD = State()
    RESULT = State()

async def show_screen(bot, store, user_id, chat_id, text, markup):
    session = store.load_session(user_id)
    message_id = session.get("screen_message_id")
    if message_id and session.get("screen_chat_id") == chat_id:
        try:
            await bot.edit_message_text(text=text, chat_id=chat_id,
                                        message_id=message_id, reply_markup=markup)
            return
        except TelegramBadRequest as error:
            description = str(error).lower()
            if "message is not modified" in description:
                return
            if not any(part in description for part in ("message to edit not found", "message can't be edited")):
                raise
            logger.info("Экран %s удалён или недоступен", message_id)
    message = await bot.send_message(chat_id, text, reply_markup=markup)
    # Снова читаем, чтобы не затереть обновлённое состояние FSM.
    session = store.load_session(user_id)
    session.update(screen_message_id=message.message_id, screen_chat_id=chat_id)
    store.save_session(user_id,session)




def create_dispatcher(store=None):
    store = store or Store()
    dp = Dispatcher(storage=JsonStorage(store),events_isolation=SimpleEventIsolation())
    router = Router()
    dp.include_router(router)
    router.message.filter(F.chat.type == "private")
    router.callback_query.filter(F.message.chat.type == "private")
    database_lock = asyncio.Lock()
    last_click = {}

    async def screen(bot, user_id, chat_id, text, markup=None):
        await show_screen(bot,store,user_id,chat_id,text,markup or keyboards.menu())

    def active_track(user_id):
        session = store.load_session(user_id)
        track_id = session.get("track_id")
        if not isinstance(track_id,str) or len(track_id)!=64 or any(c not in "0123456789abcdef" for c in track_id):
            track = analytics.parse_track(TRACK_PATH.read_text(encoding="utf-8-sig"))
            track_id = track["id"]
            atomic_json(store.root/"tracks"/(track_id+".json"),track)
            session["track_id"] = track_id
            store.save_session(user_id,session)
        return track_id

    async def notify(bot, track_id, improved):
        if not improved:
            return
        sessions = store.root/"sessions"
        for path in sessions.glob("*.json") if sessions.exists() else []:
            if not path.stem.isdigit():
                continue
            user_id = int(path.stem)
            session = store.load_session(user_id)
            if session.get("watch_track") != track_id:
                continue
            chat_id = session.get("screen_chat_id")
            if not chat_id:
                continue
            try:
                text = f"Новый рекорд трассы {track_id[:8]}: {', '.join(improved)}. Откройте /top."
                try:
                    await bot.send_message(chat_id,text)
                except TelegramRetryAfter as error:
                    # Большую паузу не удерживаем внутри пользовательского запроса.
                    if error.retry_after > 5:
                        logger.warning("Уведомление отложено Telegram для user=%s",user_id)
                        continue
                    await asyncio.sleep(error.retry_after)
                    await bot.send_message(chat_id,text)
                await asyncio.sleep(0.05)
            except TelegramForbiddenError:
                session = store.load_session(user_id)
                session.pop("watch_track",None)
                store.save_session(user_id,session)
            except Exception:
                logger.exception("Не доставлено уведомление user=%s",user_id)

    async def import_json(bot, user_id, text):
        track_id = active_track(user_id)
        valid,errors = analytics.parse_records(text,track_id)
        async with database_lock:
            added,duplicates,improved = analytics.merge_records(store.root,track_id,valid)
        await notify(bot,track_id,improved)
        logger.info("Импорт user=%s track=%s added=%s duplicates=%s rejected=%s",user_id,track_id[:8],added,duplicates,len(errors))
        report = f"Добавлено: {added}; дубликатов: {duplicates}; отклонено: {len(errors)}.\nТрасса: {track_id[:8]}"
        if errors:
            report += "\n"+escape("\n".join(errors[:5]))
        if any(r["sectors"] is None for r in valid):
            report += "\nЕсть старые записи без секторов: они участвуют только в рейтинге круга."
        if any(r["sectors"] and r.get("sector_version")!=analytics.SECTOR_VERSION for r in valid):
            report += "\nСтарые границы секторов: эти записи участвуют только в рейтинге круга. Для S1–S3 проедьте заезд в обновлённой игре."
        return report

    async def perform(action, bot, user_id, chat_id, state, argument=None):
        try:
            if action == "upload":
                await state.set_state(Engineer.UPLOAD)
                await screen(bot,user_id,chat_id,"Отправьте track.txt (15×20, # . F) или records.json документом, до 1 МБ.\n"
                             "Трек выбирается только для вашей сессии; JSON добавляется в общий рейтинг этой трассы.\n"
                             "Для старого JSON без track_id сначала выберите соответствующий трек.")
            elif action.startswith("top:"):
                metric = action.split(":",1)[1]
                track_id = active_track(user_id)
                text = analytics.leaderboard(analytics.load_records(store.root,track_id),metric)
                await state.set_state(Engineer.RESULT)
                await screen(bot,user_id,chat_id,text+f"\nТрасса: {track_id[:8]}",keyboards.top())
            elif action == "stats":
                track_id = active_track(user_id)
                text = analytics.statistics(analytics.load_records(store.root,track_id),argument)
                await state.set_state(Engineer.RESULT)
                await screen(bot,user_id,chat_id,text+f"\nТрасса: {track_id[:8]}")
            elif action == "watch":
                track_id = active_track(user_id)
                session = store.load_session(user_id)
                enabled = session.get("watch_track") != track_id
                if enabled:
                    session["watch_track"] = track_id
                else:
                    session.pop("watch_track",None)
                store.save_session(user_id,session)
                await state.set_state(Engineer.MENU)
                await screen(bot,user_id,chat_id,f"Уведомления {'включены' if enabled else 'выключены'} для трассы {track_id[:8]}.\n"
                             "Событие: улучшение общего рекорда круга или сектора при импорте JSON.")
            elif action == "import":
                if RECORDS_PATH.stat().st_size > analytics.MAX_FILE_SIZE:
                    raise ValueError("Файл рекордов больше 1 МБ.")
                report = await import_json(bot,user_id,RECORDS_PATH.read_text(encoding="utf-8-sig"))
                await state.set_state(Engineer.RESULT)
                await screen(bot,user_id,chat_id,report)
            elif action == "help":
                await state.set_state(Engineer.MENU)
                await screen(bot,user_id,chat_id,HELP)
            elif action == "menu":
                await state.set_state(Engineer.MENU)
                await screen(bot,user_id,chat_id,"<b>Гоночный инженер</b>\nАналитика выгрузок Pygame-игры.\n"+HELP)
            else:
                await screen(bot,user_id,chat_id,"Неизвестная кнопка. Используйте /start.")
        except (ValueError,OSError,UnicodeError) as error:
            logger.warning("Действие %s user=%s: %s",action,user_id,error)
            await screen(bot,user_id,chat_id,"Ошибка данных: "+escape(str(error)[:500]))

    @router.message(CommandStart())
    async def start(message: Message, state: FSMContext, bot: Bot):
        await perform("menu",bot,message.from_user.id,message.chat.id,state)

    @router.message(Command("top","stats","upload","watch","help"))
    async def command_handler(message: Message, state: FSMContext, bot: Bot, command: CommandObject):
        action = command.command.lower()
        if action == "top":
            metric = (command.args or "lap").strip().lower()
            if metric not in ("lap","s1","s2","s3"):
                await screen(bot,message.from_user.id,message.chat.id,"Используйте /top, /top s1, /top s2 или /top s3.")
                return
            action = "top:"+metric
        await perform(action,bot,message.from_user.id,message.chat.id,state,command.args)

    @router.callback_query()
    async def clicked(callback: CallbackQuery, state: FSMContext, bot: Bot):
        await callback.answer()
        user_id,chat_id = callback.from_user.id,callback.message.chat.id
        session = store.load_session(user_id)
        if callback.message.message_id != session.get("screen_message_id"):
            await screen(bot,user_id,chat_id,"Этот экран устарел. Используйте меню ниже.")
            return
        now = time.monotonic()
        if now-last_click.get(user_id,0)<0.4:
            return
        last_click[user_id] = now
        if len(last_click)>1000:
            for uid in [uid for uid,t in last_click.items() if now-t>60]:
                last_click.pop(uid,None)
        await perform(callback.data or "",bot,user_id,chat_id,state)

    @router.message(StateFilter(Engineer.UPLOAD), F.document)
    async def upload(message: Message, state: FSMContext, bot: Bot):
        document = message.document
        name = (document.file_name or "").lower()
        allowed = {".txt":{"text/plain","application/octet-stream"},
                   ".json":{"application/json","text/plain","application/octet-stream"}}
        suffix = Path(name).suffix
        if suffix not in allowed or document.mime_type not in allowed[suffix]:
            await screen(bot,message.from_user.id,message.chat.id,"Нужен документ .txt или .json с текстовым MIME-типом.")
            return
        if document.file_size is None or not 0 < document.file_size <= analytics.MAX_FILE_SIZE:
            await screen(bot,message.from_user.id,message.chat.id,"Размер файла должен быть от 1 байта до 1 МБ.")
            return
        class LimitedBuffer(io.BytesIO):
            def write(self, data):
                if self.tell()+len(data)>analytics.MAX_FILE_SIZE:
                    raise ValueError("Файл больше 1 МБ.")
                return super().write(data)
        try:
            buffer = LimitedBuffer()
            await bot.download(document,destination=buffer)
            text = buffer.getvalue().decode("utf-8-sig")
            user_id = message.from_user.id
            if suffix == ".txt":
                track = analytics.parse_track(text)
                atomic_json(store.root/"tracks"/(track["id"]+".json"),track)
                session = store.load_session(user_id)
                changed = session.get("track_id") != track["id"]
                session["track_id"] = track["id"]
                if changed:
                    session.pop("watch_track",None)
                store.save_session(user_id,session)
                report = f"Трек принят: 15×20; дорожных клеток {track['road_cells']}; F: {track['finish_cells']}.\nТрасса: {track['id'][:8]}"
                if changed:
                    report += "\nДля нового трека включите уведомления через /watch."
            else:
                report = await import_json(bot,user_id,text)
            await screen(bot,user_id,message.chat.id,report+"\nМожно отправить следующий файл или открыть /top.")
        except (ValueError,OSError,UnicodeError) as error:
            logger.warning("Отклонён файл user=%s: %s",message.from_user.id,error)
            await screen(bot,message.from_user.id,message.chat.id,"Файл не принят: "+escape(str(error)[:500]))

    @router.message()
    async def fallback(message: Message, state: FSMContext, bot: Bot):
        if await state.get_state() == Engineer.UPLOAD.state:
            await screen(bot,message.from_user.id,message.chat.id,"Отправьте файл документом или выберите /start.")
        else:
            await screen(bot,message.from_user.id,message.chat.id,"Используйте /upload для загрузки файла или /start для меню.")

    @dp.errors()
    async def on_error(event: ErrorEvent, bot: Bot):
        logger.error("Ошибка обработки события",exc_info=(type(event.exception),event.exception,event.exception.__traceback__))
        message = event.update.message or (event.update.callback_query.message if event.update.callback_query else None)
        if message:
            try:
                await bot.send_message(message.chat.id,"Временный сбой. Попробуйте /start.")
            except Exception:
                logger.exception("Не удалось сообщить об ошибке")
        return True
    return dp

async def main():
    load_dotenv(BASE_DIR/".env")
    token = os.getenv("BOT_TOKEN","").strip()
    if not token or token == "PASTE_TOKEN_HERE":
        raise SystemExit("Заполните BOT_TOKEN в py_bot/.env (образец: .env.example).")
    DATA_DIR.mkdir(parents=True,exist_ok=True)
    logging.basicConfig(level=logging.INFO,format="%(asctime)s | %(levelname)s | %(message)s",
                        handlers=[RotatingFileHandler(DATA_DIR/"bot_flight.log",maxBytes=1_000_000,
                                                      backupCount=2,encoding="utf-8"),logging.StreamHandler()])
    bot = Bot(token,default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    try:
        await bot.set_my_commands([BotCommand(command=c,description=d) for c,d in [
            ("start","Главное меню"),("top","Рейтинг круга и секторов"),("upload","Загрузить трек или рекорды"),
            ("stats","Статистика пилотов"),("watch","Уведомления о рекордах"),("help","Справка")]])
        logger.info("Бот запущен")
        await create_dispatcher().start_polling(bot)
    finally:
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
