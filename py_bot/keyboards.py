"""Инлайн-клавиатуры сервиса аналитики."""
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

def keyboard(rows):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=text,callback_data=data) for text,data in row] for row in rows])

def menu():
    return keyboard([[("Рейтинг", "top:lap"),("Статистика", "stats")],
                     [("Загрузить файл", "upload"),("Уведомления", "watch")],
                     [("Импорт из игры на этом ПК", "import")],[("Справка", "help")]])

def top():
    return keyboard([[("Круг", "top:lap"),("S1", "top:s1"),("S2", "top:s2"),("S3", "top:s3")],
                     [("В меню", "menu")]])
