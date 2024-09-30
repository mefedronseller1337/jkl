import sqlite3
from aiogram import Bot, Dispatcher, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils import executor
from aiogram.dispatcher.filters import Text
import os

# Токен вашего бота
API_TOKEN = '8007023701:AAGCd6yqWYOy4va7DkYQegb5iFy9v6FVQdI'

# Инициализация бота и диспетчера
bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)

# Подключение к базе данных
conn = sqlite3.connect('dating.db')
cursor = conn.cursor()

# Создание таблиц
cursor.execute('''CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY,
                    name TEXT,
                    age INTEGER,
                    gender TEXT,
                    preference TEXT,
                    bio TEXT,
                    photos TEXT)''')

cursor.execute('''CREATE TABLE IF NOT EXISTS likes (
                    liker_id INTEGER,
                    liked_id INTEGER,
                    status TEXT)''')
conn.commit()

# Хэндлер для команды /start
@dp.message_handler(commands=['start'])
async def start_command(message: types.Message):
    user_id = message.from_user.id
    cursor.execute("SELECT id FROM users WHERE id=?", (user_id,))
    user = cursor.fetchone()

    if user:
        await message.reply("Ты уже зарегистрирован! Давай посмотрим анкеты.")
    else:
        await message.reply("Привет! Давай начнем с твоей анкеты. Сколько тебе лет?")
        await bot.send_message(user_id, "Укажи свой возраст:")

@dp.message_handler(lambda message: message.text.isdigit())
async def set_age(message: types.Message):
    age = int(message.text)
    user_id = message.from_user.id

    cursor.execute("INSERT OR IGNORE INTO users (id, age) VALUES (?, ?)", (user_id, age))
    conn.commit()

    await message.reply("Отлично! Теперь укажи свой пол (М/Ж):")

@dp.message_handler(lambda message: message.text.lower() in ['м', 'ж'])
async def set_gender(message: types.Message):
    gender = message.text.lower()
    user_id = message.from_user.id

    cursor.execute("UPDATE users SET gender=? WHERE id=?", (gender, user_id))
    conn.commit()

    await message.reply("Какой пол ты хочешь найти? (М/Ж):")

@dp.message_handler(lambda message: message.text.lower() in ['м', 'ж'])
async def set_preference(message: types.Message):
    preference = message.text.lower()
    user_id = message.from_user.id

    cursor.execute("UPDATE users SET preference=? WHERE id=?", (preference, user_id))
    conn.commit()

    await message.reply("Теперь расскажи немного о себе:")

@dp.message_handler(lambda message: len(message.text) > 0)
async def set_bio(message: types.Message):
    bio = message.text
    user_id = message.from_user.id

    cursor.execute("UPDATE users SET bio=? WHERE id=?", (bio, user_id))
    conn.commit()

    await message.reply("Ты можешь прикрепить до 3 фотографий. Просто отправь их сюда:")

@dp.message_handler(content_types=['photo'])
async def handle_photos(message: types.Message):
    user_id = message.from_user.id
    photos = message.photo[-1].file_id  # Получаем ID самой большой версии фото

    cursor.execute("SELECT photos FROM users WHERE id=?", (user_id,))
    existing_photos = cursor.fetchone()[0] or ""

    if len(existing_photos.split(",")) < 3:
        new_photos = existing_photos + "," + photos if existing_photos else photos
        cursor.execute("UPDATE users SET photos=? WHERE id=?", (new_photos, user_id))
        conn.commit()

        await message.reply("Фото добавлено!")
    else:
        await message.reply("Ты уже добавил 3 фотографии.")

# Команда для просмотра анкет
@dp.message_handler(commands=['search'])
async def search_profiles(message: types.Message):
    user_id = message.from_user.id
    cursor.execute("SELECT preference FROM users WHERE id=?", (user_id,))
    preference = cursor.fetchone()[0]

    cursor.execute("SELECT id, name, age, bio FROM users WHERE gender=? AND id!=?", (preference, user_id))
    profiles = cursor.fetchall()

    if profiles:
        for profile in profiles:
            buttons = InlineKeyboardMarkup(row_width=3)
            buttons.add(
                InlineKeyboardButton("❤", callback_data=f"like_{profile[0]}"),
                InlineKeyboardButton("👎", callback_data=f"dislike_{profile[0]}"),
                InlineKeyboardButton("💬", callback_data=f"message_{profile[0]}")
            )
            await bot.send_message(user_id, f"Имя: {profile[1]}\nВозраст: {profile[2]}\nО себе: {profile[3]}", reply_markup=buttons)
    else:
        await message.reply("Анкеты не найдены.")

# Обработка лайков/дизлайков
@dp.callback_query_handler(lambda call: call.data.startswith('like_') or call.data.startswith('dislike_'))
async def handle_like_dislike(call: types.CallbackQuery):
    action, liked_id = call.data.split('_')
    liker_id = call.from_user.id

    if action == "like":
        cursor.execute("INSERT INTO likes (liker_id, liked_id, status) VALUES (?, ?, 'like')", (liker_id, liked_id))
        conn.commit()
        await call.message.reply("Ты лайкнул(а) анкету!")
    elif action == "dislike":
        await call.message.reply("Ты дизлайкнул(а) анкету.")
    
    # Проверка взаимного лайка
    cursor.execute("SELECT * FROM likes WHERE liker_id=? AND liked_id=? AND status='like'", (liked_id, liker_id))
    mutual_like = cursor.fetchone()
    
    if mutual_like:
        cursor.execute("SELECT name FROM users WHERE id=?", (liked_id,))
        liked_user_name = cursor.fetchone()[0]
        await bot.send_message(liker_id, f"Взаимный лайк! Вот ссылка на {liked_user_name}: @{liked_user_name}")
        await bot.send_message(liked_id, f"{call.from_user.full_name} лайкнул(а) тебя! Вот его профиль: @{call.from_user.username}")

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
