import os
import time
import requests
import telebot
from dotenv import load_dotenv
from telebot import types
import logging

# Загрузка переменных окружения
load_dotenv()
TOKEN = os.getenv("TELEGRAM_TOKEN")
API_URL = os.getenv("API_URL")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD")

# Настройка логирования
telebot.logger.setLevel(logging.INFO)

bot = telebot.TeleBot(TOKEN)
authorized_users = set()

# ================= Commands =================

@bot.message_handler(commands=['start'])
def start(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("/list", "/get")
    markup.row("/add", "/update", "/delete")
    markup.row("/login")
    bot.send_message(
        message.chat.id,
        "Привет! Вот доступные команды:\n"
        "- /list : показать все товары\n"
        "- /get <id> : показать товар по id\n"
        "- /add : добавить товар (требует входа)\n"
        "- /update : обновить товар (требует входа)\n"
        "- /delete : удалить товар (требует входа)\n"
        "- /login <password> : войти как админ",
        reply_markup=markup
    )

@bot.message_handler(commands=['login'])
def login(message):
    try:
        password = message.text.split()[1]
        if password == ADMIN_PASSWORD:
            authorized_users.add(message.chat.id)
            bot.reply_to(message, "Успешный вход! Теперь можно использовать админ-функции.")
        else:
            bot.reply_to(message, "Неверный пароль!")
    except IndexError:
        bot.reply_to(message, "Используй: /login <password>")

@bot.message_handler(commands=['list'])
def list_products(message):
    try:
        response = requests.get(f"{API_URL}/products", timeout=10)
        products = response.json()
        text = "\n".join([f"{p['id']}. {p['name']} - ${p['price']}" for p in products])
        bot.reply_to(message, text or "Товары отсутствуют")
    except Exception as e:
        bot.reply_to(message, f"Ошибка: {str(e)}")

@bot.message_handler(commands=['get'])
def get_product(message):
    try:
        product_id = int(message.text.split()[1])
        response = requests.get(f"{API_URL}/products/{product_id}", timeout=10)
        if response.status_code == 200:
            p = response.json()
            bot.reply_to(message, f"{p['id']}. {p['name']} - {p['description']} - ${p['price']} - Stock: {p['stock']}")
        else:
            bot.reply_to(message, f"Ошибка: {response.json().get('detail')}")
    except Exception as e:
        bot.reply_to(message, f"Ошибка: {str(e)}")

# ================ Admin check decorator =================

def check_admin(func):
    def wrapper(message):
        if message.chat.id not in authorized_users:
            bot.reply_to(message, "Сначала войдите через /login <password> для использования админ-функций.")
            return
        func(message)
    return wrapper

# ================= Admin commands =================

@bot.message_handler(commands=['add'])
@check_admin
def add_product(message):
    try:
        parts = message.text.split(" ", 1)[1].split("|")
        name, description, price, stock = parts[0], parts[1], float(parts[2]), int(parts[3])
        response = requests.post(f"{API_URL}/products", params={
            "name": name,
            "description": description,
            "price": price,
            "stock": stock
        }, timeout=10)
        if response.status_code == 200:
            bot.reply_to(message, "Товар успешно добавлен!")
        else:
            bot.reply_to(message, f"Ошибка: {response.text}")
    except Exception as e:
        bot.reply_to(message, f"Ошибка: {str(e)}")

@bot.message_handler(commands=['update'])
@check_admin
def update_product(message):
    try:
        parts = message.text.split(" ", 1)[1].split("|")
        product_id = int(parts[0])
        name, description, price, stock = parts[1], parts[2], float(parts[3]), int(parts[4])
        response = requests.put(f"{API_URL}/products/{product_id}", params={
            "name": name,
            "description": description,
            "price": price,
            "stock": stock
        }, timeout=10)
        if response.status_code == 200:
            bot.reply_to(message, "Товар успешно обновлён!")
        else:
            bot.reply_to(message, f"Ошибка: {response.text}")
    except Exception as e:
        bot.reply_to(message, f"Ошибка: {str(e)}")

@bot.message_handler(commands=['delete'])
@check_admin
def delete_product(message):
    try:
        product_id = int(message.text.split()[1])
        response = requests.delete(f"{API_URL}/products/{product_id}", timeout=10)
        if response.status_code == 200:
            bot.reply_to(message, "Товар успешно удалён!")
        else:
            bot.reply_to(message, f"Ошибка: {response.text}")
    except Exception as e:
        bot.reply_to(message, f"Ошибка: {str(e)}")

# ================= Main =================

if __name__ == "__main__":
    # Ожидание FastAPI
    for _ in range(10):
        try:
            r = requests.get(f"{API_URL}/products", timeout=5)
            if r.status_code == 200:
                break
        except Exception:
            print("Waiting for FastAPI...")
            time.sleep(2)

    print("Bot started!")
    bot.polling(non_stop=True, interval=0, long_polling_timeout=60)
