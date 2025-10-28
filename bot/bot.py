import os
import time
import requests
import telebot
from dotenv import load_dotenv
from telebot import types
import logging
from functools import wraps

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
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

def safe_request(method, endpoint, **kwargs):

    url = f"{API_URL}{endpoint}"
    try:
        response = requests.request(method, url, timeout=5, **kwargs)
        response.raise_for_status()
        try:
            return response.json()
        except ValueError:
            return {"error": "Invalid JSON response"}
    except requests.exceptions.ConnectionError:
        return {"error": "Backend unavailable"}
    except requests.exceptions.Timeout:
        return {"error": "Request timed out"}
    except requests.exceptions.HTTPError as e:
        return {"error": f"HTTP error: {e.response.status_code}"}
    except Exception as e:
        logger.warning(f"Request failed [{method.upper()} {url}]: {e}")
        return {"error": str(e)}


def main_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("/list", "/get")
    markup.row("/add", "/update", "/delete")
    markup.row("/search", "/lowstock")
    markup.row("/recent", "/login", "/home")
    return markup

def send(message, text, parse_html=True):
    bot.send_message(
        message.chat.id,
        text,
        parse_mode="HTML" if parse_html else None,
        reply_markup=main_menu()
    )


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
    send(message, text)
    user_state.pop(message.chat.id, None)


@bot.message_handler(commands=['login'])
def login_step1(message):
    send(message, "🔑 Enter the admin password:", parse_html=False)
    user_state[message.chat.id] = "waiting_for_login"

@bot.message_handler(func=lambda m: user_state.get(m.chat.id) == "waiting_for_login")
def login_step2(message):
    if message.text.strip() == ADMIN_PASSWORD:
        authorized_users.add(message.chat.id)
        send(message, "✅ Login successful! Admin features unlocked.")
    else:
        send(message, "❌ Incorrect password. Try again.")
    user_state.pop(message.chat.id, None)


def check_admin(func):
    @wraps(func)
    def wrapper(message):
        if message.chat.id not in authorized_users:
            send(message, "⚠️ Please login as admin first using /login.")
            return
        return func(message)
    return wrapper


@bot.message_handler(commands=['list'])
def list_products(message):
    data = safe_request("get", "/products")

    if "error" in data:
        send(message, f"⚠️ {data['error']}")
        return

    if not isinstance(data, list) or not data:
        send(message, "📭 No products found in the database.")
        return

    text = "🛒 <b>Product List:</b>\n\n" + "\n".join(
        [
            f"🔹 <b>{p['id']}</b>. {p['name']}\n"
            f"📝 {p['description']}\n"
            f"💰 Price: ${p['price']}\n"
            f"📦 Stock: {p['stock']}\n"
            for p in data
        ]
    )
    send(message, text)


@bot.message_handler(commands=['get'])
def get_product_step1(message):
    send(message, "🔍 Enter the Product ID:", parse_html=False)
    user_state[message.chat.id] = "waiting_for_get_id"

@bot.message_handler(func=lambda m: user_state.get(m.chat.id) == "waiting_for_get_id")
def get_product_step2(message):
    try:
        product_id = int(message.text)
        data = safe_request("get", f"/products/{product_id}")

        if "error" in data:
            send(message, f"⚠️ {data['error']}")
            return

        if not data or "name" not in data:
            send(message, f"❌ Product with ID {product_id} not found.")
            return

        p = data
        text = (
            f"🛍 <b>{p['name']}</b>\n"
            f"📝 {p['description']}\n"
            f"💰 Price: ${p['price']}\n"
            f"📦 Stock: {p['stock']}"
        )

        recently_viewed.setdefault(message.chat.id, [])
        recently_viewed[message.chat.id].insert(0, p)
        recently_viewed[message.chat.id] = recently_viewed[message.chat.id][:5]

        send(message, text)
    except ValueError:
        send(message, "❌ Please enter a valid numeric ID.")
    finally:
        user_state.pop(message.chat.id, None)


@bot.message_handler(commands=['recent'])
def show_recent(message):
    products = recently_viewed.get(message.chat.id, [])
    if not products:
        send(message, "📭 You haven't viewed any products yet.")
        return

    text = "🕘 <b>Recently Viewed Products:</b>\n\n" + "\n".join(
        [f"🔹 <b>{p['id']}</b>. {p['name']} — ${p['price']}" for p in products]
    )
    send(message, text)


@bot.message_handler(commands=['add'])
@check_admin
def add_product_step1(message):
    send(message,
         "➕ Enter new product data (comma separated):\n"
         "<b>Name, Description, Price, Stock</b>\n\n"
         "Example:\n<b>Mouse, Wireless gaming mouse, 39.99, 20</b>")

    user_state[message.chat.id] = "waiting_for_add"

@bot.message_handler(func=lambda m: user_state.get(m.chat.id) == "waiting_for_add")
def add_product_step2(message):
    try:
        parts = [p.strip() for p in message.text.split(",")]
        if len(parts) != 4:
            raise ValueError("❌ Wrong format! Use: Name, Description, Price, Stock")

        name, desc, price, stock = parts
        data = safe_request("post", "/products", json={
            "name": name,
            "description": desc,
            "price": float(price),
            "stock": int(stock)
        })

        if "error" in data:
            send(message, f"⚠️ {data['error']}")
        else:
            send(message, "✅ Product added successfully!")
    except Exception as e:
        send(message, f"❌ {str(e)}")
    finally:
        user_state.pop(message.chat.id, None)


@bot.message_handler(commands=['update'])
@check_admin
def update_product_step1(message):
    send(message,
         "✏️ Enter updated product data:\n"
         "<b>ID, field=value, field=value...</b>\n\n"
         "Examples:\n"
         "<b>1, price=79.99</b>\n"
         "<b>1, name=Keyboard, stock=10</b>")
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
            if key == "price":
                val = float(val)
            elif key == "stock":
                val = int(val)
            updates[key] = val

        data = safe_request("put", f"/products/{pid}", json=updates)

        if "error" in data:
            msg = f"⚠️ {data['error']}"
        elif isinstance(data, dict) and ("id" in data or "message" in data):
            msg = "✅ Product updated successfully!"
        else:
            msg = f"❌ Product ID {pid} not found."

        send(message, msg)
    except Exception as e:
        send(message, f"⚠️ Error: {str(e)}")
    finally:
        user_state.pop(message.chat.id, None)


@bot.message_handler(commands=['delete'])
@check_admin
def delete_product_step1(message):
    send(message, "🗑 Enter the ID of the product to delete:", parse_html=False)
    user_state[message.chat.id] = "waiting_for_delete"

@bot.message_handler(func=lambda m: user_state.get(m.chat.id) == "waiting_for_delete")
def delete_product_step2(message):
    try:
        pid = int(message.text)
        data = safe_request("delete", f"/products/{pid}")

        if "error" in data:
            msg = f"⚠️ {data['error']}"
        elif not data or "message" in data:
            msg = "✅ Product deleted successfully!"
        else:
            msg = f"❌ Product ID {pid} not found."

        send(message, msg)
    except Exception as e:
        send(message, f"❌ {str(e)}")
    finally:
        user_state.pop(message.chat.id, None)


@bot.message_handler(commands=['search'])
def search_step1(message):
    send(message, "🔎 Enter keyword to search products:", parse_html=False)
    user_state[message.chat.id] = "waiting_for_search"

@bot.message_handler(func=lambda m: user_state.get(m.chat.id) == "waiting_for_search")
def search_step2(message):
    keyword = message.text.strip()
    data = safe_request("get", f"/search/{keyword}")

    if "error" in data:
        send(message, f"⚠️ {data['error']}")
    elif isinstance(data, list) and data:
        text = "🔎 <b>Search results:</b>\n\n" + "\n".join(
            [
                f"🔹 <b>{p['id']}</b>. {p['name']}\n"
                f"📝 {p['description']}\n"
                f"💰 Price: ${p['price']}\n"
                f"📦 Stock: {p['stock']}\n"
                for p in data
            ]
        )
        send(message, text)
    else:
        send(message, "📭 No products found for your keyword.")
    user_state.pop(message.chat.id, None)


@bot.message_handler(commands=['lowstock'])
def lowstock_step(message):
    data = safe_request("get", "/lowstock")

    if "error" in data:
        send(message, f"⚠️ {data['error']}")
    elif isinstance(data, list) and data:
        text = "📦 <b>Low stock products:</b>\n\n" + "\n".join(
            [f"🔹 <b>{p['id']}</b>. {p['name']} — Stock: {p['stock']}" for p in data]
        )
        send(message, text)
    else:
        send(message, "✅ All products have sufficient stock.")


if __name__ == "__main__":
    print("🤖 SilkyWay Bot started! Waiting for API if needed...")
    while True:
        try:
            bot.polling(non_stop=True, interval=0, long_polling_timeout=60)
        except Exception as e:
            logger.error(f"⚠️ Bot crashed with error: {e}")
            time.sleep(5)
