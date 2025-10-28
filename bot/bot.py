import os
import time
import requests
import telebot
from dotenv import load_dotenv
from telebot import types
import logging
from functools import wraps

logging.basicConfig(level=logging.INFO)
telebot.logger.setLevel(logging.INFO)
logger = logging.getLogger("SilkyBot")

load_dotenv()

TOKEN = os.getenv("TELEGRAM_TOKEN")
API_URL = os.getenv("API_URL")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD")

if not TOKEN or not API_URL or not ADMIN_PASSWORD:
    raise ValueError("❌ Missing environment variables! Please check .env file.")

bot = telebot.TeleBot(TOKEN)
authorized_users = set()
user_state = {}
recently_viewed = {}

def main_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("/list", "/get")
    markup.row("/add", "/update", "/delete")
    markup.row("/search", "/lowstock")
    markup.row("/recent", "/login", "/home")
    return markup

@bot.message_handler(commands=['start', 'home'])
def start(message):
    text = (
        "👋 <b>Welcome to SilkyWay Product Bot!</b>\n\n"
        "Here’s what I can do:\n"
        "📄 <b>/list</b> — Show all products\n"
        "🔍 <b>/get</b> — Get product by ID\n"
        "➕ <b>/add</b> — Add a product (admin only)\n"
        "✏️ <b>/update</b> — Update a product (admin only)\n"
        "🗑 <b>/delete</b> — Delete a product (admin only)\n"
        "🔎 <b>/search</b> — Search products by name\n"
        "📦 <b>/lowstock</b> — Products with low stock\n"
        "🕘 <b>/recent</b> — Recently viewed products\n"
        "🔑 <b>/login</b> — Admin login"
    )
    bot.send_message(message.chat.id, text, parse_mode="HTML", reply_markup=main_menu())
    user_state.pop(message.chat.id, None)

@bot.message_handler(commands=['login'])
def login_step1(message):
    bot.send_message(message.chat.id, "🔑 Enter the admin password:")
    user_state[message.chat.id] = "waiting_for_login"

@bot.message_handler(func=lambda m: user_state.get(m.chat.id) == "waiting_for_login")
def login_step2(message):
    if message.text.strip() == ADMIN_PASSWORD:
        authorized_users.add(message.chat.id)
        bot.send_message(message.chat.id, "✅ Login successful! Admin features unlocked.", reply_markup=main_menu())
    else:
        bot.send_message(message.chat.id, "❌ Incorrect password. Try again.", reply_markup=main_menu())
    user_state.pop(message.chat.id, None)

def check_admin(func):
    @wraps(func)
    def wrapper(message):
        if message.chat.id not in authorized_users:
            bot.send_message(message.chat.id, "⚠️ Please login as admin first using /login.", reply_markup=main_menu())
            return
        return func(message)
    return wrapper

@bot.message_handler(commands=['list'])
def list_products(message):
    try:
        response = requests.get(f"{API_URL}/products", timeout=10)
        response.raise_for_status()
        products = response.json()
        if products:
            text = "🛒 <b>Product List:</b>\n\n" + "\n".join(
                [f"🔹 <b>{p['id']}</b>. {p['name']} — ${p['price']}" for p in products]
            )
        else:
            text = "📭 No products found in the database."
        bot.send_message(message.chat.id, text, parse_mode="HTML", reply_markup=main_menu())
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ Error: {str(e)}", reply_markup=main_menu())

@bot.message_handler(commands=['get'])
def get_product_step1(message):
    bot.send_message(message.chat.id, "🔍 Enter the Product ID:")
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
                f"📝 {p['description']}\n"
                f"💰 Price: ${p['price']}\n"
                f"📦 Stock: {p['stock']}"
            )

            if message.chat.id not in recently_viewed:
                recently_viewed[message.chat.id] = []
            recently_viewed[message.chat.id].insert(0, p)
            recently_viewed[message.chat.id] = recently_viewed[message.chat.id][:5]
        elif response.status_code == 404:
            text = f"❌ Product with ID {product_id} not found."
        else:
            text = f"⚠️ Server error: {response.status_code}"
        bot.send_message(message.chat.id, text, parse_mode="HTML", reply_markup=main_menu())
    except ValueError:
        bot.send_message(message.chat.id, "❌ Please enter a valid numeric ID.")
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ Error: {str(e)}")
    finally:
        user_state.pop(message.chat.id, None)

@bot.message_handler(commands=['recent'])
def show_recent(message):
    products = recently_viewed.get(message.chat.id, [])
    if not products:
        bot.send_message(message.chat.id, "📭 You haven't viewed any products yet.", reply_markup=main_menu())
        return
    text = "🕘 <b>Recently Viewed Products:</b>\n\n" + "\n".join(
        [f"🔹 <b>{p['id']}</b>. {p['name']} — ${p['price']}" for p in products]
    )
    bot.send_message(message.chat.id, text, parse_mode="HTML", reply_markup=main_menu())

@bot.message_handler(commands=['add'])
@check_admin
def add_product_step1(message):
    bot.send_message(message.chat.id,
                     "➕ Enter new product data (comma separated):\n"
                     "<b>Name, Description, Price, Stock</b>\n\n"
                     "Example:\n<b>Mouse, Wireless gaming mouse, 39.99, 20</b>",
                     parse_mode="HTML")
    user_state[message.chat.id] = "waiting_for_add"

@bot.message_handler(func=lambda m: user_state.get(m.chat.id) == "waiting_for_add")
def add_product_step2(message):
    try:
        parts = [p.strip() for p in message.text.split(",")]
        if len(parts) != 4:
            raise ValueError("❌ Wrong format! Use: Name, Description, Price, Stock")
        name, desc, price, stock = parts
        response = requests.post(f"{API_URL}/products", json={
            "name": name,
            "description": desc,
            "price": float(price),
            "stock": int(stock)
        }, timeout=10)
        if response.status_code in (200, 201):
            bot.send_message(message.chat.id, "✅ Product added successfully!", reply_markup=main_menu())
        else:
            bot.send_message(message.chat.id, f"❌ Error: {response.text}", reply_markup=main_menu())
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ {str(e)}", reply_markup=main_menu())
    finally:
        user_state.pop(message.chat.id, None)


@bot.message_handler(commands=['update'])
@check_admin
def update_product_step1(message):
    bot.send_message(
        message.chat.id,
        "✏️ Enter updated product data:\n"
        "<b>ID, field=value, field=value...</b>\n\n"
        "Examples:\n"
        "<b>1, price=79.99</b>\n"
        "<b>1, name=Keyboard, stock=10</b>",
        parse_mode="HTML"
    )
    user_state[message.chat.id] = "waiting_for_update"


@bot.message_handler(func=lambda m: user_state.get(m.chat.id) == "waiting_for_update")
def update_product_step2(message):
    try:
        parts = [p.strip() for p in message.text.split(",")]
        if len(parts) < 2:
            raise ValueError("❌ Wrong format! Use: ID, field=value, field=value...")

        pid = int(parts[0])
        updates = {}

        for p in parts[1:]:
            if "=" not in p:
                raise ValueError(f"❌ Invalid field format: {p}")
            key, val = p.split("=", 1)
            key, val = key.strip(), val.strip()

            if key in ["price"]:
                val = float(val)
            elif key in ["stock"]:
                val = int(val)
            updates[key] = val

        response = requests.put(f"{API_URL}/products/{pid}", json=updates, timeout=10)

        if response.status_code == 200:
            msg = "✅ Product updated successfully!"
        elif response.status_code == 404:
            msg = f"❌ Product ID {pid} not found."
        else:
            msg = f"❌ Error: {response.text}"

        bot.send_message(message.chat.id, msg, reply_markup=main_menu())

    except Exception as e:
        bot.send_message(message.chat.id, f"⚠️ Error: {str(e)}", reply_markup=main_menu())
    finally:
        user_state.pop(message.chat.id, None)

@bot.message_handler(commands=['delete'])
@check_admin
def delete_product_step1(message):
    bot.send_message(message.chat.id, "🗑 Enter the ID of the product to delete:")
    user_state[message.chat.id] = "waiting_for_delete"

@bot.message_handler(func=lambda m: user_state.get(m.chat.id) == "waiting_for_delete")
def delete_product_step2(message):
    try:
        pid = int(message.text)
        response = requests.delete(f"{API_URL}/products/{pid}", timeout=10)
        if response.status_code == 200:
            bot.send_message(message.chat.id, "✅ Product deleted successfully!", reply_markup=main_menu())
        elif response.status_code == 404:
            bot.send_message(message.chat.id, f"❌ Product ID {pid} not found.", reply_markup=main_menu())
        else:
            bot.send_message(message.chat.id, f"❌ Error: {response.text}", reply_markup=main_menu())
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ {str(e)}", reply_markup=main_menu())
    finally:
        user_state.pop(message.chat.id, None)


@bot.message_handler(commands=['search'])
def search_step1(message):
    bot.send_message(message.chat.id, "🔎 Enter keyword to search products:")
    user_state[message.chat.id] = "waiting_for_search"

@bot.message_handler(func=lambda m: user_state.get(m.chat.id) == "waiting_for_search")
def search_step2(message):
    try:
        keyword = message.text.strip()
        response = requests.get(f"{API_URL}/search/{keyword}", timeout=10)
        response.raise_for_status()
        products = response.json()
        if products:
            text = "🔎 <b>Search results:</b>\n\n" + "\n".join(
                [f"🔹 <b>{p['id']}</b>. {p['name']} — ${p['price']}" for p in products]
            )
        else:
            text = "📭 No products found for your keyword."
        bot.send_message(message.chat.id, text, parse_mode="HTML", reply_markup=main_menu())
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ Error: {str(e)}", reply_markup=main_menu())
    finally:
        user_state.pop(message.chat.id, None)


@bot.message_handler(commands=['lowstock'])
def lowstock_step(message):
    try:
        response = requests.get(f"{API_URL}/lowstock", timeout=10)
        response.raise_for_status()
        products = response.json()
        if products:
            text = "📦 <b>Low stock products:</b>\n\n" + "\n".join(
                [f"🔹 <b>{p['id']}</b>. {p['name']} — Stock: {p['stock']}" for p in products]
            )
        else:
            text = "✅ All products have sufficient stock."
        bot.send_message(message.chat.id, text, parse_mode="HTML", reply_markup=main_menu())
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ Error: {str(e)}", reply_markup=main_menu())


if __name__ == "__main__":
    for i in range(10):
        try:
            print(f"🔄 Checking FastAPI connection (attempt {i+1})...")
            r = requests.get(f"{API_URL}/products", timeout=5)
            if r.status_code == 200:
                print("✅ FastAPI is ready! Starting bot...")
                break
        except Exception:
            print("⚠ Waiting for FastAPI to be ready...")
            time.sleep(3)
    else:
        print("❌ Could not connect to FastAPI after 10 attempts.")
        exit(1)

    print("🤖 Bot started successfully!")
    bot.polling(non_stop=True, interval=0, long_polling_timeout=60)
