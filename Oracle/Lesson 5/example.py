"""
Урок 5: Подключение и базовые операции с Oracle Database на Python
Библиотека: python-oracledb (Thin Mode)
"""

import os
import sys

try:
    import oracledb
except ImportError:
    print("❌ Библиотека 'oracledb' не установлена.")
    print("👉 Установите её командой: pip install oracledb")
    sys.exit(1)

# ==============================================================================
# НАСТРОЙКИ ПОДКЛЮЧЕНИЯ
# ==============================================================================
ORACLE_USER = os.getenv("ORACLE_USER", "system")
ORACLE_PASSWORD = os.getenv("ORACLE_PASSWORD", "MyStrongPassword123!")
ORACLE_DSN = os.getenv("ORACLE_DSN", "localhost:1521/FREEPDB1")


def get_connection():
    """Создает соединение в Thin Mode (чистый Python без C-библиотек)"""
    try:
        conn = oracledb.connect(
            user=ORACLE_USER,
            password=ORACLE_PASSWORD,
            dsn=ORACLE_DSN
        )
        return conn
    except oracledb.DatabaseError as e:
        error_obj, = e.args
        print(f"❌ [CONNECT ERROR] Код ORA-{error_obj.code}: {error_obj.message}")
        print("👉 Убедитесь, что контейнер Oracle Database запущен на порту 1521.")
        sys.exit(1)


def setup_tables(cursor):
    """Инициализация демонстрационной таблицы"""
    print("--- 1. Создание таблицы demo_users ---")
    try:
        cursor.execute("DROP TABLE demo_users PURGE")
    except oracledb.DatabaseError:
        pass  # Таблица еще не существовала

    cursor.execute("""
        CREATE TABLE demo_users (
            id NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
            username VARCHAR2(50) NOT NULL UNIQUE,
            email VARCHAR2(100) NOT NULL UNIQUE,
            balance NUMBER(12, 2) DEFAULT 0.00 NOT NULL CHECK (balance >= 0),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    print("🛠️ Таблица demo_users успешно создана.\n")


def run_demo():
    print("=" * 65)
    print("      УРОК 5: ДЕМОНСТРАЦИЯ РАБОТЫ ORACLE DATABASE + PYTHON       ")
    print("=" * 65 + "\n")

    conn = get_connection()
    print(f"✅ [CONNECT] Успешное подключение к Oracle Database {conn.version}!\n")

    try:
        cursor = conn.cursor()

        # 1. DDL: Создание таблицы
        setup_tables(cursor)

        # ----------------------------------------------------------------------
        # 2. ПАКЕТНАЯ ВСТАВКА (INSERT - EXECUTEMANY)
        # ----------------------------------------------------------------------
        print("--- 2. Пакетная параметризованная вставка данных ---")
        users_data = [
            {"u": "alice_wonder", "e": "alice@oracle.com", "b": 15000.00},
            {"u": "bob_builder", "e": "bob@oracle.com", "b": 8500.50},
            {"u": "charlie_brown", "e": "charlie@oracle.com", "b": 1200.00},
            {"u": "diana_prince", "e": "diana@oracle.com", "b": 45000.00}
        ]

        insert_sql = """
            INSERT INTO demo_users (username, email, balance) 
            VALUES (:u, :e, :b)
        """
        cursor.executemany(insert_sql, users_data)
        conn.commit()  # Обязательный коммит в Oracle!
        print(f"➕ Успешно добавлено записей пакетом: {cursor.rowcount}\n")

        # ----------------------------------------------------------------------
        # 3. ВЫБОРКА ДАННЫХ СО СЛОВАРНЫМ ВЫВОДОМ (ROWFACTORY)
        # ----------------------------------------------------------------------
        print("--- 3. Выборка данных со словарным курсором (rowfactory) ---")
        cursor.execute("""
            SELECT id, username, email, balance, 
                   TO_CHAR(created_at, 'YYYY-MM-DD HH24:MI:SS') AS reg_date 
            FROM demo_users 
            WHERE balance > :min_balance 
            ORDER BY balance DESC
        """, {"min_balance": 5000.00})

        # Настраиваем вывод строк в виде словаря
        columns = [col[0].lower() for col in cursor.description]
        cursor.rowfactory = lambda *args: dict(zip(columns, args))

        wealthy_users = cursor.fetchall()
        print(f"Пользователи с балансом свыше 5 000 руб (Найдено: {len(wealthy_users)}):")
        for u in wealthy_users:
            print(f"  👤 ID: {u['id']:<2} | Логин: {u['username']:<15} | Баланс: {u['balance']:>10.2f} руб. | Дата: {u['reg_date']}")
        print()

        # ----------------------------------------------------------------------
        # 4. ОБНОВЛЕНИЕ ДАННЫХ (UPDATE)
        # ----------------------------------------------------------------------
        print("--- 4. Обновление баланса (Бонус 1 000 руб для Charlie) ---")
        cursor.execute("""
            UPDATE demo_users 
            SET balance = balance + :bonus 
            WHERE username = :uname
        """, {"bonus": 1000.00, "uname": "charlie_brown"})
        conn.commit()
        print(f"🔄 Баланс обновлен. Затронуто строк: {cursor.rowcount}\n")

        # ----------------------------------------------------------------------
        # 5. ТРАНЗАКЦИОННЫЙ ПЕРЕВОД СО СБОЕМ И ПРОВЕРКОЙ ROLLBACK
        # ----------------------------------------------------------------------
        print("--- 5. Демонстрация транзакции: Перевод средств со сбоем ---")
        transfer_amount = 99999.00  # Сумма превышает баланс Bob!

        try:
            print(f"Попытка перевести {transfer_amount:.2f} руб. от Bob к Alice...")
            
            # Шаг A: Списание средств с проверкой достаточности
            cursor.execute("""
                UPDATE demo_users 
                SET balance = balance - :amount 
                WHERE username = :from_u AND balance >= :amount
            """, {"amount": transfer_amount, "from_u": "bob_builder"})

            if cursor.rowcount == 0:
                raise ValueError("Недостаточно средств на балансе у Bob!")

            # Шаг Б: Начисление
            cursor.execute("""
                UPDATE demo_users 
                SET balance = balance + :amount 
                WHERE username = :to_u
            """, {"amount": transfer_amount, "to_u": "alice_wonder"})

            conn.commit()
            print("💸 Перевод успешно завершен.")

        except Exception as tx_err:
            conn.rollback()  # Откатываем транзакцию
            print(f"⚠️ [ROLLBACK] Транзакция отклонена: {tx_err}")
            print("🛡️ Балансы пользователей остались в исходном неизменном виде!\n")

        # Проверка итоговых балансов
        cursor.execute("SELECT username, balance FROM demo_users ORDER BY id ASC")
        print("Итоговые балансы пользователей:")
        for row in cursor.fetchall():
            print(f"  💰 {row['username']:<15}: {row['balance']:>10.2f} руб.")

        print("\n" + "=" * 65)
        print("          ДЕМОНСТРАЦИЯ ORACLE + PYTHON УСПЕШНО ЗАВЕРШЕНА!        ")
        print("=" * 65)

    finally:
        cursor.close()
        conn.close()
        print("🔌 Соединение с Oracle закрыто.")


if __name__ == "__main__":
    run_demo()
