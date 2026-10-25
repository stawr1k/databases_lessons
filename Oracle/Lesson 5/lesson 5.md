# Лекция 5: Подключение и работа с Oracle Database на языке Python (python-oracledb)

## 1. Введение и библиотека python-oracledb

Для взаимодействия с Oracle Database из языка Python используется официальная библиотека нового поколения — **`python-oracledb`** (разрабатывается напрямую командой Oracle Database и является официальным преемником устаревшей библиотеки `cx_Oracle`).

### Революция Thin Mode (Тонкий режим):
Исторически для подключения к Oracle из Python требовалось вручную скачивать и настраивать огромный пакет *Oracle Instant Client* (C-библиотеки OCI), прописывать системные переменные `LD_LIBRARY_PATH` или `PATH`, что доставляло множество неудобств.

Библиотека `python-oracledb` по умолчанию работает в **Thin Mode (Тонкий режим)**:
* Написана на **чистом Python** и реализует сетевой протокол TNS напрямую.
* **Не требует установки Oracle Client**, C-библиотек или системных драйверов.
* Мгновенно устанавливается через `pip` и работает одинаково гладко на Windows, macOS и Linux.

---

## 2. Подготовка окружения

### Шаг 1. Создание и активация виртуального окружения

```bash
# Windows
python -m venv .venv
.venv\Scripts\Activate.ps1

# Linux / macOS
python3 -m venv .venv
source .venv/bin/activate
```

### Шаг 2. Установка библиотеки

```bash
pip install oracledb
```

---

## 3. Подключение к СУБД: DSN и параметры

Для подключения к подключаемой базе данных (PDB) используется строка подключения DSN (*Data Source Name*) в формате `хост:порт/имя_службы`:

```python
import oracledb

try:
    connection = oracledb.connect(
        user="dev_user",
        password="StrongPassword123!",
        dsn="localhost:1521/FREEPDB1"
    )
    print("✅ Успешное подключение к Oracle Database!")
    print(f"Версия сервера: {connection.version}")

except oracledb.DatabaseError as e:
    error_obj, = e.args
    print(f"❌ Ошибка подключения ORA-{error_obj.code}: {error_obj.message}")

finally:
    if 'connection' in locals() and connection:
        connection.close()
        print("🔌 Соединение закрыто.")
```

---

## 4. Словарный вывод (Rowfactory)

По умолчанию курсор Oracle возвращает строки в виде обычных кортежей: `(1, 'alex_dev', 5000.0)`.

Чтобы получать удобные словари Python (`{'id': 1, 'username': 'alex_dev', 'balance': 5000.0}`), используется стандартный механизм `cursor.rowfactory`:

```python
cursor = connection.cursor()
cursor.execute("SELECT id, username, balance FROM users")

# Преобразуем каждую строку в словарь с ключами в нижнем регистре:
columns = [col[0].lower() for col in cursor.description]
cursor.rowfactory = lambda *args: dict(zip(columns, args))

for row in cursor.fetchall():
    print(f"Пользователь: {row['username']} | Баланс: {row['balance']} руб.")
```

---

## 5. Защита от SQL Injection: Параметризованные запросы в Oracle

> **🛑 КРИТИЧЕСКИ ВАЖНОЕ ПРАВИЛО:**  
> В Oracle Database плейсхолдеры параметров обозначаются двоеточием **`:имя_переменной`** или номерами **`:1, :2`** (в отличие от `%s` в MySQL/PostgreSQL или `?` в SQLite)!

### ❌ Смертельно опасный код (Уязвимость SQL-инъекции):
```python
# НИКОГДА так не пишите!
login = "admin' OR '1'='1"
cursor.execute(f"SELECT * FROM users WHERE username = '{login}'")
```

### ✅ Безопасный параметризованный запрос:
```python
query = "SELECT id, username, balance FROM users WHERE username = :u AND balance >= :b"
params = {"u": "alex_dev", "b": 1000.00}

cursor.execute(query, params)
user = cursor.fetchone()
```
Параметризация не только защищает от взлома, но и активирует механизм **Shared Pool**: Oracle один раз компилирует план выполнения запроса и переиспользует его для миллионов вызовов с разными аргументами (*Soft Parse*).

---

## 6. Управление транзакциями и пакетная вставка (executemany)

### Пакетная вставка (executemany):
Пакетная вставка передает на сервер сотни строк за один сетевой вызов, ускоряя работу в 10–50 раз:

```python
new_users = [
    {"uname": "olga_k", "mail": "olga@mail.ru", "bal": 2500.00},
    {"uname": "ivan_p", "mail": "ivan@mail.ru", "bal": 4200.50},
    {"uname": "sergey_d", "mail": "sergey@mail.ru", "bal": 150.00}
]

insert_sql = """
    INSERT INTO users (username, email, balance) 
    VALUES (:uname, :mail, :bal)
"""

cursor.executemany(insert_sql, new_users)
connection.commit()  # Обязательно подтверждаем транзакцию!
print(f"Успешно добавлено записей: {cursor.rowcount}")
```

### Атомарный перевод средств с гарантией ROLLBACK:

```python
try:
    amount = 500.00
    from_user = "olga_k"
    to_user = "ivan_p"
    
    # 1. Списываем с баланса Ольги
    cursor.execute("""
        UPDATE users SET balance = balance - :amount 
        WHERE username = :uname AND balance >= :amount
    """, {"amount": amount, "uname": from_user})
    
    if cursor.rowcount == 0:
        raise ValueError("Недостаточно средств на балансе отправителя!")

    # 2. Начисляем на баланс Ивана
    cursor.execute("""
        UPDATE users SET balance = balance + :amount 
        WHERE username = :uname
    """, {"amount": amount, "uname": to_user})

    # Фиксируем транзакцию
    connection.commit()
    print("💸 Перевод успешно зафиксирован на диске!")

except Exception as err:
    connection.rollback()  # Откатываем все изменения при ошибке
    print(f"⚠️ Ошибка транзакции! Выполнен откат (ROLLBACK): {err}")
```

---

## 7. Демонстрационный скрипт (example.py)

В директории урока находится полностью автономный файл [`example.py`](./example.py), демонстрирующий полный рабочий цикл:
* Создание схемы таблиц через DDL.
* Пакетную вставку данных через `executemany`.
* Выборку со словарным представлением `rowfactory`.
* Демонстрацию транзакции с намеренным сбоем и проверкой корректности `ROLLBACK`.

Запуск скрипта:

```bash
python example.py
```

`Следующий материал:` [Лекция 6: Индексы, анализ плана выполнения (EXPLAIN PLAN) и основы PL/SQL](../Lesson%206/lesson%206.md)
