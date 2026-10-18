# Лекция 5: Подключение и работа с MySQL на языке Python

## 1. Введение и подготовка окружения

Для взаимодействия с MySQL из языка Python используется официальная клиентская библиотека **`mysql-connector-python`** (разрабатывается напрямую командой Oracle MySQL) или её популярный аналог **`PyMySQL`**.

### Шаг 1. Проверка установки Python

Убедитесь, что в системе установлен Python версии 3.9 или выше:

```bash
# Windows
python --version

# Linux / macOS
python3 --version
```

### Шаг 2. Создание виртуального окружения

Создание виртуального окружения позволяет изолировать зависимости вашего проекта от глобальной операционной системы:

| Операционная система | Команда создания |
| :--- | :--- |
| **Windows** | `python -m venv .venv` |
| **Linux / macOS** | `python3 -m venv .venv` |

### Шаг 3. Активация виртуального окружения

```bash
# Windows (PowerShell)
.venv\Scripts\Activate.ps1

# Windows (Command Prompt - cmd)
.venv\Scripts\activate.bat

# Linux / macOS
source .venv/bin/activate
```

После активации в начале строки терминала появится маркер `(.venv)`.

### Шаг 4. Установка официального коннектора MySQL

```bash
pip install mysql-connector-python
```

*(Опционально можно установить также `python-dotenv` для безопасного хранения паролей в файле `.env`)*.

---

## 2. Параметры подключения и объект Connection

Для открытия сессии с сервером базы данных вызывается функция `mysql.connector.connect()`:

```python
import mysql.connector
from mysql.connector import Error

try:
    connection = mysql.connector.connect(
        host="localhost",           # Хост (127.0.0.1)
        port=3306,                  # Порт сервера MySQL
        user="root",                # Имя пользователя
        password="secretpassword",  # Пароль
        database="shop_db",         # Имя базы данных
        charset="utf8mb4",          # Кодировка для поддержки Unicode
        autocommit=False            # Ручное управление транзакциями (COMMIT / ROLLBACK)
    )

    if connection.is_connected():
        print("✅ Успешное подключение к серверу MySQL!")
        print(f"Версия сервера: {connection.get_server_info()}")

except Error as err:
    print(f"❌ Ошибка подключения: {err}")

finally:
    # Закрытие соединения после окончания работы
    if 'connection' in locals() and connection.is_connected():
        connection.close()
        print("🔌 Соединение с базой данных закрыто.")
```

---

## 3. Работа с курсорами (Cursor)

Все SQL-запросы в Python выполняются через специальный объект — **курсор** (`cursor`), который создается из объекта соединения:

```python
cursor = connection.cursor(dictionary=True)
```

### Виды курсоров и методы чтения:

* **`dictionary=False` (по умолчанию):** Возвращает строки в виде обычных кортежей: `(1, 'alex', 25)`. Доступ к полям только по индексам.
* **`dictionary=True` (рекомендуется):** Возвращает строки в виде удобных словарей Python: `{'id': 1, 'username': 'alex', 'age': 25}`. Доступ по именам столбцов.
* **`cursor.fetchone()`:** Извлекает ровно одну следующую строку из результата. Если строк больше нет — возвращает `None`.
* **`cursor.fetchall()`:** Извлекает сразу все строки в виде списка (`list`).
* **`cursor.fetchmany(size=10)`:** Извлекает порцию из указанного числа строк (для экономного расхода памяти).

---

## 4. Защита от SQL Injection: Параметризованные запросы

> **🛑 КРИТИЧЕСКИ ВАЖНОЕ ПРАВИЛО БЕЗОПАСНОСТИ:**  
> **НИКОГДА** не склеивайте SQL-запрос с пользовательскими переменными через конкатенацию `+`, оператор `%` или f-строки:

```python
# ❌ СМЕРТЕЛЬНО ОПАСНО (Уязвимость SQL-инъекции!):
user_input = "admin' OR '1'='1"
query = f"SELECT * FROM users WHERE username = '{user_input}'"
# Злоумышленник получит доступ без пароля или сотрет таблицу!
```

Вместо этого всегда используйте **параметризованные запросы (Prepared Statements)**. В них параметры передаются отдельно от текста SQL в виде второго аргумента (кортежа или списка):

```python
# ✅ АБСОЛЮТНО БЕЗОПАСНО:
query = "SELECT * FROM users WHERE username = %s AND is_active = %s"
params = ("alex_dev", True)

cursor.execute(query, params)
result = cursor.fetchall()
```

СУБД сначала компилирует структуру SQL-запроса, а затем безопасно подставляет значения параметров, полностью исключая возможность выполнения внедренного вредоносного кода.

---

## 5. Выполнение операций и фиксация транзакций

Для команд изменения данных (`INSERT`, `UPDATE`, `DELETE`) критически важно вызвать **`connection.commit()`**, чтобы зафиксировать изменения на диске:

```python
# 1. Вставка с получением сгенерированного ID
insert_sql = "INSERT INTO users (username, email) VALUES (%s, %s)"
cursor.execute(insert_sql, ("maria_k", "maria@example.com"))

connection.commit()  # Обязательно сохраняем изменения!
print(f"Добавлена запись с ID: {cursor.lastrowid}")

# 2. Пакетная вставка (Batch insert):
users_to_add = [
    ("ivan_tech", "ivan@test.ru"),
    ("sergey_pro", "sergey@test.ru"),
    ("anna_design", "anna@test.ru")
]
cursor.executemany(insert_sql, users_to_add)
connection.commit()
print(f"Добавлено записей: {cursor.rowcount}")

# 3. Обновление с проверкой числа измененных строк:
update_sql = "UPDATE users SET is_active = %s WHERE id = %s"
cursor.execute(update_sql, (False, 1))
connection.commit()
print(f"Обновлено строк: {cursor.rowcount}")
```

---

## 6. Демонстрационный скрипт (example.py)

В директории этого урока находится готовый к запуску файл [`example.py`](./example.py), демонстрирующий полный цикл взаимодействия с базой: инициализацию, создание таблиц, безопасный CRUD, транзакции с автоматическим откатом при ошибках и извлечение данных.

Для запуска скрипта:

```bash
python example.py
```

`Следующий материал:` [Лекция 6: Индексы, оптимизация запросов (EXPLAIN) и современные возможности (JSON)](../Lesson%206/lesson%206.md)
