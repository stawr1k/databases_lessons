import os
import sys
import time
import json
import mysql.connector
from mysql.connector import Error

DB_CONFIG = {
    "host": os.getenv("MYSQL_HOST", "localhost"),
    "port": int(os.getenv("MYSQL_PORT", 3306)),
    "user": os.getenv("MYSQL_USER", "root"),
    "password": os.getenv("MYSQL_PASSWORD", "rootpassword"),
    "charset": "utf8mb4"
}

DB_NAME = "demo_lesson6_db"


def init_database():
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS {DB_NAME} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;")
        cursor.close()
        conn.close()
    except Error as e:
        print(f"❌ [ОШИБКА ПОДКЛЮЧЕНИЯ] Не удалось подключиться к MySQL: {e}")
        print("👉 Убедитесь, что сервер MySQL запущен.")
        sys.exit(1)


def run_optimization_demo():
    init_database()
    conn_params = {**DB_CONFIG, "database": DB_NAME, "autocommit": True}

    try:
        conn = mysql.connector.connect(**conn_params)
        cursor = conn.cursor(dictionary=True)
        print("=" * 70)
        print("      УРОК 6: ДЕМОНСТРАЦИЯ ИНДЕКСОВ, EXPLAIN И JSON В MYSQL      ")
        print("=" * 70 + "\n")

        # ======================================================================
        # ЧАСТЬ 1: ТЕСТИРОВАНИЕ ПРОИЗВОДИТЕЛЬНОСТИ ИНДЕКСОВ
        # ======================================================================
        print("--- ЭТАП 1: Создание тестовой таблицы и генерация 10 000 строк ---")
        cursor.execute("DROP TABLE IF EXISTS audit_logs;")
        cursor.execute("""
            CREATE TABLE audit_logs (
                id BIGINT AUTO_INCREMENT PRIMARY KEY,
                user_email VARCHAR(120) NOT NULL,
                action_name VARCHAR(50) NOT NULL,
                ip_address VARCHAR(45) NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            ) ENGINE=InnoDB;
        """)

        # Генерируем тестовые записи пакетами
        total_rows = 10000
        batch_size = 2000
        print(f"⏳ Наполнение таблицы {total_rows} записями...")

        for batch_start in range(0, total_rows, batch_size):
            batch_data = [
                (f"user_{i}@benchmark.org", "LOGIN_ATTEMPT", f"192.168.1.{i % 255}")
                for i in range(batch_start, batch_start + batch_size)
            ]
            cursor.executemany(
                "INSERT INTO audit_logs (user_email, action_name, ip_address) VALUES (%s, %s, %s)",
                batch_data
            )
        print(f"✅ База данных успешно заполнена ({total_rows} записей).\n")

        # Целевой email для поиска (находится в самом конце таблицы)
        target_email = "user_9876@benchmark.org"

        # ----------------------------------------------------------------------
        # 1. Запрос БЕЗ индекса (Full Table Scan)
        # ----------------------------------------------------------------------
        print(f"--- ЭТАП 2: Поиск без индекса (Target: '{target_email}') ---")
        
        # Анализ через EXPLAIN
        cursor.execute("EXPLAIN SELECT * FROM audit_logs WHERE user_email = %s;", (target_email,))
        explain_no_idx = cursor.fetchone()
        print(f"🔍 План EXPLAIN: type = '{explain_no_idx['type']}' (Полное сканирование!), rows = {explain_no_idx['rows']}")

        # Замер времени
        start_time = time.perf_counter()
        cursor.execute("SELECT * FROM audit_logs WHERE user_email = %s;", (target_email,))
        res_no_idx = cursor.fetchall()
        duration_no_idx = (time.perf_counter() - start_time) * 1000  # в миллисекундах

        print(f"⏱️ Время выполнения БЕЗ индекса: {duration_no_idx:.3f} мс")
        print(f"Найдено записей: {len(res_no_idx)}\n")

        # ----------------------------------------------------------------------
        # 2. Создание B-Tree индекса
        # ----------------------------------------------------------------------
        print("--- ЭТАП 3: Создание B-Tree индекса: CREATE INDEX idx_user_email ---")
        idx_start = time.perf_counter()
        cursor.execute("CREATE INDEX idx_user_email ON audit_logs(user_email);")
        print(f"⚡ Индекс построен за {(time.perf_counter() - idx_start)*1000:.2f} мс!\n")

        # ----------------------------------------------------------------------
        # 3. Запрос С индексом
        # ----------------------------------------------------------------------
        print(f"--- ЭТАП 4: Повторный поиск С индексом ---")
        
        # Анализ через EXPLAIN
        cursor.execute("EXPLAIN SELECT * FROM audit_logs WHERE user_email = %s;", (target_email,))
        explain_idx = cursor.fetchone()
        print(f"🔍 План EXPLAIN: type = '{explain_idx['type']}' (Поиск по ключу), key = '{explain_idx['key']}', rows = {explain_idx['rows']}")

        # Замер времени
        start_time = time.perf_counter()
        cursor.execute("SELECT * FROM audit_logs WHERE user_email = %s;", (target_email,))
        res_idx = cursor.fetchall()
        duration_idx = (time.perf_counter() - start_time) * 1000

        print(f"⏱️ Время выполнения С индексом: {duration_idx:.3f} мс")
        print(f"🚀 Ускорение поиска: в {duration_no_idx / max(duration_idx, 0.0001):.1f} раз быстрее!\n")

        # ======================================================================
        # ЧАСТЬ 2: РАБОТА С СОВРЕМЕННЫМ ТИПОМ JSON
        # ======================================================================
        print("--- ЭТАП 5: Работа с документами JSON в MySQL 8.x ---")
        cursor.execute("DROP TABLE IF EXISTS gadgets;")
        cursor.execute("""
            CREATE TABLE gadgets (
                id INT AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(100) NOT NULL,
                specs JSON NOT NULL
            ) ENGINE=InnoDB;
        """)

        # Вставка сложных структур
        laptop_specs = {
            "cpu": "Intel Core i7-14700",
            "ram_gb": 32,
            "ssd_gb": 1000,
            "interfaces": ["USB-C", "Thunderbolt 4", "HDMI 2.1"],
            "is_touchscreen": False
        }

        phone_specs = {
            "cpu": "Apple A18 Pro",
            "ram_gb": 8,
            "storage_gb": 256,
            "interfaces": ["USB-C"],
            "camera_mp": 48
        }

        insert_json_sql = "INSERT INTO gadgets (name, specs) VALUES (%s, %s);"
        cursor.execute(insert_json_sql, ("Pro Laptop 16", json.dumps(laptop_specs)))
        cursor.execute(insert_json_sql, ("Super Phone X", json.dumps(phone_specs)))
        print("💾 Гаджеты с JSON-спецификациями успешно сохранены.")

        # Извлечение свойств с помощью оператора ->>
        print("\nЗапрос данных с оператором стрелок '->>':")
        cursor.execute("""
            SELECT 
                name,
                specs->>'$.cpu' AS cpu_model,
                specs->'$.ram_gb' AS memory_gb,
                specs->'$.interfaces[0]' AS primary_port
            FROM gadgets;
        """)

        for row in cursor.fetchall():
            print(f"  📱 Модель: {row['name']:<15} | Процессор: {row['cpu_model']:<20} | RAM: {row['memory_gb']} GB | Порт: {row['primary_port']}")

        print("\n" + "=" * 70)
        print("                 ТЕСТИРОВАНИЕ УСПЕШНО ЗАВЕРШЕНО!                ")
        print("=" * 70)

    except Error as err:
        print(f"❌ Ошибка в процессе тестирования: {err}")
    finally:
        if 'cursor' in locals() and cursor:
            cursor.close()
        if 'conn' in locals() and conn.is_connected():
            conn.close()


if __name__ == "__main__":
    run_optimization_demo()
