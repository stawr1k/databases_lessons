# Лекция 2: Основы SQL в Oracle: Табличные пространства, типы данных, DDL и CRUD-операции

## 1. Концепция «Пользователь = Схема» (User is Schema)

В большинстве реляционных СУБД (например, PostgreSQL или MySQL) понятия базы данных, пользователя и схемы разделены: один пользователь может подключаться к разным базам, а внутри базы создавать десятки разных схем.

В **Oracle Database** действует фундаментальное правило: **Пользователь (User) и Схема (Schema) — это одно и то же**:
* Создавая учетную запись пользователя `shop_admin`, СУБД автоматически создает одноименную схему `SHOP_ADMIN`.
* Все таблицы, индексы, процедуры и представления, созданные этим пользователем, принадлежат его личной схеме.
* Обращение к объектам своего пользователя происходит напрямую (`SELECT * FROM products`), а к объектам другого пользователя — через префикс схемы (`SELECT * FROM other_user.products`), при условии наличия выданных прав (`GRANT SELECT`).

### Создание прикладного пользователя и назначение прав

Перед началом работы создадим отдельного пользователя для нашего проекта внутри подключаемой базы данных (`FREEPDB1`):

```sql
-- 1. Переключаемся в нашу прикладную базу PDB
ALTER SESSION SET CONTAINER = FREEPDB1;

-- 2. Создаем пользователя схемы
CREATE USER dev_user IDENTIFIED BY StrongPassword123!
    DEFAULT TABLESPACE USERS
    QUOTA UNLIMITED ON USERS;

-- 3. Выдаем базовые системные привилегии
-- CONNECT: право на установку сессии
-- RESOURCE: право на создание таблиц, индексов, триггеров и процедур
GRANT CONNECT, RESOURCE TO dev_user;

-- В Oracle 12c+ также требуется явно разрешить создание представлений
GRANT CREATE VIEW TO dev_user;
```

---

## 2. Типы данных в Oracle Database

Oracle обладает собственной специализированной системой типов данных, оптимизированной для высокой точности вычислений и экономии дискового пространства.

| Категория | Тип данных | Размер | Описание и назначение |
| :--- | :--- | :--- | :--- |
| **Числа** | `NUMBER(p, s)` | До 22 байт | **Универсальный числовой тип Oracle**. Заменяет `INT`, `BIGINT`, `DECIMAL`.<br>• `p` (precision) — общее число цифр (до 38).<br>• `s` (scale) — число знаков после запятой.<br>Примеры: `NUMBER(10)` для целых ID, `NUMBER(12, 2)` для денег. |
| **Строки** | `VARCHAR2(N)` | До 4000 байт *(до 32 767 при MAX_STRING_SIZE=EXTENDED)* | Строка переменной длины. **Всегда используйте `VARCHAR2`**, а не `VARCHAR`. |
| | `CHAR(N)` | До 2000 байт | Строка строго фиксированной длины. Если передан текст короче $N$, остаток дополняется пробелами. |
| | `CLOB` | До 4 ГБ | *Character Large Object* — огромные тексты, логи, статьи, markdown-документы. |
| **Дата и время** | `DATE` | 7 байт | **Хранит и дату, и время** (год, месяц, день, часы, минуты, секунды). |
| | `TIMESTAMP` | До 11 байт | Дата и время с точностью до долей секунд (микросекунды, по умолчанию 6 знаков). |
| | `TIMESTAMP WITH TIME ZONE` | 13 байт | Дата и время с явным смещением часового пояса (UTC/регион). |
| **Логический** | `BOOLEAN` | 1 байт | Появился нативно в **Oracle 23ai** (`TRUE` / `FALSE`). Для старых версий (19c/21c) используется `NUMBER(1)` с проверкой `CHECK (col IN (0, 1))`. |
| **Бинарные** | `BLOB` | До 4 ГБ | *Binary Large Object* — изображения, PDF-файлы, аудио, бинарные архивы. |
| | `RAW(N)` | До 2000 байт | Сырые байтовые последовательности (хеши SHA-256, токены, UUID). |

> **💡 Почему именно `VARCHAR2`, а не `VARCHAR`?**  
> В стандарте ANSI SQL тип `VARCHAR` теоретически может интерпретировать пустые строки иначе в будущем. Компания Oracle ввела тип `VARCHAR2`, чтобы зафиксировать собственное гарантированное поведение: в Oracle любая пустая строка `''` приравнивается к значению `NULL`. Все разработчики Oracle обязаны использовать тип `VARCHAR2`.

---

## 3. Ограничения целостности (Constraints)

Ограничения предотвращают сохранение некорректных данных на уровне ядра СУБД:

* **`PRIMARY KEY`:** Первичный ключ таблицы. Обеспечивает уникальность строк и автоматически создает уникальный B-Tree индекс.
* **`NOT NULL`:** Запрещает сохранение значений `NULL`.
* **`UNIQUE`:** Гарантирует уникальность значений в пределах колонки (например, уникальный `email`).
* **`DEFAULT <значение>`:** Подставляет значение по умолчанию, если оно не было передано в `INSERT` (например, `DEFAULT SYSDATE`).
* **`CHECK (условие)`:** Логическая валидация значений при вставке и изменении (например, `CHECK (price > 0)`).

---

## 4. Создание таблиц (DDL) и генерация первичных ключей

### Современный способ (Oracle 12c+ / 19c / 23ai): Столбцы Identity

В современном Oracle для автоматической генерации целочисленных первичных ключей (аналог `AUTO_INCREMENT` или `SERIAL`) используется декларативная конструкция **`GENERATED ALWAYS AS IDENTITY`**:

```sql
-- Таблица категорий
CREATE TABLE categories (
    id NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name VARCHAR2(100) NOT NULL UNIQUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Таблица товаров
CREATE TABLE products (
    id NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    category_id NUMBER NOT NULL,
    title VARCHAR2(150) NOT NULL,
    price NUMBER(10, 2) NOT NULL CHECK (price >= 0),
    stock_quantity NUMBER(6) DEFAULT 0 NOT NULL CHECK (stock_quantity >= 0),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_products_category 
        FOREIGN KEY (category_id) REFERENCES categories(id)
);
```

### Классический способ: Последовательности (SEQUENCE)

В старых версиях (Oracle 11g и ранее) генераторы создавались отдельно в виде объектов последовательностей (**SEQUENCE**):

```sql
CREATE SEQUENCE users_seq START WITH 1 INCREMENT BY 1 NOCACHE;

-- Использование при вставке:
-- INSERT INTO users (id, username) VALUES (users_seq.NEXTVAL, 'alex');
```

### Просмотр и изменение структуры объектов (ALTER / DROP)

```sql
-- Добавление нового столбца
ALTER TABLE products ADD (sku VARCHAR2(50) NULL);

-- Изменение размерности столбца
ALTER TABLE products MODIFY (title VARCHAR2(200));

-- Удаление столбца
ALTER TABLE products DROP COLUMN sku;

-- Просмотр структуры таблицы в SQL*Plus / SQLcl:
DESC products;
```

> **⚠️ КРИТИЧЕСКИ ВАЖНО: Неявный COMMIT в операциях DDL!**  
> В Oracle **любая DDL-команда** (`CREATE`, `ALTER`, `DROP`, `TRUNCATE`) выполняет **автоматический неявный COMMIT** до и после своего выполнения.  
> Если вы открыли транзакцию, изменили несколько строк через `UPDATE`, а затем выполнили команду `CREATE TABLE ...`, все ваши предыдущие изменения будут **зафиксированы намертво**, и выполнить `ROLLBACK` для них будет уже невозможно!

---

## 5. Манипуляция данными (DML / CRUD)

### 1. Create: Вставка данных (INSERT INTO)

#### Одиночная вставка:

```sql
INSERT INTO categories (name) VALUES ('Электроника');
INSERT INTO categories (name) VALUES ('Бытовая техника');

INSERT INTO products (category_id, title, price, stock_quantity)
VALUES (1, 'Ноутбук Pro 15', 85000.00, 7);

-- Не забываем подтвердить транзакцию в Oracle!
COMMIT;
```

#### Пакетная вставка нескольких строк (INSERT ALL):

В отличие от MySQL, где пишется `VALUES (...), (...)`, в классическом SQL Oracle используется конструкция `INSERT ALL`:

```sql
INSERT ALL
    INTO categories (name) VALUES ('Книги')
    INTO categories (name) VALUES ('Спорт и отдых')
    INTO categories (name) VALUES ('Одежда')
SELECT * FROM DUAL;

COMMIT;
```

---

### 2. Read: Чтение данных и специальная таблица DUAL

Таблица **`DUAL`** — легендарная встроенная таблица Oracle, состоящая ровно из одной строки и одного столбца. Она используется для вычисления системных выражений, функций и дат, когда реальная таблица не требуется:

```sql
-- Получение текущей даты и времени сервера
SELECT SYSDATE FROM DUAL;

-- Вычисление математических выражений
SELECT (150 * 1.20) AS price_with_vat FROM DUAL;

-- Чтение из реальной таблицы
SELECT id, title, price FROM products WHERE price > 50000;
```

*(Начиная с Oracle 23ai, указание `FROM DUAL` стало необязательным, однако знание `DUAL` необходимо при чтении существующего кода).*

---

### 3. Update: Изменение данных

```sql
UPDATE products 
SET price = price * 1.05,
    stock_quantity = stock_quantity + 10
WHERE id = 1;

COMMIT;
```

---

### 4. Delete и Truncate: Удаление строк

* **`DELETE FROM products WHERE id = 1;`** — удаляет указанные строки, записывая данные в сегменты отката (Undo), что позволяет отменить операцию через `ROLLBACK`.
* **`TRUNCATE TABLE products;`** — мгновенно освобождает экстенты таблицы на диске и сбрасывает счетчик IDENTITY (является DDL-командой, отменить нельзя!).

---

### 5. Операция MERGE INTO (Фирменный UPSERT в Oracle)

Команда **`MERGE`** атомарно проверяет наличие записи по условию: если запись найдена — обновляет её (`UPDATE`), а если отсутствует — создает новую (`INSERT`):

```sql
MERGE INTO products p
USING (SELECT 1 AS cat_id, 'Ноутбук Pro 15' AS title, 89990.00 AS new_price FROM DUAL) src
ON (p.title = src.title)
WHEN MATCHED THEN
    UPDATE SET p.price = src.new_price
WHEN NOT MATCHED THEN
    INSERT (category_id, title, price, stock_quantity)
    VALUES (src.cat_id, src.title, src.new_price, 5);

COMMIT;
```

`Следующий материал:` [Лекция 3: Выборка и фильтрация данных: WHERE, сортировка, агрегатные функции и пагинация в Oracle](../Lesson%203/lesson%203.md)
