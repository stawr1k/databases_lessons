import os
import sys
import mysql.connector
from mysql.connector import Error

# ==============================================================================
# НАСТРОЙКИ ПОДКЛЮЧЕНИЯ
# Параметры можно переопределить через переменные окружения или изменить здесь
# ==============================================================================
DB_CONFIG = {
    "host": os.getenv("MYSQL_HOST", "localhost"),
    "port": int(os.getenv("MYSQL_PORT", 3306)),
    "user": os.getenv("MYSQL_USER", "root"),
    "password": os.getenv("MYSQL_PASSWORD", "rootpassword"),
    "charset": "utf8mb4"
}

DB_NAME = "demo_lesson5_db"


def init_database():
    """Создает тестовую базу данных, если она еще не создана"""
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS {DB_NAME} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;")
        print(f"📦 [SETUP] База данных '{DB_NAME}' готова к работе.")
        cursor.close()
        conn.close()
    except Error as e:
        print(f"❌ [SETUP ERROR] Не удалось подключиться к серверу MySQL: {e}")
        print("👉 Убедитесь, что сервер MySQL или Docker-контейнер запущен на порту 3306.")
        sys.exit(1)


def run_demo():
    init_database()

    # Подключаемся уже непосредственно к нашей базе
    db_conn_config = {**DB_CONFIG, "database": DB_NAME, "autocommit": False}
    
    try:
        connection = mysql.connector.connect(**db_conn_config)
        cursor = connection.cursor(dictionary=True)
        print("✅ [CONNECT] Соединение с базой данных успешно установлено!\n")

        # ----------------------------------------------------------------------
        # 1. СОЗДАНИЕ ТАБЛИЦ (DDL)
        # ----------------------------------------------------------------------
        print("--- 1. Создание демонстрационной таблицы ---")
        cursor.execute("DROP TABLE IF EXISTS accounts;")
        cursor.execute("DROP TABLE IF EXISTS users;")
        
        cursor.execute("""
            CREATE TABLE users (
                id BIGINT AUTO_INCREMENT PRIMARY KEY,
                username VARCHAR(50) NOT NULL UNIQUE,
                email VARCHAR(100) NOT NULL UNIQUE,
                balance DECIMAL(10, 2) NOT NULL DEFAULT 0.00,
                is_active BOOLEAN NOT NULL DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            ) ENGINE=InnoDB;
        """)
        connection.commit()
        print("🛠️ Таблица 'users' успешно создана.\n")

        # ----------------------------------------------------------------------
        # 2. ПАРАМЕТРИЗОВАННАЯ ВСТАВКА (INSERT - CREATE)
        # ----------------------------------------------------------------------
        print("--- 2. Вставка данных (Одиночная и Пакетная) ---")
        
        # Безопасная одиночная вставка
        insert_single = """
            INSERT INTO users (username, email, balance) 
            VALUES (%s, %s, %s);
        """
        cursor.execute(insert_single, ("alice_wonder", "alice@example.com", 1500.50))
        connection.commit()
        alice_id = cursor.lastrowid
        print(f"➕ Добавлен пользователь Alice (ID: {alice_id})")

        # Пакетная вставка (Batch Insert через executemany)
        batch_users = [
            ("bob_builder", "bob@example.com", 2400.00),
            ("charlie_brown", "charlie@example.com", 750.25),
            ("diana_prince", "diana@example.com", 5000.00)
        ]
        cursor.executemany(insert_single, batch_users)
        connection.commit()
        print(f"➕ Добавлено пользователей пакетом: {cursor.rowcount}\n")

        # ----------------------------------------------------------------------
        # 3. ВЫБОРКА ДАННЫХ (SELECT - READ)
        # ----------------------------------------------------------------------
        print("--- 3. Выборка данных со словарным курсором (dictionary=True) ---")
        
        # Параметризованная фильтрация
        select_query = """
            SELECT id, username, email, balance 
            FROM users 
            WHERE balance > %s 
            ORDER BY balance DESC;
        """
        cursor.execute(select_query, (1000.00,))
        wealthy_users = cursor.fetchall()

        print("Пользователи с балансом свыше 1000.00 руб:")
        for u in wealthy_users:
            print(f"  👤 ID: {u['id']} | Логин: {u['username']:<15} | Баланс: {u['balance']:>8.2f} руб.")
        print()

        # ----------------------------------------------------------------------
        # 4. ОБНОВЛЕНИЕ ДАННЫХ (UPDATE)
        # ----------------------------------------------------------------------
        print("--- 4. Безопасное обновление записи ---")
        update_query = "UPDATE users SET balance = balance + %s WHERE username = %s;"
        cursor.execute(update_query, (500.00, "alice_wonder"))
        connection.commit()
        print(f"🔄 Баланс Alice пополнен на 500 руб. Затронуто строк: {cursor.rowcount}\n")

        # ----------------------------------------------------------------------
        # 5. ТРАНЗАКЦИОННЫЙ ПЕРЕВОД С ПРОВЕРКОЙ И ОТКАТОМ (ACID)
        # ----------------------------------------------------------------------
        print("--- 5. Демонстрация транзакции: Перевод средств от Bob к Charlie ---")
        transfer_amount = 400.00
        
        try:
            # Начинаем перевод (транзакция управляется вручную)
            # Шаг 1: Списываем у Bob
            cursor.execute("UPDATE users SET balance = balance - %s WHERE username = %s AND balance >= %s;", 
                           (transfer_amount, "bob_builder", transfer_amount))
            
            if cursor.rowcount == 0:
                raise ValueError("Недостаточно средств у отправителя!")

            # Шаг 2: Начисляем Charlie
            cursor.execute("UPDATE users SET balance = balance + %s WHERE username = %s;", 
                           (transfer_amount, "charlie_brown"))

            # Фиксируем транзакцию
            connection.commit()
            print(f"💸 Транзакция успешна! {transfer_amount} руб. переведено от Bob к Charlie.")

        except Exception as tx_err:
            connection.rollback()
            print(f"⚠️ Ошибка транзакции! Изменения отменены (ROLLBACK): {tx_err}")

        # Проверка итоговых балансов
        cursor.execute("SELECT username, balance FROM users WHERE username IN ('bob_builder', 'charlie_brown');")
        for row in cursor.fetchall():
            print(f"  💰 {row['username']}: {row['balance']} руб.")
        print()

        # ----------------------------------------------------------------------
        # 6. УДАЛЕНИЕ ЗАПИСИ (DELETE)
        # ----------------------------------------------------------------------
        print("--- 6. Удаление пользователя ---")
        cursor.execute("DELETE FROM users WHERE username = %s;", ("diana_prince",))
        connection.commit()
        print(f"🗑️ Пользователь diana_prince удален. Затронуто строк: {cursor.rowcount}\n")

        print("=" * 60)
        print("  ДЕМОНСТРАЦИЯ РАБОТЫ PYTHON + MYSQL УСПЕШНО ЗАВЕРШЕНА!  ")
        print("=" * 60)

    except Error as err:
        print(f"❌ Критическая ошибка выполнения запроса: {err}")
    finally:
        if 'cursor' in locals() and cursor:
            cursor.close()
        if 'connection' in locals() and connection.is_connected():
            connection.close()
            print("🔌 Соединение с MySQL закрыто.")


if __name__ == "__main__":
    run_demo()
