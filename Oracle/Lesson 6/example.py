"""
Урок 6: Индексы, оптимизация запросов и интеграция с PL/SQL на Python
"""

import os
import sys
import time

try:
    import oracledb
except ImportError:
    print("❌ Библиотека 'oracledb' не найдена. Установите её: pip install oracledb")
    sys.exit(1)

ORACLE_USER = os.getenv("ORACLE_USER", "system")
ORACLE_PASSWORD = os.getenv("ORACLE_PASSWORD", "MyStrongPassword123!")
ORACLE_DSN = os.getenv("ORACLE_DSN", "localhost:1521/FREEPDB1")


def get_connection():
    try:
        return oracledb.connect(
            user=ORACLE_USER,
            password=ORACLE_PASSWORD,
            dsn=ORACLE_DSN
        )
    except oracledb.DatabaseError as e:
        error_obj, = e.args
        print(f"❌ [CONNECT ERROR] ORA-{error_obj.code}: {error_obj.message}")
        sys.exit(1)


def run_demo():
    print("=" * 70)
    print("      УРОК 6: ДЕМОНСТРАЦИЯ ИНДЕКСОВ И PL/SQL В ORACLE DATABASE      ")
    print("=" * 70 + "\n")

    conn = get_connection()
    cursor = conn.cursor()

    try:
        # ======================================================================
        # ЧАСТЬ 1: БЕНЧМАРК ИНДЕКСОВ (10 000 ЗАПИСЕЙ)
        # ======================================================================
        print("--- ЭТАП 1: Подготовка таблицы audit_events ---")
        try:
            cursor.execute("DROP TABLE audit_events PURGE")
        except oracledb.DatabaseError:
            pass

        cursor.execute("""
            CREATE TABLE audit_events (
                id NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
                user_email VARCHAR2(120) NOT NULL,
                action_name VARCHAR2(50) NOT NULL,
                ip_address VARCHAR2(45) NOT NULL,
                event_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Генерируем 10 000 строк пакетами
        total_rows = 10000
        batch_size = 2000
        print(f"⏳ Генерация и пакетная вставка {total_rows} записей...")

        insert_sql = """
            INSERT INTO audit_events (user_email, action_name, ip_address) 
            VALUES (:1, :2, :3)
        """
        for start_i in range(0, total_rows, batch_size):
            batch = [
                (f"user_{i}@enterprise.oracle.com", "LOGIN_ATTEMPT", f"10.0.1.{i % 254 + 1}")
                for i in range(start_i, start_i + batch_size)
            ]
            cursor.executemany(insert_sql, batch)

        conn.commit()
        print(f"✅ База данных успешно наполнена ({total_rows} строк).\n")

        target_email = "user_9876@enterprise.oracle.com"

        # ----------------------------------------------------------------------
        # 1. Поиск БЕЗ индекса (Full Table Scan)
        # ----------------------------------------------------------------------
        print(f"--- ЭТАП 2: Поиск БЕЗ индекса (Цель: '{target_email}') ---")
        start_time = time.perf_counter()
        cursor.execute("SELECT id, user_email, ip_address FROM audit_events WHERE user_email = :e", {"e": target_email})
        res_no_idx = cursor.fetchall()
        duration_no_idx = (time.perf_counter() - start_time) * 1000  # в миллисекундах

        print(f"⏱️ Время выполнения БЕЗ индекса: {duration_no_idx:.3f} мс")
        print(f"Найдено записей: {len(res_no_idx)}\n")

        # ----------------------------------------------------------------------
        # 2. Создание B-Tree индекса
        # ----------------------------------------------------------------------
        print("--- ЭТАП 3: Создание B-Tree индекса: CREATE INDEX idx_audit_email ---")
        idx_start = time.perf_counter()
        cursor.execute("CREATE INDEX idx_audit_email ON audit_events(user_email)")
        print(f"⚡ Индекс построен за {(time.perf_counter() - idx_start)*1000:.2f} мс!\n")

        # ----------------------------------------------------------------------
        # 3. Поиск С индексом (Index Range Scan)
        # ----------------------------------------------------------------------
        print("--- ЭТАП 4: Повторный поиск С индексом ---")
        start_time = time.perf_counter()
        cursor.execute("SELECT id, user_email, ip_address FROM audit_events WHERE user_email = :e", {"e": target_email})
        res_idx = cursor.fetchall()
        duration_idx = (time.perf_counter() - start_time) * 1000

        print(f"⏱️ Время выполнения С индексом: {duration_idx:.3f} мс")
        speedup = duration_no_idx / max(duration_idx, 0.0001)
        print(f"🚀 Ускорение поиска: в {speedup:.1f} раз быстрее!\n")

        # ======================================================================
        # ЧАСТЬ 2: СОЗДАНИЕ И ВЫЗОВ ХРАНИМОЙ ПРОЦЕДУРЫ PL/SQL
        # ======================================================================
        print("--- ЭТАП 5: Создание и вызов хранимой процедуры PL/SQL ---")
        
        # Создаем процедуру на сервере Oracle
        cursor.execute("""
            CREATE OR REPLACE PROCEDURE calculate_security_metric (
                p_email        IN  VARCHAR2,
                p_bonus_points IN  NUMBER,
                p_result_score OUT NUMBER
            ) AS
                v_attempts NUMBER;
            BEGIN
                SELECT COUNT(*) INTO v_attempts 
                FROM audit_events 
                WHERE user_email = p_email;

                p_result_score := (v_attempts * 10) + p_bonus_points;
            END;
        """)
        print("🛠️ Хранимая процедура 'calculate_security_metric' скомпилирована в базе данных.")

        # Вызываем процедуру из Python через callproc()
        bonus_points = 50
        # Создаем выходную переменную Oracle для приема OUT-параметра
        out_score = cursor.var(oracledb.NUMBER)

        cursor.callproc("calculate_security_metric", [target_email, bonus_points, out_score])
        final_score = out_score.getvalue()

        print(f"📊 Результат вызова процедуры для '{target_email}':")
        print(f"  Вычисленный скоринг безопасности (OUT параметр): {final_score}")

        print("\n" + "=" * 70)
        print("                 ТЕСТИРОВАНИЕ УСПЕШНО ЗАВЕРШЕНО!                ")
        print("=" * 70)

    finally:
        cursor.close()
        conn.close()


if __name__ == "__main__":
    run_demo()
