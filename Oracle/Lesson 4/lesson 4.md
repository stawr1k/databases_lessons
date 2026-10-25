# Лекция 4: Связи между таблицами (JOIN), внешние ключи, транзакции и уровни изоляции

## 1. Реляционные связи и внешние ключи (FOREIGN KEY)

В реляционных базах данных разделение сущностей на отдельные таблицы устраняет дублирование информации и аномалии модификации. Целостность взаимосвязей обеспечивается механизмом **внешних ключей (Foreign Keys)**.

### Создание схемы со связями 1:N и M:N

Создадим схему интернет-магазина: клиенты (`users`), заказы (`orders`) и связующую таблицу позиций чека (`order_items`):

```sql
-- Таблица пользователей
CREATE TABLE users (
    id NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    username VARCHAR2(50) NOT NULL UNIQUE,
    email VARCHAR2(100) NOT NULL UNIQUE,
    balance NUMBER(12, 2) DEFAULT 0.00 NOT NULL CHECK (balance >= 0)
);

-- Таблица заказов (Связь 1:N с пользователем)
CREATE TABLE orders (
    id NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_id NUMBER NOT NULL,
    total_amount NUMBER(12, 2) DEFAULT 0.00 NOT NULL,
    status VARCHAR2(20) DEFAULT 'NEW' NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_orders_user 
        FOREIGN KEY (user_id) REFERENCES users(id)
        ON DELETE CASCADE
);

-- Таблица позиций заказа (Связь M:N между orders и products)
CREATE TABLE order_items (
    id NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    order_id NUMBER NOT NULL,
    product_id NUMBER NOT NULL,
    quantity NUMBER(6) NOT NULL CHECK (quantity > 0),
    price_at_purchase NUMBER(10, 2) NOT NULL,
    CONSTRAINT fk_items_order 
        FOREIGN KEY (order_id) REFERENCES orders(id)
        ON DELETE CASCADE,
    CONSTRAINT fk_items_product 
        FOREIGN KEY (product_id) REFERENCES products(id)
);
```

### Поведение внешних ключей при удалении (ON DELETE):

| Действие | Описание | Применение |
| :--- | :--- | :--- |
| **`NO ACTION`** *(по умолчанию)* | Запрещает удаление записи из родительской таблицы, пока существуют дочерние строки (ошибка `ORA-02292`). | Финансовые счета, договоры, аудит. |
| **`ON DELETE CASCADE`** | При удалении родителя (заказа) СУБД автоматически удаляет все зависимые дочерние записи (позиции заказа). | Дочерние строки чека, настройки профиля. |
| **`ON DELETE SET NULL`** | Поле внешнего ключа в дочерней таблице заменяется на `NULL` (столбец должен допускать `NULL`). | Назначенный курьер или менеджер. |

> **⚡️ Особенность Oracle:** В отличие от MySQL, в Oracle Database отсутствует конструкция `ON UPDATE CASCADE`. В философии Oracle первичные ключи всегда должны быть неизменяемыми суррогатными идентификаторами (`ID NUMBER IDENTITY`).

---

## 2. Объединение таблиц (Виды JOIN)

### Современный стандарт ANSI SQL (Рекомендуемый подход)

```
        A               B                 A               B
    +-------+       +-------+         +-------+-------+-------+
    |   A   |       |   B   |         |       |       |       |
    | only  | ( A ∩ B ) | only  |         |   A   | A ∩ B |       |
    |       |       |       |         |       |       |       |
    +-------+-------+-------+         +-------+-------+-------+
            INNER JOIN                         LEFT JOIN
```

#### 1. INNER JOIN (Внутреннее пересечение)
Возвращает только те строки, для которых найдено совпадение условий связи в обеих таблицах:

```sql
SELECT 
    o.id AS order_id,
    u.username AS customer,
    o.total_amount,
    o.status
FROM orders o
INNER JOIN users u ON o.user_id = u.id;
```

#### 2. LEFT JOIN (Левое внешнее объединение)
Возвращает **все строки из левой таблицы**, даже если у них нет связанных записей в правой. Если соответствие отсутствует, поля правой таблицы заполняются `NULL`:

```sql
-- Вывести всех клиентов и их заказы (включая тех, кто еще ничего не купил):
SELECT 
    u.username,
    u.email,
    COALESCE(o.total_amount, 0.00) AS spent_amount
FROM users u
LEFT JOIN orders o ON u.id = o.user_id;

-- Найти "спящих" клиентов, у которых нет ни одного заказа:
SELECT u.username, u.email
FROM users u
LEFT JOIN orders o ON u.id = o.user_id
WHERE o.id IS NULL;
```

#### 3. FULL OUTER JOIN в Oracle
В отличие от многих СУБД, Oracle **нативно** поддерживает полный `FULL OUTER JOIN`:

```sql
SELECT u.username, o.id AS order_id
FROM users u
FULL OUTER JOIN orders o ON u.id = o.user_id;
```

#### 4. Многотабличные объединения
Извлечение полной спецификации заказа с объединением 4 таблиц:

```sql
SELECT 
    o.id AS order_id,
    u.username,
    p.title AS item_name,
    oi.quantity,
    oi.price_at_purchase,
    (oi.quantity * oi.price_at_purchase) AS line_total
FROM orders o
INNER JOIN users u ON o.user_id = u.id
INNER JOIN order_items oi ON o.id = oi.order_id
INNER JOIN products p ON oi.product_id = p.id
WHERE o.id = 1;
```

---

### Историческая справка: Старый синтаксис со знаком плюс `(+)`

В старом коде Oracle можно встретить исторический синтаксис внешних объединений со знаком `(+)`:

```sql
-- Устаревший синтаксис Oracle (эквивалент LEFT JOIN):
SELECT u.username, o.total_amount
FROM users u, orders o
WHERE u.id = o.user_id(+);
```
*(Знак `(+)` ставится у той таблицы, где данных "не хватает" и нужно подставить NULL. В новом коде всегда используйте `LEFT JOIN` стандарта ANSI SQL).*

---

## 3. Транзакции в Oracle (TCL)

### Фундаментальное правило транзакций в Oracle

> **Важно:** В Oracle Database **любая DML-команда (`INSERT`, `UPDATE`, `DELETE`) автоматически открывает транзакцию**!  
> Вам не нужно писать `START TRANSACTION` или `BEGIN`. Но вы **обязаны явно зафиксировать изменения** командой `COMMIT` или отменить их через `ROLLBACK`.

```sql
-- Пример атомарного перевода 1000 руб со счета на счет:
UPDATE users SET balance = balance - 1000.00 WHERE id = 1 AND balance >= 1000.00;
UPDATE users SET balance = balance + 1000.00 WHERE id = 2;

-- Если обе операции прошли без ошибок:
COMMIT;

-- Если на каком-то этапе произошла ошибка:
-- ROLLBACK;
```

### Точки сохранения (SAVEPOINT)

Точки сохранения позволяют откатить часть транзакции, не отменяя выполненные ранее корректные действия:

```sql
INSERT INTO users (username, email) VALUES ('user1', 'u1@test.ru');
SAVEPOINT step_one;

INSERT INTO users (username, email) VALUES ('user2', 'u2@test.ru');
-- Откатываемся к точке step_one (пользователь user2 удален, user1 остался в транзакции):
ROLLBACK TO step_one;

COMMIT;
```

---

## 4. Модель многоверсионности (MVCC) и сегменты отката (Undo)

Oracle Database славится своей архитектурой многоверсионного управления параллельным доступом (**MVCC**):

* **Принцип непротиворечивого чтения (Read Consistency):**  
  Каждый выполняемый `SELECT` видит данные строго на момент начала своего выполнения (по системному счетчику изменений — **SCN** / System Change Number).
* **Читатели не ждут писателей:**  
  Если запрос начал строить сложный финансовый отчет на 1 миллион строк, а в этот момент параллельная транзакция меняет балансы и фиксирует изменения, читающий запрос **не блокируется**. Oracle на лету реконструирует старые версии измененных блоков данных из специального табличного пространства отката — **Undo Tablespace**!

### Легендарная ошибка ORA-01555: Snapshot too old

Если аналитический отчет выполняется слишком долго (например, 2 часа), а база данных интенсивно перезаписывает сегменты отката новыми транзакциями, старые блоки Undo могут быть вытеснены. В этом случае запрос падает с ошибкой:
`ORA-01555: snapshot too old: rollback segment number ... too small`.

**Как с этим бороться:**
1. Оптимизировать медленный SQL-запрос с помощью индексов, сократив время его выполнения.
2. Увеличить размер `UNDO TABLESPACE` и системный параметр `UNDO_RETENTION` (время хранения снимков отката в секундах).

---

## 5. Пессимистическая блокировка строк: SELECT ... FOR UPDATE

Чтобы защитить баланс или складской остаток от состояния гонки (Race Condition), когда два пользователя одновременно пытаются списать последние деньги или последний товар:

```sql
-- Блокируем строку товара для других транзакций до завершения нашей транзакции:
SELECT stock_quantity FROM products WHERE id = 10 FOR UPDATE;

-- Обновляем проверенный остаток:
UPDATE products SET stock_quantity = stock_quantity - 1 WHERE id = 10;

COMMIT;
```

### Опции NOWAIT и WAIT:

* **`FOR UPDATE NOWAIT`** — если строка уже заблокирована другой сессией, не ждать, а мгновенно вернуть ошибку `ORA-00054: resource busy and acquire with NOWAIT specified`.
* **`FOR UPDATE WAIT 5`** — ждать освобождения строки не более 5 секунд, после чего вернуть ошибку тайм-аута.

`Следующий материал:` [Лекция 5: Подключение и работа с Oracle Database на языке Python (python-oracledb)](../Lesson%205/lesson%205.md)
