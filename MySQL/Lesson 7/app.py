"""
Финальный практический проект: Сервис интернет-магазина на Python + MySQL
Использует пул соединений, транзакции (ACID), реляционные связи (JOIN) и нативный JSON.
"""

import os
import sys
import json
import mysql.connector
from mysql.connector import pooling, Error

# ==============================================================================
# НАСТРОЙКИ ПОДКЛЮЧЕНИЯ
# ==============================================================================
DB_CONFIG = {
    "host": os.getenv("MYSQL_HOST", "localhost"),
    "port": int(os.getenv("MYSQL_PORT", 3306)),
    "user": os.getenv("MYSQL_USER", "root"),
    "password": os.getenv("MYSQL_PASSWORD", "rootpassword"),
    "charset": "utf8mb4"
}

DB_NAME = "ecommerce_db"
pool = None


def setup_database_and_pool():
    """Создает базу данных и инициализирует пул постоянных соединений"""
    global pool
    try:
        # Первичное подключение к СУБД для создания базы данных
        admin_conn = mysql.connector.connect(**DB_CONFIG)
        admin_cursor = admin_conn.cursor()
        admin_cursor.execute(f"CREATE DATABASE IF NOT EXISTS {DB_NAME} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;")
        admin_cursor.close()
        admin_conn.close()

        # Инициализация пула соединений
        pool = pooling.MySQLConnectionPool(
            pool_name="ecommerce_pool",
            pool_size=5,
            pool_reset_session=True,
            database=DB_NAME,
            **DB_CONFIG
        )
        print("⚡ [POOL] Пул соединений MySQL успешно инициализирован (Размер: 5).\n")

    except Error as e:
        print(f"❌ [CRITICAL] Ошибка инициализации базы данных: {e}")
        print("👉 Убедитесь, что сервер MySQL доступен на порту 3306.")
        sys.exit(1)


def get_db_connection():
    """Извлекает свободное соединение из пула"""
    return pool.get_connection()


def init_schema():
    """Создает таблицы и внешние ключи с каскадным контролем целостности"""
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # Отключаем проверку внешних ключей для безопасного пересоздания схемы
        cursor.execute("SET FOREIGN_KEY_CHECKS = 0;")
        cursor.execute("DROP TABLE IF EXISTS audit_logs;")
        cursor.execute("DROP TABLE IF EXISTS order_items;")
        cursor.execute("DROP TABLE IF EXISTS orders;")
        cursor.execute("DROP TABLE IF EXISTS products;")
        cursor.execute("DROP TABLE IF EXISTS categories;")
        cursor.execute("DROP TABLE IF EXISTS users;")
        cursor.execute("SET FOREIGN_KEY_CHECKS = 1;")

        # 1. Таблица категорий
        cursor.execute("""
            CREATE TABLE categories (
                id INT AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(100) NOT NULL UNIQUE
            ) ENGINE=InnoDB;
        """)

        # 2. Таблица пользователей
        cursor.execute("""
            CREATE TABLE users (
                id BIGINT AUTO_INCREMENT PRIMARY KEY,
                username VARCHAR(50) NOT NULL UNIQUE,
                email VARCHAR(100) NOT NULL UNIQUE,
                balance DECIMAL(12, 2) NOT NULL DEFAULT 0.00 CHECK (balance >= 0.00),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            ) ENGINE=InnoDB;
        """)

        # 3. Таблица товаров (включая нативный JSON)
        cursor.execute("""
            CREATE TABLE products (
                id BIGINT AUTO_INCREMENT PRIMARY KEY,
                category_id INT NOT NULL,
                title VARCHAR(150) NOT NULL,
                price DECIMAL(10, 2) NOT NULL CHECK (price >= 0.00),
                stock_quantity INT NOT NULL DEFAULT 0 CHECK (stock_quantity >= 0),
                attributes JSON NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                CONSTRAINT fk_products_category 
                    FOREIGN KEY (category_id) REFERENCES categories(id)
                    ON DELETE RESTRICT
            ) ENGINE=InnoDB;
        """)

        # 4. Таблица заказов
        cursor.execute("""
            CREATE TABLE orders (
                id BIGINT AUTO_INCREMENT PRIMARY KEY,
                user_id BIGINT NOT NULL,
                total_amount DECIMAL(12, 2) NOT NULL DEFAULT 0.00,
                status VARCHAR(30) NOT NULL DEFAULT 'NEW',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                CONSTRAINT fk_orders_user 
                    FOREIGN KEY (user_id) REFERENCES users(id)
                    ON DELETE CASCADE
            ) ENGINE=InnoDB;
        """)

        # 5. Позиции заказа (Связующая таблица M:N с фиксацией цены на момент покупки)
        cursor.execute("""
            CREATE TABLE order_items (
                id BIGINT AUTO_INCREMENT PRIMARY KEY,
                order_id BIGINT NOT NULL,
                product_id BIGINT NOT NULL,
                quantity INT NOT NULL CHECK (quantity > 0),
                price_at_purchase DECIMAL(10, 2) NOT NULL,
                CONSTRAINT fk_items_order 
                    FOREIGN KEY (order_id) REFERENCES orders(id)
                    ON DELETE CASCADE,
                CONSTRAINT fk_items_product 
                    FOREIGN KEY (product_id) REFERENCES products(id)
                    ON DELETE RESTRICT
            ) ENGINE=InnoDB;
        """)

        # 6. Журнал аудита
        cursor.execute("""
            CREATE TABLE audit_logs (
                id BIGINT AUTO_INCREMENT PRIMARY KEY,
                event_type VARCHAR(50) NOT NULL,
                details JSON NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            ) ENGINE=InnoDB;
        """)

        conn.commit()
        print("🛠️ [SCHEMA] Схема базы данных успешно развернута.")

    finally:
        cursor.close()
        conn.close()


def seed_data():
    """Наполняет базу первоначальными данными"""
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # Категории
        cursor.executemany("INSERT INTO categories (id, name) VALUES (%s, %s);", [
            (1, "Ноутбуки и ПК"),
            (2, "Смартфоны"),
            (3, "Аксессуары")
        ])

        # Товары
        products = [
            (1, "Ноутбук Pro 16", 120000.00, 10, json.dumps({"ram": 32, "storage": 1000, "color": "Space Gray"})),
            (2, "Смартфон Neo X", 55000.00, 15, json.dumps({"ram": 12, "storage": 256, "color": "Midnight"})),
            (3, "Беспроводные наушники AirPro", 12000.00, 30, json.dumps({"battery_hours": 30, "anc": True})),
            (4, "Быстрая зарядка 65W", 2500.00, 50, json.dumps({"ports": ["USB-C", "USB-A"]}))
        ]
        cursor.executemany("""
            INSERT INTO products (category_id, title, price, stock_quantity, attributes) 
            VALUES (%s, %s, %s, %s, %s);
        """, products)

        conn.commit()
        print("🌱 [SEED] Начальные категории и товары загружены в базу.")

    finally:
        cursor.close()
        conn.close()


def register_user(username: str, email: str, initial_balance: float) -> int:
    """Регистрирует нового пользователя с балансом"""
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("""
            INSERT INTO users (username, email, balance) 
            VALUES (%s, %s, %s);
        """, (username, email, initial_balance))
        conn.commit()
        user_id = cursor.lastrowid
        print(f"👤 [USER] Создан аккаунт '{username}' (ID: {user_id}) с балансом {initial_balance:.2f} руб.")
        return user_id
    finally:
        cursor.close()
        conn.close()


def checkout_order(user_id: int, cart: list[dict]) -> int:
    """
    Транзакционное оформление заказа (ACID).
    cart = [{'product_id': 1, 'quantity': 2}, ...]
    """
    conn = get_db_connection()
    conn.autocommit = False  # Ручное управление транзакцией
    cursor = conn.cursor(dictionary=True)

    try:
        total_order_sum = 0.0
        validated_items = []

        # 1. Проверяем товары на складе с блокировкой строк (FOR UPDATE)
        for item in cart:
            p_id = item["product_id"]
            qty = item["quantity"]

            cursor.execute("SELECT id, title, price, stock_quantity FROM products WHERE id = %s FOR UPDATE;", (p_id,))
            product = cursor.fetchone()

            if not product:
                raise ValueError(f"Товар с ID {p_id} не существует в каталоге!")
            if product["stock_quantity"] < qty:
                raise ValueError(f"Недостаточно товара '{product['title']}' на складе! Запрошено: {qty}, в наличии: {product['stock_quantity']}.")

            item_cost = float(product["price"]) * qty
            total_order_sum += item_cost
            validated_items.append({
                "product_id": p_id,
                "title": product["title"],
                "quantity": qty,
                "unit_price": float(product["price"])
            })

        # 2. Проверяем баланс покупателя с блокировкой строки
        cursor.execute("SELECT balance FROM users WHERE id = %s FOR UPDATE;", (user_id,))
        user = cursor.fetchone()
        if not user:
            raise ValueError(f"Пользователь с ID {user_id} не найден!")

        if float(user["balance"]) < total_order_sum:
            raise ValueError(f"Недостаточно средств на балансе! Сумма заказа: {total_order_sum:.2f} руб., баланс: {float(user['balance']):.2f} руб.")

        # 3. Списание средств с баланса покупателя
        cursor.execute("UPDATE users SET balance = balance - %s WHERE id = %s;", (total_order_sum, user_id))

        # 4. Списание складских остатков
        for item in validated_items:
            cursor.execute("UPDATE products SET stock_quantity = stock_quantity - %s WHERE id = %s;", 
                           (item["quantity"], item["product_id"]))

        # 5. Создание записи заказа
        cursor.execute("INSERT INTO orders (user_id, total_amount, status) VALUES (%s, %s, 'PAID');", 
                       (user_id, total_order_sum))
        order_id = cursor.lastrowid

        # 6. Запись позиций заказа (order_items)
        for item in validated_items:
            cursor.execute("""
                INSERT INTO order_items (order_id, product_id, quantity, price_at_purchase) 
                VALUES (%s, %s, %s, %s);
            """, (order_id, item["product_id"], item["quantity"], item["unit_price"]))

        # 7. Логирование действия в аудит
        audit_payload = {
            "order_id": order_id,
            "user_id": user_id,
            "amount": total_order_sum,
            "items_count": len(validated_items)
        }
        cursor.execute("INSERT INTO audit_logs (event_type, details) VALUES ('ORDER_COMPLETED', %s);", 
                       (json.dumps(audit_payload),))

        # ФИКСАЦИЯ ТРАНЗАКЦИИ (Все изменения атомарно сохраняются на диск)
        conn.commit()
        print(f"🛒 [CHECKOUT] Заказ #{order_id} успешно оформлен и оплачен на сумму {total_order_sum:.2f} руб.")
        return order_id

    except Exception as err:
        # ОТКАТ ТРАНЗАКЦИИ (Все промежуточные изменения полностью стираются)
        conn.rollback()
        print(f"❌ [TRANSACTION ROLLBACK] Заказ отклонен: {err}")
        return None

    finally:
        cursor.close()
        conn.close()


def print_order_receipt(order_id: int):
    """Выводит детальный чек заказа с объединением 4 таблиц (JOIN)"""
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        # Запрос информации о заказе и покупателе
        cursor.execute("""
            SELECT o.id, o.created_at, o.total_amount, o.status, u.username, u.email
            FROM orders o
            INNER JOIN users u ON o.user_id = u.id
            WHERE o.id = %s;
        """, (order_id,))
        order = cursor.fetchone()

        if not order:
            print(f"Чек для заказа #{order_id} не найден.")
            return

        print("\n" + "=" * 60)
        print(f"                 КАССОВЫЙ ЧЕК #{order['id']}                 ")
        print("=" * 60)
        print(f"Покупатель: {order['username']} ({order['email']})")
        print(f"Дата и время: {order['created_at']}")
        print(f"Статус оплаты: {order['status']}")
        print("-" * 60)
        print(f"{'Товар':<30} {'Кол-во':>6} {'Цена':>10} {'Сумма':>10}")
        print("-" * 60)

        # Выборка позиций заказа через JOIN с продуктами
        cursor.execute("""
            SELECT p.title, oi.quantity, oi.price_at_purchase,
                   (oi.quantity * oi.price_at_purchase) AS subtotal
            FROM order_items oi
            INNER JOIN products p ON oi.product_id = p.id
            WHERE oi.order_id = %s;
        """, (order_id,))

        for row in cursor.fetchall():
            print(f"{row['title']:<30} {row['quantity']:>6} {float(row['price_at_purchase']):>10.2f} {float(row['subtotal']):>10.2f} руб.")

        print("=" * 60)
        print(f"{'ИТОГО К ОПЛАТЕ:':<48} {float(order['total_amount']):>10.2f} руб.")
        print("=" * 60 + "\n")

    finally:
        cursor.close()
        conn.close()


def generate_sales_analytics():
    """Формирует сводный аналитический отчет по категориям с GROUP BY и HAVING"""
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        print("📊 [ANALYTICS] Формирование финансового отчета продаж по категориям:")
        
        query = """
            SELECT 
                c.name AS category_name,
                COUNT(DISTINCT o.id) AS total_orders,
                SUM(oi.quantity) AS total_units_sold,
                SUM(oi.quantity * oi.price_at_purchase) AS total_revenue,
                ROUND(AVG(oi.price_at_purchase), 2) AS average_item_price
            FROM categories c
            INNER JOIN products p ON c.id = p.category_id
            INNER JOIN order_items oi ON p.id = oi.product_id
            INNER JOIN orders o ON oi.order_id = o.id
            WHERE o.status = 'PAID'
            GROUP BY c.id, c.name
            HAVING total_revenue > 0
            ORDER BY total_revenue DESC;
        """
        cursor.execute(query)
        report = cursor.fetchall()

        print("-" * 75)
        print(f"{'Категория':<20} {'Заказов':>8} {'Продано шт':>12} {'Выручка (руб)':>18} {'Ср. цена':>12}")
        print("-" * 75)
        for r in report:
            print(f"{r['category_name']:<20} {r['total_orders']:>8} {r['total_units_sold']:>12} {float(r['total_revenue']):>18.2f} {float(r['average_item_price']):>12.2f}")
        print("-" * 75 + "\n")

    finally:
        cursor.close()
        conn.close()


# ==============================================================================
# СЦЕНАРИЙ ДЕМОНСТРАЦИИ РАБОТЫ ПРИЛОЖЕНИЯ
# ==============================================================================
def main():
    print("=" * 70)
    print("        ЗАПУСК ФИНАЛЬНОГО ПРАКТИЧЕСКОГО ПРОЕКТА PYTHON + MYSQL       ")
    print("=" * 70 + "\n")

    # 1. Развертывание БД и пула
    setup_database_and_pool()
    init_schema()
    seed_data()
    print()

    # 2. Регистрация клиентов
    print("--- ЭТАП 1: Регистрация пользователей в системе ---")
    user_alex = register_user("alex_gamer", "alex@game.com", 200000.00)
    user_elena = register_user("elena_smart", "elena@tech.com", 15000.00)
    print("-" * 50 + "\n")

    # 3. Успешный заказ (Alex покупает ноутбук и наушники)
    print("--- ЭТАП 2: Успешное транзакционное оформление заказа ---")
    cart_alex = [
        {"product_id": 1, "quantity": 1},  # Ноутбук: 120 000 руб
        {"product_id": 3, "quantity": 2}   # Наушники: 2 * 12 000 = 24 000 руб
    ]
    order_id_1 = checkout_order(user_alex, cart_alex)
    if order_id_1:
        print_order_receipt(order_id_1)

    # 4. Попытка заказа с превышением остатка на складе (Демонстрация ROLLBACK)
    print("--- ЭТАП 3: Попытка заказать 999 ноутбуков (Складской отказ) ---")
    cart_impossible = [{"product_id": 1, "quantity": 999}]
    checkout_order(user_alex, cart_impossible)
    print("-" * 50 + "\n")

    # 5. Попытка заказа с нехваткой баланса (Финансовый отказ ROLLBACK)
    print("--- ЭТАП 4: Попытка покупки без достаточного баланса ---")
    cart_elena = [{"product_id": 2, "quantity": 1}]  # Смартфон: 55 000 руб (у нее только 15 000)
    checkout_order(user_elena, cart_elena)
    print("-" * 50 + "\n")

    # 6. Успешный заказ Elena (покупает аксессуары в пределах баланса)
    print("--- ЭТАП 5: Успешная покупка Елены в пределах доступного бюджета ---")
    cart_elena_ok = [
        {"product_id": 3, "quantity": 1},  # Наушники 12 000 руб
        {"product_id": 4, "quantity": 1}   # Зарядка 2 500 руб (Итого 14 500)
    ]
    order_id_2 = checkout_order(user_elena, cart_elena_ok)
    if order_id_2:
        print_order_receipt(order_id_2)

    # 7. Финансовая аналитика
    print("--- ЭТАП 6: Генерация бизнес-отчетности ---")
    generate_sales_analytics()

    print("=" * 70)
    print("             ПРАКТИЧЕСКИЙ ПРОЕКТ УСПЕШНО ЗАВЕРШЕН!              ")
    print("=" * 70)


if __name__ == "__main__":
    main()
