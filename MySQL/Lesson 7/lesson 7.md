# Лекция 7: Практический проект на Python и MySQL

## 1. Введение и архитектура финального проекта

В заключительном уроке курса мы объединим все полученные знания в единый практический проект — **Сервис управления интернет-магазином и обработкой заказов (E-Commerce Order & Inventory Management System)**.

### Ключевые возможности и архитектурные решения:

1. **Пул соединений (Connection Pooling):**  
   В реальных высоконагруженных бэкенд-сервисах открытие нового TCP-соединения на каждый HTTP-запрос недопустимо из-за высоких накладных расходов. Мы используем класс `MySQLConnectionPool`, который держит готовые соединения в горячем резерве и автоматически переиспользует их.
2. **Строгая реляционная модель:**  
   Схема включает 5 взаимосвязанных таблиц (`users`, `categories`, `products`, `orders`, `order_items`) с внешними ключами (`FOREIGN KEY`) и каскадным контролем целостности.
3. **Транзакционное оформление заказов (ACID):**  
   Критическая бизнес-операция «Оформление заказа» выполняется строго внутри транзакции:
   * Проверка и блокировка остатков на складе (`FOR UPDATE`).
   * Проверка платежеспособности покупателя.
   * Синхронное списание остатков товара и баланса клиента.
   * Создание заказа и позиций в чеке.
   * В случае любой ошибки (нехватка товара на складе, сбой сети) вызывается автоматический откат (`ROLLBACK`), предотвращающий расхождение данных.
4. **Аналитические агрегации и отчетность:**  
   Формирование отчетов по выручке в разрезе категорий с помощью многотабличных `JOIN`, `GROUP BY` и агрегатных функций `SUM()` и `ROUND(AVG())`.
5. **Современные возможности:**  
   Хранение динамических характеристик товаров в нативном формате `JSON`.

---

## 2. Структура базы данных проекта

```
+----------------+          +----------------+
|   categories   |          |     users      |
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
| specs (JSON)   |                  |
+----------------+                  |
        | 1                         | N
        |                   +----------------+
        |                   |     orders     |
        |                   |----------------|
        |                   | id (PK)        |
        |                   | user_id (FK)   |
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
| price_at_purchase (фиксация цены покупки)  |
+--------------------------------------------+
```

---

## 3. Разбор ключевых функций проекта

### 1. Инициализация пула соединений

```python
from mysql.connector import pooling

db_pool = pooling.MySQLConnectionPool(
    pool_name="shop_pool",
    pool_size=5,             # Размер пула (одновременно до 5 активных коннектов)
    pool_reset_session=True, # Очистка сессионных переменных при возврате коннекта в пул
    host="localhost",
    user="root",
    password="rootpassword",
    database="ecommerce_db"
)
```

### 2. Безопасное проведение транзакции заказа

```python
def checkout_order(user_id: int, cart_items: list[dict]):
    conn = db_pool.get_connection()
    conn.autocommit = False  # Отключаем автокоммит для ручного управления транзакцией
    cursor = conn.cursor(dictionary=True)
    
    try:
        total_cost = 0.0
        
        # Шаг 1: Проверяем наличие всех товаров и блокируем строки
        for item in cart_items:
            cursor.execute("SELECT price, stock_quantity FROM products WHERE id = %s FOR UPDATE;", (item['product_id'],))
            product = cursor.fetchone()
            if not product or product['stock_quantity'] < item['quantity']:
                raise ValueError(f"Товар ID {item['product_id']} закончился на складе!")
            total_cost += float(product['price']) * item['quantity']

        # Шаг 2: Проверяем баланс покупателя
        cursor.execute("SELECT balance FROM users WHERE id = %s FOR UPDATE;", (user_id,))
        user = cursor.fetchone()
        if user['balance'] < total_cost:
            raise ValueError("Недостаточно средств на балансе покупателя!")

        # Шаг 3: Списываем средства и уменьшаем складские остатки
        cursor.execute("UPDATE users SET balance = balance - %s WHERE id = %s;", (total_cost, user_id))
        for item in cart_items:
            cursor.execute("UPDATE products SET stock_quantity = stock_quantity - %s WHERE id = %s;", 
                           (item['quantity'], item['product_id']))

        # Шаг 4: Создаем запись о заказе
        cursor.execute("INSERT INTO orders (user_id, total_amount, status) VALUES (%s, %s, 'PAID');", 
                       (user_id, total_cost))
        order_id = cursor.lastrowid

        # Шаг 5: Сохраняем позиции чека
        for item in cart_items:
            cursor.execute("""
                INSERT INTO order_items (order_id, product_id, quantity, price_at_purchase) 
                VALUES (%s, %s, %s, %s);
            """, (order_id, item['product_id'], item['quantity'], item['price']))

        # Успешная фиксация
        conn.commit()
        return order_id

    except Exception as err:
        conn.rollback()  # При ошибке возвращаем состояние базы в исходную точку
        raise err
    finally:
        cursor.close()
        conn.close()     # Соединение возвращается обратно в пул
```

---

## 4. Запуск практического приложения (app.py)

В директории этого урока находится полный исходный код проекта: [`app.py`](./app.py).

Скрипт содержит полноценный автоматический сценарий демонстрации:
1. Создание схемы базы данных с нуля и наполнение начальными справочниками.
2. Регистрация покупателей с пополнением персональных балансов.
3. Успешное оформление мультикатегорийного заказа с автоматическим пересчетом остатков на складе.
4. Попытка оформления заказа при нехватке товара (демонстрация безопасного отката `ROLLBACK`).
5. Генерация детализированного чека заказа с 4-сторонним `JOIN`.
6. Формирование управленческого финансового отчета по категориям с `GROUP BY` и `HAVING`.

Для запуска приложения:

```bash
python app.py
```

---

## 5. Заключение и дальнейшие шаги

Поздравляем с завершением курса по MySQL! Вы освоили фундамент реляционных баз данных:
* Принципы реляционной модели и архитектуру современного MySQL 8.x / InnoDB.
* Написание чистых запросов DDL и DML, выборку и фильтрацию данных любой сложности.
* Реляционные связи (`1:1`, `1:N`, `M:N`), объединения `INNER` и `LEFT JOIN`.
* Транзакции, уровни изоляции и принципы ACID.
* Безопасное подключение из Python без риска SQL-инъекций.
* Анализ производительности с помощью `EXPLAIN` и B-Tree индексы.
* Работу с пулами соединений и нативным форматом `JSON`.

Для дальнейшего развития рекомендуется изучить:
* Оконные функции SQL (`ROW_NUMBER()`, `RANK()`, `LEAD()`, `LAG()`).
* Обобщенные табличные выражения (CTE) и рекурсивные запросы `WITH RECURSIVE`.
* Использование ORM в Python (SQLAlchemy, Tortoise-ORM, Django ORM).
* Репликацию Master-Slave и шардинг баз данных для распределенных систем.
