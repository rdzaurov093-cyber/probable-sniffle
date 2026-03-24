import asyncio
import aiohttp
import sqlite3
import json
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command

# --- НАСТРОЙКИ ---
TELEGRAM_TOKEN = "8615927540:AAHFZrbvBnXPbZGBeiUjBkeeKMfTlEl0RZU"
OPENROUTER_API_KEY = "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"

bot = Bot(token=TELEGRAM_TOKEN)
dp = Dispatcher()

# --- РАБОТА С БАЗОЙ ДАННЫХ ---
def init_db():
    conn = sqlite3.connect('anya_memory.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS history 
        (user_id INTEGER, role TEXT, content TEXT)
    ''')
    conn.commit()
    conn.close()

def save_message(user_id, role, content):
    conn = sqlite3.connect('anya_memory.db')
    cursor = conn.cursor()
    cursor.execute('INSERT INTO history (user_id, role, content) VALUES (?, ?, ?)', (user_id, role, content))
    conn.commit()
    conn.close()

def get_history(user_id, limit=10):
    conn = sqlite3.connect('anya_memory.db')
    cursor = conn.cursor()
    # Берем последние сообщения
    cursor.execute('SELECT role, content FROM history WHERE user_id = ? ORDER BY rowid DESC LIMIT ?', (user_id, limit))
    rows = cursor.fetchall()
    conn.close()
    # Возвращаем в правильном порядке (от старых к новым)
    return [{"role": r, "content": c} for r, c in reversed(rows)]

# --- ЛОГИКА ИИ ---
async def get_anya_response(user_id, user_text):
    url = "https://openrouter.ai/api/v1/chat/completions"
    
    # 1. Сохраняем сообщение пользователя в память
    save_message(user_id, "user", user_text)
    
    # 2. Достаем историю
    history = get_history(user_id)
    
    system_prompt = (
        "Ты — Аня Форджер из аниме 'Семья шпиона'. Ты маленькая девочка-телепат. "
        "Обожаешь арахис, называешь пользователя 'Чичи'. Используй 'Waku Waku!'. "
        "Помни о прошлых темах разговора, которые тебе переданы в истории."
    )
    
    # Формируем список сообщений для ИИ (Промпт + История)
    messages = [{"role": "system", "content": system_prompt}] + history
    
    payload = {
        "model": "google/gemini-2.0-flash-exp:free",
        "messages": messages,
        "temperature": 0.8
    }
    
    headers = {"Authorization": f"Bearer {OPENROUTER_API_KEY}", "Content-Type": "application/json"}

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json=payload, timeout=25) as response:
                if response.status == 200:
                    data = await response.json()
                    answer = data['choices'][0]['message']['content']
                    # 3. Сохраняем ответ Ани в память
                    save_message(user_id, "assistant", answer)
                    return answer
                return "Аня что-то забыла... (Ошибка API)"
    except Exception:
        return "Миссия провалена! (Проблема с сетью)"

# --- ХЕНДЛЕРЫ ---
@dp.message(Command("start"))
async def start_cmd(message: types.Message):
    await message.answer("Waku Waku! Аня всё помнит! 🥜\nЧичи, я готова к новой миссии!")

@dp.message()
async def handle_message(message: types.Message):
    if not message.text: return
    await bot.send_chat_action(message.chat.id, "typing")
    response = await get_anya_response(message.from_user.id, message.text)
    await message.answer(response)

async def main():
    init_db() # Создаем базу при запуске
    print("--- Аня с памятью запущена! ---")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
