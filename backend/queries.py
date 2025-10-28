from backend.db import get_connection

def get_all_products():
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM products ORDER BY id;")
            return cursor.fetchall()
    finally:
        conn.close()

def get_product_by_id(product_id):
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM products WHERE id=%s;", (product_id,))
            return cursor.fetchone()
    finally:
        conn.close()

def add_product(name, description, price, stock):
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                "INSERT INTO products (name, description, price, stock) VALUES (%s, %s, %s, %s);",
                (name, description, price, stock)
            )
            conn.commit()
            return cursor.lastrowid
    finally:
        conn.close()

def update_product(product_id, data):
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            allowed_fields = ["name", "description", "price", "stock"]
            data = {k: v for k, v in data.items() if k in allowed_fields}

            if not data:
                return False

            set_clause = ", ".join([f"{key}=%s" for key in data.keys()])
            values = list(data.values())
            values.append(product_id)

            query = f"UPDATE products SET {set_clause} WHERE id=%s;"
            cursor.execute(query, values)
            conn.commit()

            return cursor.rowcount > 0
    finally:
        conn.close()



def delete_product(product_id):
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("DELETE FROM products WHERE id=%s;", (product_id,))
            conn.commit()
            return cursor.rowcount
    finally:
        conn.close()

def search_products(keyword):
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM products WHERE name LIKE %s;", (f"%{keyword}%",))
            return cursor.fetchall()
    finally:
        conn.close()

def get_low_stock(threshold=5):
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM products WHERE stock < %s;", (threshold,))
            return cursor.fetchall()
    finally:
        conn.close()