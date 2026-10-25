# Лекция 6: Индексы, анализ плана выполнения (EXPLAIN PLAN) и основы PL/SQL

## 1. Архитектура индексов в Oracle Database

В высоконагруженных промышленных базах данных с миллионами записей неоптимизированные запросы приводят к **Full Table Scan (Полному сканированию таблицы)**: сервер последовательно считывает каждый блок таблицы с диска в оперативную память, создавая колоссальную нагрузку на дисковую подсистему (I/O).

Для мгновенного доступа к данным Oracle предоставляет разнообразные типы индексов.

### 1. B-Tree индексы (Сбалансированное дерево)
Стандартный и наиболее универсальный тип индекса. Листья дерева содержат отсортированное значение ключа и физический адрес строки на диске — **ROWID**.
* **Сложность поиска:** $O(\log N)$.
* **Применение:** Колонки с высокой кардинальностью (уникальные или редко повторяющиеся значения: `id`, `email`, `created_at`).

```sql
-- Создание стандартного B-Tree индекса:
CREATE INDEX idx_users_email ON users(email);

-- Составной индекс по нескольким колонкам:
CREATE INDEX idx_orders_user_status ON orders(user_id, status);
```

### 2. Bitmap-индексы (Битовые карты)
Эксклюзивная технология Oracle Database, незаменимая в аналитических хранилищах (Data Warehouse):
* Вместо списка ROWID индекс хранит компактные битовые маски (0 и 1) для каждого уникального значения.
* Логические условия (`AND`, `OR`, `NOT`) выполняются напрямую над битовыми векторами со скоростью процессора.
* **Применение:** Поля с низкой кардинальностью (статус заказа: `NEW`, `PAID`, `CANCELLED`; пол; тип аккаунта).

```sql
-- Создание Bitmap-индекса:
CREATE BITMAP INDEX bmp_orders_status ON orders(status);
```
*(Предостережение: Bitmap-индексы не рекомендуется использовать в OLTP-системах с частыми параллельными обновлениями, так как блокировка накладывается сразу на фрагмент битовой карты).*

### 3. Функциональные индексы (Function-Based Indexes)
Если колонка в условии `WHERE` оборачивается в функцию (например, регистронезависимый поиск `UPPER(email)`), обычный индекс перестает работать. Функциональный индекс сохраняет уже вычисленный результат функции:

```sql
-- Индекс по вычисленному выражению:
CREATE INDEX idx_users_upper_email ON users(UPPER(email));

-- Теперь этот запрос выполнится мгновенно через Index Scan:
SELECT * FROM users WHERE UPPER(email) = 'ALICE@ORACLE.COM';
```

---

## 2. Анализ плана выполнения: EXPLAIN PLAN и DBMS_XPLAN

Оптимизатор Oracle (Cost-Based Optimizer — CBO) рассчитывает стоимость выполнения запроса (*Cost*) на основе статистики таблиц. Чтобы увидеть, какой путь выбрал сервер, используется команда **`EXPLAIN PLAN FOR`**:

```sql
-- 1. Рассчитываем план для запроса
EXPLAIN PLAN FOR 
SELECT * FROM users WHERE email = 'alice@oracle.com';

-- 2. Выводим отформатированный отчет с помощью системного пакета DBMS_XPLAN
SELECT * FROM TABLE(DBMS_XPLAN.DISPLAY());
```

### Пример вывода плана:

```
-----------------------------------------------------------------------------------------------
| Id  | Operation                   | Name            | Rows  | Bytes | Cost (%CPU)| Time     |
-----------------------------------------------------------------------------------------------
|   0 | SELECT STATEMENT            |                 |     1 |    45 |     2   (0)| 00:00:01 |
|   1 |  TABLE ACCESS BY INDEX ROWID| USERS           |     1 |    45 |     2   (0)| 00:00:01 |
|*  2 |   INDEX UNIQUE SCAN         | IDX_USERS_EMAIL |     1 |       |     1   (0)| 00:00:01 |
-----------------------------------------------------------------------------------------------
Predicate Information (identified by operation id):
---------------------------------------------------
   2 - access("EMAIL"='alice@oracle.com')
```

### Ключевые операции в плане:

* **`INDEX UNIQUE SCAN`:** Идеально. Считывание единственного листа уникального индекса.
* **`INDEX RANGE SCAN`:** Поиск диапазона значений по неуникальному индексу.
* **`TABLE ACCESS BY INDEX ROWID`:** Извлечение колонок из самой таблицы по адресам строк, полученным из индекса.
* **`TABLE ACCESS FULL`:** Полное сканирование таблицы. Если таблица большая — это главный признак необходимости добавления индекса.

---

## 3. Введение в PL/SQL (Procedural Language for SQL)

**PL/SQL** — встроенный язык процедурного программирования Oracle. В отличие от отправки отдельных SQL-запросов из клиентского приложения, код PL/SQL компилируется и исполняется **непосредственно внутри ядра базы данных**, что снижает нагрузку на сеть до нуля.

### 1. Структура анонимного блока PL/SQL:

```sql
DECLARE
    -- Секция объявления локальных переменных
    v_username VARCHAR2(50);
    v_balance  NUMBER(12, 2);
BEGIN
    -- Исполняемая секция
    SELECT username, balance 
    INTO v_username, v_balance 
    FROM users 
    WHERE id = 1;

    DBMS_OUTPUT.PUT_LINE('Клиент: ' || v_username || ' | Баланс: ' || v_balance);

EXCEPTION
    -- Секция перехвата исключений
    WHEN NO_DATA_FOUND THEN
        DBMS_OUTPUT.PUT_LINE('Пользователь с указанным ID не найден.');
    WHEN OTHERS THEN
        DBMS_OUTPUT.PUT_LINE('Произошла непредвиденная ошибка: ' || SQLERRM);
END;
/
```

### 2. Хранимые процедуры (PROCEDURE) и параметры OUT

Хранимые процедуры инкапсулируют бизнес-логику в базе данных. Они могут принимать входные параметры (`IN`) и возвращать результаты через выходные параметры (`OUT`):

```sql
CREATE OR REPLACE PROCEDURE topup_balance (
    p_user_id   IN  NUMBER,
    p_amount    IN  NUMBER,
    p_new_bal   OUT NUMBER
) AS
BEGIN
    -- Проверяем сумму
    IF p_amount <= 0 THEN
        RAISE_APPLICATION_ERROR(-20001, 'Сумма пополнения должна быть больше нуля!');
    END IF;

    -- Обновляем баланс и возвращаем новое значение через RETURNING INTO
    UPDATE users 
    SET balance = balance + p_amount 
    WHERE id = p_user_id
    RETURNING balance INTO p_new_bal;

    COMMIT;
END topup_balance;
/
```

---

## 4. Вызов процедур PL/SQL из Python

Библиотека `python-oracledb` предоставляет специализированный метод **`cursor.callproc()`** для бесшовного вызова хранимых процедур:

```python
import oracledb

connection = oracledb.connect(user="dev_user", password="pass", dsn="localhost:1521/FREEPDB1")
cursor = connection.cursor()

# Создаем переменную Python для приема выходного значения OUT из Oracle
new_balance_var = cursor.var(oracledb.NUMBER)

# Вызываем процедуру topup_balance(p_user_id, p_amount, p_new_bal)
cursor.callproc("topup_balance", [1, 500.00, new_balance_var])

# Считываем результат
updated_balance = new_balance_var.getvalue()
print(f"Баланс успешно пополнен. Новое значение: {updated_balance:.2f} руб.")
```

---

## 5. Демонстрационный скрипт (example.py)

В директории этого урока находится файл [`example.py`](./example.py). Он наглядно демонстрирует:
1. Заполнение таблицы на 10 000 строк.
2. Реальный замер времени выборки **без индекса** и **с B-Tree индексом** (с расчетом коэффициента ускорения).
3. Создание хранимой процедуры PL/SQL прямо из Python и её вызов через `cursor.callproc()`.

Запуск примера:

```bash
python example.py
```

`Следующий материал:` [Лекция 7: Практический проект на Python и Oracle: Корпоративная система управления заказами](../Lesson%207/lesson%207.md)
