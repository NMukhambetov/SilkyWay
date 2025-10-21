import os
import time
import requests
import telebot
from dotenv import load_dotenv
from telebot import types
import logging

load_dotenv()
TOKEN = os.getenv("TELEGRAM_TOKEN")
API_URL = os.getenv("API_URL")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD")

telebot.logger.setLevel(logging.INFO)

bot = telebot.TeleBot(TOKEN)
authorized_users = set()
user_state = {}

def main_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("/list", "/get")
    markup.row("/add", "/update", "/delete")
    markup.row("/login", "/home")
    return markup

@bot.message_handler(commands=['start', 'home'])
def start(message):
    text = (
        "👋 Hello! I'm your product management bot.\n\n"
        "Here is what I can do:\n"
        "📄 /list : Show all products\n"
        "🔍 /get : Show product by ID (interactive)\n"
        "➕ /add : Add a new product (admin only)\n"
        "✏️ /update : Update a product (admin only)\n"
        "🗑 /delete : Delete a product (admin only)\n"
        "🔑 /login : Login as admin\n\n"
        "📌 Use the buttons below or type a command!"
    )
    bot.send_message(message.chat.id, text, reply_markup=main_menu())
    user_state.pop(message.chat.id, None)

@bot.message_handler(commands=['login'])
def login_step1(message):
    bot.send_message(message.chat.id, "🔑 Enter the admin password:")
    user_state[message.chat.id] = "waiting_for_login"

@bot.message_handler(func=lambda m: user_state.get(m.chat.id) == "waiting_for_login")
def login_step2(message):
    if message.text == ADMIN_PASSWORD:
        authorized_users.add(message.chat.id)
        bot.send_message(message.chat.id, "✅ Login successful! Admin functions unlocked.", reply_markup=main_menu())
    else:
        bot.send_message(message.chat.id, "❌ Incorrect password! Try again.", reply_markup=main_menu())
    user_state.pop(message.chat.id, None)

@bot.message_handler(commands=['list'])
def list_products(message):
    try:
        response = requests.get(f"{API_URL}/products", timeout=10)
        if response.status_code != 200:
            raise Exception(f"Server returned {response.status_code}")
        products = response.json()
        if products:
            text = "🛒 Product List:\n" + "\n".join([f"{p['id']}. {p['name']} - ${p['price']}" for p in products])
        else:
            text = "No products found."
        bot.send_message(message.chat.id, text, reply_markup=main_menu())
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ Error fetching products: {str(e)}\nTry /home and select '📄 List Products'", reply_markup=main_menu())

@bot.message_handler(commands=['get'])
def get_product_step1(message):
    bot.send_message(message.chat.id, "🔍 Enter the Product ID you want to see:")
    user_state[message.chat.id] = "waiting_for_get_id"

@bot.message_handler(func=lambda m: user_state.get(m.chat.id) == "waiting_for_get_id")
def get_product_step2(message):
    try:
        product_id = int(message.text)
        response = requests.get(f"{API_URL}/products/{product_id}", timeout=10)
        if response.status_code == 200:
            p = response.json()
            text = (
                f"🛍 <b>{p['name']}</b>\n"
                f"📝 Description: {p['description']}\n"
                f"💰 Price: ${p['price']}\n"
                f"📦 Stock: {p['stock']}"
            )
        elif response.status_code == 404:
            text = f"❌ Product with ID {product_id} not found. Check /list for valid IDs."
        else:
            text = f"❌ Error: {response.json().get('detail')}"
        bot.send_message(message.chat.id, text, reply_markup=main_menu(), parse_mode='HTML')
    except ValueError:
        bot.send_message(message.chat.id, "❌ Please enter a numeric Product ID!")
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ Error: {str(e)}")
    finally:
        user_state.pop(message.chat.id, None)

def check_admin(func):
    def wrapper(message):
        if message.chat.id not in authorized_users:
            bot.send_message(message.chat.id, "⚠ Please login as admin first using /login", reply_markup=main_menu())
            return
        func(message)
    return wrapper

@bot.message_handler(commands=['add'])
@check_admin
def add_product_step1(message):
    bot.send_message(
        message.chat.id,
        "➕ Enter product details separated by commas:\n"
        "Example:\n"
        "Product Name, Short Description, 99.99, 10"
    )
    user_state[message.chat.id] = "waiting_for_add"

@bot.message_handler(func=lambda m: user_state.get(m.chat.id) == "waiting_for_add")
def add_product_step2(message):
    try:
        parts = [p.strip() for p in message.text.split(",")]
        if len(parts) != 4:
            raise ValueError("Invalid format! Example: Product Name, Short Description, 99.99, 10")
        name, description, price, stock = parts[0], parts[1], float(parts[2]), int(parts[3])
        response = requests.post(f"{API_URL}/products", json={  # <- use json body
            "name": name,
            "description": description,
            "price": price,
            "stock": stock
        }, timeout=10)
        if response.status_code == 201 or response.status_code == 200:
            bot.send_message(message.chat.id, "✅ Product added successfully!", reply_markup=main_menu())
        else:
            bot.send_message(message.chat.id, f"❌ Error adding product: {response.text}\nCheck format!", reply_markup=main_menu())
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ {str(e)}", reply_markup=main_menu())
    finally:
        user_state.pop(message.chat.id, None)

@bot.message_handler(commands=['update'])
@check_admin
def update_product_step1(message):
    bot.send_message(
        message.chat.id,
        "✏️ Enter product update details separated by commas:\n"
        "Example:\n"
        "ID, Product Name, Short Description, 99.99, 10"
    )
    user_state[message.chat.id] = "waiting_for_update"

@bot.message_handler(func=lambda m: user_state.get(m.chat.id) == "waiting_for_update")
def update_product_step2(message):
    try:
        parts = [p.strip() for p in message.text.split(",")]
        if len(parts) != 5:
            raise ValueError("Invalid format! Example: ID, Product Name, Short Description, 99.99, 10")
        product_id = int(parts[0])
        name, description, price, stock = parts[1], parts[2], float(parts[3]), int(parts[4])
        response = requests.put(f"{API_URL}/products/{product_id}", json={
            "name": name,
            "description": description,
            "price": price,
            "stock": stock
        }, timeout=10)
        if response.status_code == 200:
            bot.send_message(message.chat.id, "✅ Product updated successfully!", reply_markup=main_menu())
        else:
            bot.send_message(message.chat.id, f"❌ Error updating product: {response.text}", reply_markup=main_menu())
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ {str(e)}", reply_markup=main_menu())
    finally:
        user_state.pop(message.chat.id, None)

@bot.message_handler(commands=['delete'])
@check_admin
def delete_product_step1(message):
    bot.send_message(message.chat.id, "🗑 Enter the Product ID you want to delete:")
    user_state[message.chat.id] = "waiting_for_delete"

@bot.message_handler(func=lambda m: user_state.get(m.chat.id) == "waiting_for_delete")
def delete_product_step2(message):
    try:
        product_id = int(message.text)
        response = requests.delete(f"{API_URL}/products/{product_id}", timeout=10)
        if response.status_code == 200:
            bot.send_message(message.chat.id, "✅ Product deleted successfully!", reply_markup=main_menu())
        elif response.status_code == 404:
            bot.send_message(message.chat.id, f"❌ Product with ID {product_id} not found.", reply_markup=main_menu())
        else:
            bot.send_message(message.chat.id, f"❌ Error deleting product: {response.text}", reply_markup=main_menu())
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ {str(e)}", reply_markup=main_menu())
    finally:
        user_state.pop(message.chat.id, None)

if __name__ == "__main__":
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
