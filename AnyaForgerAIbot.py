import asyncio
import aiohttp
import sqlite3
import random
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command

# --- НАСТРОЙКИ ---
TELEGRAM_TOKEN = "8615927540:AAHFZrbvBnXPbZGBeiUjBkeeKMfTlEl0RZU"
OPENROUTER_API_KEY = "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"

bot = Bot(token=TELEGRAM_TOKEN)
dp = Dispatcher()
DB_PATH = '/app/data/anya_bot.db' # Путь для сохранения данных на Bothost

# --- БАЗА ДАННЫХ ---
def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('CREATE TABLE IF NOT EXISTS history (user_id INTEGER, role TEXT, content TEXT)')
    cursor.execute('CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, peanuts INTEGER DEFAULT 0)')
    conn.commit()
    conn.close()

def db_query(query, params=(), fetch=False):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(query, params)
    data = cursor.fetchall() if fetch else None
    conn.commit()
    conn.close()
    return data

# --- ЛОГИКА ИИ ---
async def get_anya_ai_response(user_id, user_text):
    url = "https://openrouter.ai/api/v1/chat/completions"
    
    # Сохраняем сообщение пользователя
    db_query('INSERT INTO history (user_id, role, content) VALUES (?, ?, ?)', (user_id, "user", user_text))
    
    # Достаем историю (последние 10 сообщений)
    rows = db_query('SELECT role, content FROM history WHERE user_id = ? ORDER BY rowid DESC LIMIT 10', (user_id,), fetch=True)
    history = [{"role": r, "content": c} for r, c in reversed(rows)]
    
    # Достаем баланс арахиса
    res = db_query('SELECT peanuts FROM users WHERE user_id = ?', (user_id,), fetch=True)
    peanuts = res[0][0] if res else 0

    payload = {
        "model": "google/gemini-2.0-flash-exp:free", # БЕСПЛАТНАЯ МОДЕЛЬ
        "messages": [
            {
                "role": "system", 
                "content": f"Ты Аня Форджер. Маленькая телепатка. Обожаешь арахис. У пользователя сейчас {peanuts} 🥜. Обращайся к нему Чичи. Используй Waku Waku!"
            }
        ] + history
    }
    
    headers = {"Authorization": f"Bearer {OPENROUTER_API_KEY}", "Content-Type": "application/json"}

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json=payload, timeout=20) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    ans = data['choices'][0]['message']['content']
                    db_query('INSERT INTO history (user_id, role, content) VALUES (?, ?, ?)', (user_id, "assistant", ans))
                    return ans
                return "Аня хочет спать... (Ошибка API или лимитов)"
    except Exception as e:
        return f"Миссия провалена! Ошибка сети: {e}"

# --- КОМАНДЫ ---
@dp.message(Command("start"))
async def start(message: types.Message):
    await message.answer("Waku Waku! Аня прибыла на секретную базу! 🥜\n\nКоманды:\n/job — заработать арахис\n/reset — очистить мою память")

@dp.message(Command("job"))
async def job(message: types.Message):
    earn = random.randint(5, 30)
    db_query('INSERT OR IGNORE INTO users (user_id, peanuts) VALUES (?, 0)', (message.from_user.id,))
    db_query('UPDATE users SET peanuts = peanuts + ? WHERE user_id = ?', (earn, message.from_user.id))
    await message.answer(f"Аня помогла тебе и заработала {earn} 🥜!")

@dp.message(Command("reset"))
async def reset(message: types.Message):
    db_query('DELETE FROM history WHERE user_id = ?', (message.from_user.id,))
    await message.answer("Аня всё забыла! Начнем новую миссию?")

@dp.message()
async def chat(message: types.Message):
    if not message.text: return
    await bot.send_chat_action(message.chat.id, "typing")
    response = await get_anya_ai_response(message.from_user.id, message.text)
    await message.answer(response)

if __name__ == "__main__":
    init_db()
    asyncio.run(dp.start_polling(bot))
    
