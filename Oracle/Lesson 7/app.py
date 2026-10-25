"""
Финальный практический проект: Корпоративная система управления заказами на Python + Oracle Database
Использует пул сессий (Session Pool), транзакции (ACID), блокировки FOR UPDATE и многотабличные JOIN.
"""

import os
import sys

try:
    import oracledb
except ImportError:
    print("❌ Библиотека 'oracledb' не найдена. Установите: pip install oracledb")
    sys.exit(1)

# ==============================================================================
# НАСТРОЙКИ ПОДКЛЮЧЕНИЯ
# ==============================================================================
ORACLE_USER = os.getenv("ORACLE_USER", "system")
ORACLE_PASSWORD = os.getenv("ORACLE_PASSWORD", "MyStrongPassword123!")
ORACLE_DSN = os.getenv("ORACLE_DSN", "localhost:1521/FREEPDB1")

pool = None


def init_session_pool():
    """Инициализирует пул сессий Oracle в Thin Mode"""
    global pool
    try:
        pool = oracledb.create_pool(
            user=ORACLE_USER,
            password=ORACLE_PASSWORD,
            dsn=ORACLE_DSN,
            min=2,
            max=5,
            increment=1
        )
        print("⚡ [POOL] Пул сессий Oracle Database успешно инициализирован (2-5 сессий).\n")
    except oracledb.DatabaseError as e:
        error_obj, = e.args
        print(f"❌ [CRITICAL] Ошибка создания пула ORA-{error_obj.code}: {error_obj.message}")
        print("👉 Убедитесь, что контейнер Oracle запущен на порту 1521.")
        sys.exit(1)


def init_database_schema():
    """Создает таблицы и внешние ключи проекта"""
    with pool.acquire() as conn:
        cursor = conn.cursor()
        
        # Безопасное удаление старых таблиц
        for table in ["order_items", "orders", "products", "customers", "categories"]:
            try:
                cursor.execute(f"DROP TABLE {table} CASCADE CONSTRAINTS PURGE")
            except oracledb.DatabaseError:
                pass

        # 1. Категории
        cursor.execute("""
            CREATE TABLE categories (
                id NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
                name VARCHAR2(100) NOT NULL UNIQUE
            )
        """)

        # 2. Клиенты
        cursor.execute("""
            CREATE TABLE customers (
                id NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
                username VARCHAR2(50) NOT NULL UNIQUE,
                email VARCHAR2(100) NOT NULL UNIQUE,
                balance NUMBER(12, 2) DEFAULT 0.00 NOT NULL CHECK (balance >= 0)
            )
        """)

        # 3. Товары
        cursor.execute("""
            CREATE TABLE products (
                id NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
                category_id NUMBER NOT NULL,
                title VARCHAR2(150) NOT NULL,
                price NUMBER(10, 2) NOT NULL CHECK (price >= 0),
                stock_quantity NUMBER(6) DEFAULT 0 NOT NULL CHECK (stock_quantity >= 0),
                CONSTRAINT fk_prod_cat FOREIGN KEY (category_id) REFERENCES categories(id)
            )
        """)

        # 4. Заказы
        cursor.execute("""
            CREATE TABLE orders (
                id NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
                customer_id NUMBER NOT NULL,
                total_amount NUMBER(12, 2) DEFAULT 0.00 NOT NULL,
                status VARCHAR2(20) DEFAULT 'NEW' NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                CONSTRAINT fk_ord_cust FOREIGN KEY (customer_id) REFERENCES customers(id) ON DELETE CASCADE
            )
        """)

        # 5. Позиции заказа (Связующая таблица)
        cursor.execute("""
            CREATE TABLE order_items (
                id NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
                order_id NUMBER NOT NULL,
                product_id NUMBER NOT NULL,
                quantity NUMBER(6) NOT NULL CHECK (quantity > 0),
                price_at_purchase NUMBER(10, 2) NOT NULL,
                CONSTRAINT fk_item_ord FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE CASCADE,
                CONSTRAINT fk_item_prod FOREIGN KEY (product_id) REFERENCES products(id)
            )
        """)

        conn.commit()
        print("🛠️ [SCHEMA] Схема базы данных Oracle (5 таблиц) успешно развернута.")


def seed_catalog_data():
    """Наполнение начальными справочниками"""
    with pool.acquire() as conn:
        cursor = conn.cursor()

        # Категории
        categories = [
            ("Серверы и СХД",),
            ("Сетевое оборудование",),
            ("Рабочие станции",),
            ("Программное обеспечение",)
        ]
        cursor.executemany("INSERT INTO categories (name) VALUES (:1)", categories)

        # Товары
        products = [
            (1, "Сервер Oracle SPARC T8-1", 450000.00, 5),
            (1, "СХД Enterprise Flash Array 10TB", 280000.00, 8),
            (2, "Коммутатор 10GbE 48-port", 85000.00, 20),
            (3, "Рабочая станция Pro Dual Xeon", 175000.00, 12),
            (4, "Лицензия Oracle Linux Support", 35000.00, 50)
        ]
        cursor.executemany("""
            INSERT INTO products (category_id, title, price, stock_quantity) 
            VALUES (:1, :2, :3, :4)
        """, products)

        conn.commit()
        print("🌱 [SEED] Начальный каталог оборудования успешно загружен.\n")


def register_customer(username: str, email: str, initial_balance: float) -> int:
    """Регистрация клиента с получением сгенерированного ID через RETURNING INTO"""
    with pool.acquire() as conn:
        cursor = conn.cursor()
        out_id = cursor.var(oracledb.NUMBER)
        
        cursor.execute("""
            INSERT INTO customers (username, email, balance) 
            VALUES (:u, :e, :b) 
            RETURNING id INTO :out_id
        """, {"u": username, "e": email, "b": initial_balance, "out_id": out_id})
        
        conn.commit()
        customer_id = int(out_id.getvalue()[0])
        print(f"👤 [CUSTOMER] Зарегистрирован '{username}' (ID: {customer_id}) с балансом {initial_balance:,.2f} руб.")
        return customer_id


def checkout_order(customer_id: int, cart: list[dict]) -> int:
    """
    Транзакционное оформление заказа (ACID).
    cart = [{'product_id': 1, 'quantity': 2}, ...]
    """
    with pool.acquire() as conn:
        cursor = conn.cursor()
        try:
            total_sum = 0.0
            order_lines = []

            # 1. Проверяем остатки на складе с блокировкой строк (FOR UPDATE WAIT)
            for item in cart:
                p_id = item["product_id"]
                qty = item["quantity"]

                cursor.execute("""
                    SELECT title, price, stock_quantity 
                    FROM products 
                    WHERE id = :p_id 
                    FOR UPDATE WAIT 3
                """, {"p_id": p_id})

                prod = cursor.fetchone()
                if not prod:
                    raise ValueError(f"Товар с ID {p_id} отсутствует в номенклатуре!")

                title, price, stock = prod[0], float(prod[1]), prod[2]
                if stock < qty:
                    raise ValueError(f"Недостаточно товара '{title}' на складе! Запрошено: {qty}, в наличии: {stock}.")

                subtotal = price * qty
                total_sum += subtotal
                order_lines.append({
                    "product_id": p_id,
                    "title": title,
                    "price": price,
                    "quantity": qty
                })

            # 2. Проверяем баланс клиента с блокировкой
            cursor.execute("""
                SELECT balance FROM customers WHERE id = :c_id FOR UPDATE WAIT 3
            """, {"c_id": customer_id})
            cust = cursor.fetchone()

            if not cust:
                raise ValueError(f"Клиент с ID {customer_id} не найден!")

            client_balance = float(cust[0])
            if client_balance < total_sum:
                raise ValueError(f"Недостаточно средств на балансе! Сумма заказа: {total_sum:,.2f} руб., баланс: {client_balance:,.2f} руб.")

            # 3. Списание средств с баланса покупателя
            cursor.execute("""
                UPDATE customers SET balance = balance - :cost WHERE id = :c_id
            """, {"cost": total_sum, "c_id": customer_id})

            # 4. Списание остатков на складе
            for line in order_lines:
                cursor.execute("""
                    UPDATE products SET stock_quantity = stock_quantity - :qty WHERE id = :p_id
                """, {"qty": line["quantity"], "p_id": line["product_id"]})

            # 5. Создание записи заказа
            order_id_var = cursor.var(oracledb.NUMBER)
            cursor.execute("""
                INSERT INTO orders (customer_id, total_amount, status) 
                VALUES (:cid, :tot, 'PAID') 
                RETURNING id INTO :out_id
            """, {"cid": customer_id, "tot": total_sum, "out_id": order_id_var})

            order_id = int(order_id_var.getvalue()[0])

            # 6. Запись строк заказа (order_items)
            for line in order_lines:
                cursor.execute("""
                    INSERT INTO order_items (order_id, product_id, quantity, price_at_purchase)
                    VALUES (:oid, :pid, :qty, :prc)
                """, {"oid": order_id, "pid": line["product_id"], "qty": line["quantity"], "prc": line["price"]})

            # 7. Фиксация транзакции (COMMIT)
            conn.commit()
            print(f"🛒 [CHECKOUT] Заказ #{order_id} успешно оплачен на сумму {total_sum:,.2f} руб.")
            return order_id

        except Exception as err:
            # Откат транзакции при любой ошибке (ROLLBACK)
            conn.rollback()
            print(f"❌ [TRANSACTION ROLLBACK] Заказ отклонен: {err}")
            return None


def print_order_receipt(order_id: int):
    """Кассовый чек с многотабличным объединением (JOIN)"""
    with pool.acquire() as conn:
        cursor = conn.cursor()

        # Информация о заказе и покупателе
        cursor.execute("""
            SELECT o.id, TO_CHAR(o.created_at, 'YYYY-MM-DD HH24:MI:SS') AS o_date,
                   o.total_amount, o.status, c.username, c.email
            FROM orders o
            INNER JOIN customers c ON o.customer_id = c.id
            WHERE o.id = :oid
        """, {"oid": order_id})
        order = cursor.fetchone()

        if not order:
            print(f"Чек для заказа #{order_id} не найден.")
            return

        print("\n" + "=" * 65)
        print(f"                 КАССОВЫЙ ЧЕК ЗАКАЗА #{order[0]}                ")
        print("=" * 65)
        print(f"Клиент: {order[4]} ({order[5]})")
        print(f"Дата и время: {order[1]}")
        print(f"Статус транзакции: {order[3]}")
        print("-" * 65)
        print(f"{'Позиция номенклатуры':<35} {'Кол-во':>6} {'Цена':>10} {'Сумма':>11}")
        print("-" * 65)

        # Позиции чека
        cursor.execute("""
            SELECT p.title, oi.quantity, oi.price_at_purchase,
                   (oi.quantity * oi.price_at_purchase) AS subtotal
            FROM order_items oi
            INNER JOIN products p ON oi.product_id = p.id
            WHERE oi.order_id = :oid
        """, {"oid": order_id})

        for row in cursor.fetchall():
            print(f"{row[0]:<35} {row[1]:>6} {float(row[2]):>10.2f} {float(row[3]):>11.2f} руб.")

        print("=" * 65)
        print(f"{'ИТОГО К ОПЛАТЕ:':<51} {float(order[2]):>11.2f} руб.")
        print("=" * 65 + "\n")


def generate_category_sales_analytics():
    """Сводный аналитический отчет продаж по категориям (GROUP BY, HAVING)"""
    with pool.acquire() as conn:
        cursor = conn.cursor()
        print("📊 [ANALYTICS] Формирование корпоративного отчета продаж по категориям:")

        query = """
            SELECT 
                c.name AS category_name,
                COUNT(DISTINCT o.id) AS total_orders,
                SUM(oi.quantity) AS total_units_sold,
                SUM(oi.quantity * oi.price_at_purchase) AS total_revenue,
                ROUND(AVG(oi.price_at_purchase), 2) AS average_price
            FROM categories c
            INNER JOIN products p ON c.id = p.category_id
            INNER JOIN order_items oi ON p.id = oi.product_id
            INNER JOIN orders o ON oi.order_id = o.id
            WHERE o.status = 'PAID'
            GROUP BY c.id, c.name
            HAVING SUM(oi.quantity * oi.price_at_purchase) > 0
            ORDER BY total_revenue DESC
        """
        cursor.execute(query)
        report = cursor.fetchall()

        print("-" * 75)
        print(f"{'Категория':<22} {'Заказов':>8} {'Продано':>10} {'Выручка (руб)':>18} {'Ср. чек':>12}")
        print("-" * 75)
        for r in report:
            print(f"{r[0]:<22} {r[1]:>8} {r[2]:>10} {float(r[3]):>18.2f} {float(r[4]):>12.2f}")
        print("-" * 75 + "\n")


# ==============================================================================
# СЦЕНАРИЙ ДЕМОНСТРАЦИИ РАБОТЫ
# ==============================================================================
def main():
    print("=" * 70)
    print("        ЗАПУСК ФИНАЛЬНОГО ПРОЕКТА PYTHON + ORACLE DATABASE       ")
    print("=" * 70 + "\n")

    # 1. Запуск пула сессий и создание схемы
    init_session_pool()
    init_database_schema()
    seed_catalog_data()

    # 2. Регистрация клиентов
    print("--- ЭТАП 1: Регистрация корпоративных клиентов ---")
    c_gazprom = register_customer("corp_gazprom", "it@gazprom.ru", 1000000.00)
    c_startup = register_customer("small_startup", "dev@startup.io", 50000.00)
    print("-" * 50 + "\n")

    # 3. Успешный заказ крупного клиента
    print("--- ЭТАП 2: Успешная покупка сервера и коммутатора ---")
    cart_big = [
        {"product_id": 1, "quantity": 1},  # Сервер: 450 000 руб
        {"product_id": 3, "quantity": 2}   # Коммутаторы: 2 * 85 000 = 170 000 руб
    ]
    order_1 = checkout_order(c_gazprom, cart_big)
    if order_1:
        print_order_receipt(order_1)

    # 4. Попытка заказа со сбоем по складу (Демонстрация ROLLBACK)
    print("--- ЭТАП 3: Попытка заказать 100 серверов (Отказ по остаткам) ---")
    cart_overstock = [{"product_id": 1, "quantity": 100}]
    checkout_order(c_gazprom, cart_overstock)
    print("-" * 50 + "\n")

    # 5. Попытка покупки при нехватке баланса (Демонстрация ROLLBACK)
    print("--- ЭТАП 4: Попытка покупки стартапом без достаточного бюджета ---")
    cart_expensive = [{"product_id": 2, "quantity": 1}]  # СХД 280 000 руб (у стартапа только 50 000)
    checkout_order(c_startup, cart_expensive)
    print("-" * 50 + "\n")

    # 6. Успешная покупка в пределах бюджета
    print("--- ЭТАП 5: Успешная покупка ПО стартапом в рамках доступного баланса ---")
    cart_ok = [{"product_id": 5, "quantity": 1}]  # Лицензия 35 000 руб
    order_2 = checkout_order(c_startup, cart_ok)
    if order_2:
        print_order_receipt(order_2)

    # 7. Финансовая аналитика
    print("--- ЭТАП 6: Управленческий финансовый отчет ---")
    generate_category_sales_analytics()

    print("=" * 70)
    print("          ФИНАЛЬНЫЙ ПРОЕКТ ORACLE УСПЕШНО ЗАВЕРШЕН!              ")
    print("=" * 70)


if __name__ == "__main__":
    main()
