# Лекция 7: Практический проект на Python и Oracle: Корпоративная система управления заказами

## 1. Введение и архитектура корпоративного проекта

В финальном уроке курса мы объединим все изученные возможности Oracle Database и Python в единый проект — **Корпоративную систему управления складскими остатками и заказами (Enterprise Order & Inventory Management System)**.

### Архитектурные требования промышленного уровня:

1. **Пул сессий (Session Pool):**  
   В Oracle выделение серверного процесса (Server Process) и инициализация сессии на каждый отдельный запрос — крайне ресурсоемкая операция. В продакшен-сервисах всегда используется пул сессий: **`oracledb.create_pool()`**. Пул держит готовые горячие подключения, мгновенно распределяя их между входящими задачами.
2. **Многоверсионная реляционная модель:**  
   Схема включает 5 взаимосвязанных таблиц (`categories`, `customers`, `products`, `orders`, `order_items`) с ограничениями первичных и внешних ключей (`IDENTITY`, `FOREIGN KEY ON DELETE CASCADE`).
3. **Строгая транзакционная бизнес-логика (ACID):**  
   Оформление заказа выполняется в рамках атомарной транзакции:
   * Проверка и превентивная блокировка строк товаров от гонки: `SELECT ... FOR UPDATE`.
   * Блокировка баланса клиента.
   * Синхронное списание остатков и денежных средств.
   * Создание заказа и строк чека.
   * Фиксация (`COMMIT`) при успехе или автоматический откат (`ROLLBACK`) при нехватке товара или денег.
4. **Аналитические агрегации и чеки:**  
   Формирование детализированного кассового чека через многотабличный `INNER JOIN` и построение финансового отчета выручки по категориям через `GROUP BY`, `SUM()`, `AVG()` и `HAVING`.

---

## 2. Диаграмма связей базы данных проекта

```
+----------------+          +----------------+
|   categories   |          |   customers    |
|----------------|          |----------------|
| id (PK)        |          | id (PK)        |
| name           |          | username       |
+----------------+          | email          |
        | 1                 | balance        |
        |                   +----------------+
        | N                         | 1
+----------------+                  |
|    products    |                  |
|----------------|                  |
| id (PK)        |                  |
| category_id(FK)|                  |
| title          |                  |
| price          |                  |
| stock_quantity |                  |
+----------------+                  |
        | 1                         | N
        |                   +----------------+
        |                   |     orders     |
        |                   |----------------|
        |                   | id (PK)        |
        |                   | customer_id(FK)|
        |                   | total_amount   |
        |                   | status         |
        |                   +----------------+
        |                           | 1
        | N                         | N
+--------------------------------------------+
|                order_items                 |
|--------------------------------------------|
| id (PK)                                    |
| order_id (FK)                              |
| product_id (FK)                            |
| quantity                                   |
| price_at_purchase                          |
+--------------------------------------------+
```

---

## 3. Разбор ключевых компонентов проекта

### 1. Создание пула сессий Oracle

```python
import oracledb

# Инициализация пула сессий в Thin Mode
pool = oracledb.create_pool(
    user="dev_user",
    password="StrongPassword123!",
    dsn="localhost:1521/FREEPDB1",
    min=2,             # Минимальное число готовых сессий
    max=10,            # Максимальный размер пула
    increment=1        # Шаг расширения пула при пиковой нагрузке
)

# Получение соединения из пула:
with pool.acquire() as connection:
    cursor = connection.cursor()
    cursor.execute("SELECT SYSDATE FROM DUAL")
    print(cursor.fetchone())
```

### 2. Транзакционное оформление заказа с блокировками

```python
def checkout_order(customer_id: int, cart_items: list[dict]):
    with pool.acquire() as conn:
        cursor = conn.cursor()
        try:
            total_cost = 0.0
            
            # Шаг 1: Проверяем наличие товаров и блокируем строки от параллельных покупок
            for item in cart_items:
                cursor.execute("""
                    SELECT price, stock_quantity 
                    FROM products 
                    WHERE id = :p_id 
                    FOR UPDATE WAIT 3
                """, {"p_id": item["product_id"]})
                
                row = cursor.fetchone()
                if not row or row[1] < item["quantity"]:
                    raise ValueError(f"Товар ID {item['product_id']} закончился на складе!")
                
                total_cost += float(row[0]) * item["quantity"]

            # Шаг 2: Проверяем баланс покупателя с блокировкой
            cursor.execute("""
                SELECT balance FROM customers WHERE id = :c_id FOR UPDATE WAIT 3
            """, {"c_id": customer_id})
            cust = cursor.fetchone()
            
            if not cust or float(cust[0]) < total_cost:
                raise ValueError("Недостаточно средств на балансе клиента!")

            # Шаг 3: Списываем средства и уменьшаем складские остатки
            cursor.execute("""
                UPDATE customers SET balance = balance - :cost WHERE id = :c_id
            """, {"cost": total_cost, "c_id": customer_id})

            for item in cart_items:
                cursor.execute("""
                    UPDATE products SET stock_quantity = stock_quantity - :qty WHERE id = :p_id
                """, {"qty": item["quantity"], "p_id": item["product_id"]})

            # Шаг 4: Создаем заказ и получаем сгенерированный ID через RETURNING INTO
            order_id_var = cursor.var(oracledb.NUMBER)
            cursor.execute("""
                INSERT INTO orders (customer_id, total_amount, status) 
                VALUES (:cid, :tot, 'PAID') 
                RETURNING id INTO :out_id
            """, {"cid": customer_id, "tot": total_cost, "out_id": order_id_var})
            
            order_id = int(order_id_var.getvalue()[0])

            # Шаг 5: Записываем позиции заказа
            for item in cart_items:
                cursor.execute("""
                    INSERT INTO order_items (order_id, product_id, quantity, price_at_purchase)
                    VALUES (:oid, :pid, :qty, :prc)
                """, {"oid": order_id, "pid": item["product_id"], "qty": item["quantity"], "prc": item["price"]})

            # Шаг 6: Фиксируем транзакцию
            conn.commit()
            return order_id

        except Exception as err:
            conn.rollback()  # Атомарный откат всей транзакции при ошибке
            raise err
```

---

## 4. Запуск практического приложения (app.py)

В директории этого урока находится полный исполняемый код: [`app.py`](./app.py).

Программа включает автоматизированный демонстрационный сценарий:
1. Инициализация пула сессий Oracle.
2. Очистка и развертывание схемы из 5 взаимосвязанных таблиц.
3. Наполнение начальным справочником категорий и товаров.
4. Регистрация клиентов и пополнение их лицевых счетов.
5. Успешное оформление мультикатегорийного заказа со списанием остатков.
6. Формирование детализированного кассового чека через 4-сторонний `INNER JOIN`.
7. Попытка оформления заказа при нехватке товара (демонстрация безопасного отката `ROLLBACK`).
8. Попытка покупки при недостаточном балансе (демонстрация отката `ROLLBACK`).
9. Построение сводной управленческой аналитики продаж по категориям (`GROUP BY`, `HAVING`).

Запуск приложения:

```bash
python app.py
```

---

## 5. Заключение и дальнейшие шаги

Поздравляем с освоением курса по Oracle Database! Вы изучили фундамент работы с самой мощной корпоративной СУБД:
* Архитектуру инстанса Oracle (SGA, PGA, фоновые процессы) и контейнеров CDB/PDB.
* Создание пользователей, схем, управление табличными пространствами и типы данных (`NUMBER`, `VARCHAR2`, `DATE`, `CLOB`).
* Современные стандарты SQL: столбцы `IDENTITY`, пагинацию `OFFSET ... FETCH`, слияние `MERGE INTO`.
* Анализ планов выполнения (`EXPLAIN PLAN`, `DBMS_XPLAN`) и индексацию B-Tree.
* Модель многоверсионности MVCC, сегменты отката Undo и транзакции ACID.
* Разработку на Python через драйвер нового поколения `python-oracledb` в Thin Mode.
* Процедурный язык PL/SQL и пулы сессий.

### Рекомендуемые темы для углубленного изучения:
* **Пакеты PL/SQL (Packages):** Инкапсуляция процедур, функций и типов данных в переиспользуемые модули.
* **Аналитические оконные функции:** `ROW_NUMBER()`, `DENSE_RANK()`, `LEAD()`, `LAG()` для финансового анализа.
* **JSON-реляционная дуальность (Oracle 23ai):** Работа с одними и теми же данными и как с реляционными таблицами, и как с документами JSON без дублирования.
* **Векторный поиск (AI Vector Search):** Хранение векторных эмбеддингов и семантический поиск по документам прямо в базе данных.
