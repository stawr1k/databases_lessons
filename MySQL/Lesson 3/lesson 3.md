# Лекция 3: Выборка и фильтрация данных: WHERE, сортировка, агрегатные функции и группировка (GROUP BY)

## 1. Введение: Логический порядок выполнения запроса (Query Lifecycle)

Когда мы пишем SQL-запрос, мы пишем его в синтаксическом порядке: `SELECT ... FROM ... WHERE ... GROUP BY ...`. Однако ядро MySQL исполняет операции в совершенно другом, **логическом порядке**:

```
1. FROM / JOIN     --> 1. СУБД определяет таблицы-источники
2. WHERE           --> 2. Фильтрует отдельные строки до группировки
3. GROUP BY        --> 3. Объединяет строки в группы
4. HAVING          --> 4. Фильтрует полученные группы по агрегатам
5. SELECT          --> 5. Вычисляет выражения, формирует столбцы и алиасы
6. DISTINCT        --> 6. Удаляет дубликаты строк
7. ORDER BY        --> 7. Сортирует итоговый результирующий набор
8. LIMIT / OFFSET  --> 8. Отсекает нужное количество строк
```

> **💡 Главное правило SQL:** Именно поэтому вы **не можете** использовать псевдоним (алиас), заданный в блоке `SELECT` (например, `SELECT price * 0.9 AS discount_price`), внутри блока `WHERE`! На этапе выполнения `WHERE` блок `SELECT` еще не отработал и имя `discount_price` серверу неизвестно.

---

## 2. Фильтрация данных (Предложение WHERE)

Предложение `WHERE` позволяет отбирать только те строки, которые удовлетворяют заданному логическому условию (возвращающему `TRUE`).

### Базовые операторы сравнения

```sql
-- Равенство и неравенство
SELECT * FROM products WHERE category = 'Электроника';
SELECT * FROM products WHERE status <> 'archived'; -- или !=

-- Сравнение чисел
SELECT * FROM products WHERE price > 5000.00;
SELECT * FROM users WHERE age <= 21;
```

### Логические операторы (AND, OR, NOT)

* **`AND`** — истинно, если оба условия выполняются.
* **`OR`** — истинно, если выполняется хотя бы одно условие.
* **`NOT`** — логическое отрицание.

```sql
-- Приоритет операций: AND выполняется раньше OR! 
-- Всегда используйте круглые скобки для группировки логики:
SELECT * FROM products 
WHERE (category = 'Смартфоны' OR category = 'Планшеты') 
  AND price < 30000 
  AND stock_quantity > 0;
```

### Специальные операторы фильтрации

#### 1. Диапазон значений (BETWEEN ... AND ...)
Проверяет вхождение значения в интервал (включая обе границы):

```sql
SELECT title, price FROM products 
WHERE price BETWEEN 1000 AND 5000;
-- Полный эквивалент: WHERE price >= 1000 AND price <= 5000
```

#### 2. Список значений (IN и NOT IN)
Проверяет совпадение с любым элементом из заданного списка:

```sql
SELECT * FROM users 
WHERE username IN ('alex', 'maria', 'dmitry');

SELECT * FROM products 
WHERE category NOT IN ('Уцененные', 'Архив');
```

#### 3. Поиск по шаблону (LIKE)
Оператор `LIKE` производит поиск по неполному совпадению строк с использованием специальных символов подстановки (Wildcards):
* `%` — любая последовательность из нуля или более символов.
* `_` — ровно один любой символ.

```sql
-- Поиск всех пользователей с почтой на Gmail
SELECT * FROM users WHERE email LIKE '%@gmail.com';

-- Поиск названий, начинающихся на "iPhone"
SELECT * FROM products WHERE title LIKE 'iPhone%';

-- Поиск четырехбуквенного кода, где вторая буква 'B' (например, 'AB12')
SELECT * FROM promo_codes WHERE code LIKE '_B__';
```

#### 4. Работа с неопределенными значениями (IS NULL / IS NOT NULL)

В реляционных базах данных `NULL` означает не ноль и не пустую строку, а **отсутствие значения (неизвестность)**. 

> **⚡️ Важно:** Сравнение `column = NULL` или `column != NULL` в SQL **всегда вернет FALSE**! Любая математическая операция с `NULL` дает `NULL`.

Для проверки на наличие или отсутствие значения всегда используются операторы `IS NULL` и `IS NOT NULL`:

```sql
-- Найти пользователей, у которых не указан номер телефона
SELECT * FROM users WHERE phone IS NULL;

-- Найти пользователей с заполненным телефоном
SELECT * FROM users WHERE phone IS NOT NULL;
```

---

## 3. Сортировка (ORDER BY) и пагинация (LIMIT / OFFSET)

### Сортировка (ORDER BY)

Сортировка определяет порядок возврата строк. По умолчанию используется направление по возрастанию (`ASC` — от А до Я, от меньшего к большему). Для обратного порядка указывается `DESC`.

```sql
-- Сортировка товаров по цене (от самых дорогих к дешевым)
SELECT id, title, price FROM products 
ORDER BY price DESC;

-- Многоуровневая сортировка: сначала по категории, а внутри категории — по названию
SELECT id, category, title, price FROM products 
ORDER BY category ASC, title ASC;
```

### Ограничение количества строк и пагинация (LIMIT, OFFSET)

* **`LIMIT N`** — возвращает максимум $N$ строк.
* **`OFFSET M`** — пропускает первые $M$ строк перед выдачей.

```sql
-- Топ-5 самых дорогих товаров
SELECT title, price FROM products 
ORDER BY price DESC 
LIMIT 5;

-- Постраничный вывод (Пагинация):
-- Страница 1 (товары с 1 по 10):
SELECT id, title, price FROM products ORDER BY id ASC LIMIT 10 OFFSET 0;

-- Страница 2 (товары с 11 по 20):
SELECT id, title, price FROM products ORDER BY id ASC LIMIT 10 OFFSET 10;

-- Страница 3 (товары с 21 по 30):
SELECT id, title, price FROM products ORDER BY id ASC LIMIT 10 OFFSET 20;
```

---

## 4. Устранение дубликатов (DISTINCT)

Ключевое слово `DISTINCT` отсекает повторяющиеся строки из результирующей выборки:

```sql
-- Получить уникальный список всех представленных в магазине категорий
SELECT DISTINCT category FROM products;

-- Уникальные комбинации города и страны
SELECT DISTINCT country, city FROM customers;
```

---

## 5. Агрегатные функции

Агрегатные функции выполняют математические вычисления над набором значений в столбце и возвращают **одно итоговое значение**.

| Функция | Описание | Пример |
| :--- | :--- | :--- |
| `COUNT(*)` | Подсчет общего количества строк | `SELECT COUNT(*) FROM users;` |
| `COUNT(колонка)` | Подсчет строк, где значение **не NULL** | `SELECT COUNT(phone) FROM users;` |
| `SUM(колонка)` | Вычисление суммы значений | `SELECT SUM(stock_quantity) FROM products;` |
| `AVG(колонка)` | Вычисление среднего арифметического | `SELECT AVG(price) FROM products;` |
| `MIN(колонка)` | Поиск минимального значения | `SELECT MIN(price) FROM products;` |
| `MAX(колонка)` | Поиск максимального значения | `SELECT MAX(price) FROM products;` |

```sql
-- Комплексный аналитический срез по каталогу:
SELECT 
    COUNT(*) AS total_products,
    MIN(price) AS cheapest_item,
    MAX(price) AS most_expensive_item,
    ROUND(AVG(price), 2) AS average_price,
    SUM(stock_quantity) AS total_items_in_stock
FROM products;
```

---

## 6. Группировка данных (GROUP BY) и фильтрация групп (HAVING)

Оператор `GROUP BY` объединяет строки с одинаковыми значениями в указанных колонках в группы. Затем к каждой группе применяется агрегатная функция.

### Базовый пример GROUP BY:

```sql
-- Подсчитать количество товаров и среднюю цену в разрезе каждой категории
SELECT 
    category,
    COUNT(*) AS products_count,
    ROUND(AVG(price), 2) AS avg_category_price
FROM products
GROUP BY category;
```

### Фильтрация групп: HAVING vs WHERE

Ключевое отличие:
* **`WHERE`** фильтрует **исходные строки** до того, как они попадут в группы. В нем нельзя использовать агрегатные функции (`WHERE COUNT(*) > 5` вызовет ошибку).
* **`HAVING`** фильтрует **уже сформированные группы** после применения агрегатных функций.

```sql
-- Найти категории, в которых представлено более 3 товаров, 
-- учитывая только товары с ценой выше 1000 руб:
SELECT 
    category,
    COUNT(*) AS total_items,
    AVG(price) AS avg_price
FROM products
WHERE price > 1000              -- Шаг 1: Фильтруем строки по цене
GROUP BY category               -- Шаг 2: Группируем подходящие строки
HAVING COUNT(*) > 3             -- Шаг 3: Оставляем только группы, где больше 3 товаров
ORDER BY total_items DESC;      -- Шаг 4: Сортируем результат
```

---

## 7. Полезные встроенные функции MySQL

### 1. Обработка NULL и условий
* **`COALESCE(v1, v2, ...)`** — возвращает первое значение из списка, не равное `NULL`:
  ```sql
  SELECT username, COALESCE(phone, 'Телефон не указан') AS contact_phone FROM users;
  ```
* **`CASE WHEN ... THEN ... ELSE ... END`** — условный оператор ветвления в SQL:
  ```sql
  SELECT title, price,
      CASE 
          WHEN price < 5000 THEN 'Бюджетный'
          WHEN price BETWEEN 5000 AND 30000 THEN 'Средний класс'
          ELSE 'Премиум'
      END AS price_segment
  FROM products;
  ```

### 2. Строковые функции
* `CONCAT(str1, str2, ...)` — конкатенация (склеивание) строк.
* `LOWER(str)` / `UPPER(str)` — приведение к нижнему/верхнему регистру.
* `LENGTH(str)` — длина строки в байтах, `CHAR_LENGTH(str)` — длина в символах.

### 3. Функции даты и времени
* `NOW()` — текущие дата и время.
* `CURDATE()` — текущая дата без времени.
* `DATEDIFF(date1, date2)` — разница между датами в днях.
* `DATE_ADD(date, INTERVAL 7 DAY)` — прибавление временного интервала.

`Следующий материал:` [Лекция 4: Связи между таблицами (JOIN), внешние ключи и транзакции (ACID)](../Lesson%204/lesson%204.md)
