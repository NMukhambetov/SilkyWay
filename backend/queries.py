from db import get_connection

def get_all_products():
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM products;")
            return cursor.fetchall()
    finally:
        conn.close()


def get_product_by_id(product_id):
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM products WHERE id = %s;", (product_id,))
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
    finally:
        conn.close()


def update_product(id, name, description, price, stock):
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                UPDATE products
                SET name=%s, description=%s, price=%s, stock=%s
                WHERE id=%s;
                """,
                (name, description, price, stock, id)
            )
            conn.commit()
    finally:
        conn.close()


def delete_product(product_id):
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("DELETE FROM products WHERE id=%s;", (product_id,))
            conn.commit()
    finally:
        conn.close()
