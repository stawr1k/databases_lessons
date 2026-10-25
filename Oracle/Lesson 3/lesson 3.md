# Лекция 3: Выборка и фильтрация данных: WHERE, сортировка, агрегатные функции и пагинация в Oracle

## 1. Логический порядок выполнения запроса (Query Lifecycle)

Как и во всех реляционных СУБД, синтаксический порядок написания запроса отличается от логического порядка, в котором ядро оптимизатора Oracle вычисляет операции:

```
1. FROM / JOIN           --> Определение источников и соединений
2. WHERE                 --> Фильтрация строк до агрегации
3. GROUP BY              --> Объединение строк в группы
4. HAVING                --> Фильтрация полученных групп
5. SELECT                --> Вычисление столбцов, скалярных функций и выражений
6. DISTINCT              --> Исключение дубликатов
7. ORDER BY              --> Физическая сортировка результирующего набора
8. OFFSET / FETCH NEXT   --> Ограничение порции выдачи (пагинация)
```

> **💡 Главное правило SQL:** Алиасы колонок, объявленные в секции `SELECT` (например, `SELECT price * 0.85 AS discount_price`), недоступны в секции `WHERE`, поскольку на момент фильтрации строк выражения `SELECT` еще не вычислены.

---

## 2. Фильтрация данных (Предложение WHERE)

### Базовые операторы сравнения и логики

```sql
-- Точное соответствие и неравенство (в Oracle поддерживаются оба оператора: != и <>)
SELECT * FROM products WHERE category_id = 1;
SELECT * FROM products WHERE status <> 'ARCHIVED';

-- Сравнение диапазонов (BETWEEN включает обе границы)
SELECT title, price FROM products WHERE price BETWEEN 10000 AND 50000;

-- Множественный выбор (IN и NOT IN)
SELECT title, price FROM products WHERE category_id IN (1, 2, 5);

-- Поиск по шаблону (LIKE)
-- % : любая последовательность символов
-- _ : ровно один любой символ
SELECT * FROM products WHERE title LIKE 'Ноутбук%';
```

### Продвинутый поиск: Регулярные выражения в Oracle

Oracle обладает одним из мощнейших в мире встроенных механизмов регулярных выражений по стандарту POSIX:

* **`REGEXP_LIKE(str, pattern)`** — проверка строки на соответствие регулярному выражению в `WHERE`.
* **`REGEXP_SUBSTR(str, pattern)`** — извлечение подстроки по регулярному выражению.
* **`REGEXP_REPLACE(str, pattern, replacement)`** — замена по регулярному выражению.

```sql
-- Найти пользователей с валидным форматом корпоративной почты:
SELECT username, email FROM users 
WHERE REGEXP_LIKE(email, '^[a-zA-Z0-9._%+-]+@company\.(ru|com)$');
```

---

## 3. Критически важная специфика Oracle: Пустые строки и значение NULL

В стандарте ANSI SQL пустая строка `''` (строка нулевой длины) и значение `NULL` (неопределенность) формально разделены. 

> **🛑 Фундаментальная особенность Oracle Database:**  
> В Oracle **пустая строка `''` всегда неявно конвертируется в `NULL`**!  
> Если вы выполните запрос:  
> `SELECT * FROM users WHERE phone = '';`  
> Oracle **не вернет ни одной строки**, так как сравнение с `NULL` через знак равенства всегда возвращает `UNKNOWN` (ложь)!

Для проверки на пустоту в Oracle всегда используются специальные операторы:
* **`IS NULL`** — проверка на отсутствие значения.
* **`IS NOT NULL`** — проверка на заполненность поля.

```sql
-- Правильная выборка пользователей без телефона:
SELECT username FROM users WHERE phone IS NULL;
```

### Функции обработки NULL в Oracle

| Функция | Описание | Пример |
| :--- | :--- | :--- |
| **`NVL(val, default)`** | Если `val IS NULL`, возвращает `default`. Фирменная функция Oracle. | `NVL(discount, 0)` |
| **`NVL2(val, if_not_null, if_null)`** | Тернарный оператор: если `val` заполнено — возвращает 2-й аргумент, иначе 3-й. | `NVL2(phone, 'Указан', 'Отсутствует')` |
| **`COALESCE(v1, v2, ...)`** | Возвращает первое значение из списка, не равное `NULL` (стандарт ANSI). | `COALESCE(mobile_phone, work_phone, 'Нет')` |
| **`NULLIF(a, b)`** | Возвращает `NULL`, если $a = b$, иначе возвращает $a$. | `NULLIF(stock_qty, 0)` |

---

## 4. Сортировка (ORDER BY) и управление позицией NULL

По умолчанию в Oracle сортировка выполняется по возрастанию (`ASC`).

### Поведение с NULL-значениями:
* При сортировке по возрастанию (`ASC`) значения `NULL` по умолчанию помещаются **в самый конец** (`NULLS LAST`).
* При сортировке по убыванию (`DESC`) значения `NULL` по умолчанию выводятся **первыми** (`NULLS FIRST`).

Для изменения этого поведения используется явное указание `NULLS FIRST` или `NULLS LAST`:

```sql
-- Вывести товары от дорогих к дешевым, но товары без цены поместить в самый конец:
SELECT title, price FROM products 
ORDER BY price DESC NULLS LAST;
```

---

## 5. Пагинация данных: Современный стандарт vs Устаревший ROWNUM

### Современный стандарт (Oracle 12c+ / 19c / 23ai)

Oracle полностью поддерживает стандартные конструкции ANSI SQL: **`OFFSET`** и **`FETCH NEXT ... ROWS ONLY`**:

```sql
-- Топ-5 самых дорогих товаров:
SELECT title, price FROM products 
ORDER BY price DESC 
FETCH FIRST 5 ROWS ONLY;

-- Постраничный вывод (Пагинация):
-- Пропустить первые 20 строк и вернуть следующие 10 (3-я страница):
SELECT id, title, price FROM products 
ORDER BY id ASC 
OFFSET 20 ROWS FETCH NEXT 10 ROWS ONLY;

-- Выборка с захватом дубликатов сортировки (WITH TIES):
SELECT title, price FROM products 
ORDER BY price DESC 
FETCH FIRST 3 ROWS WITH TIES;
```

### Историческая справка: Псевдоколонка ROWNUM

В старых версиях Oracle (до 12c) не было ключевого слова `LIMIT`. Разработчики использовали псевдоколонку `ROWNUM`, которая присваивает номер строке в момент считывания.  
Из-за того, что условие `WHERE ROWNUM > 10` всегда возвращает пустоту, пагинацию приходилось заворачивать в двойные подзапросы:

```sql
-- Старый громоздкий синтаксис (для понимания легаси-проектов):
SELECT * FROM (
    SELECT a.*, ROWNUM rnum FROM (
        SELECT id, title, price FROM products ORDER BY id
    ) a WHERE ROWNUM <= 30
) WHERE rnum > 20;
```
*(В новых проектах используйте исключительно современный синтаксис `OFFSET ... FETCH`).*

---

## 6. Агрегатные функции и группировка (GROUP BY / HAVING)

Агрегатные функции выполняют математические расчеты над набором строк и возвращают итоговое агрегированное значение:

```sql
SELECT 
    COUNT(*) AS total_items,
    ROUND(AVG(price), 2) AS average_price,
    MIN(price) AS min_price,
    MAX(price) AS max_price,
    SUM(stock_quantity) AS total_stock
FROM products;
```

### Группировка и фильтрация групп (HAVING):

```sql
-- Найти категории, в которых средняя цена товаров превышает 15 000 руб,
-- исключая товары с нулевым остатком на складе:
SELECT 
    category_id,
    COUNT(*) AS products_in_category,
    ROUND(AVG(price), 2) AS avg_price
FROM products
WHERE stock_quantity > 0          -- 1. Фильтруем строки до группировки
GROUP BY category_id              -- 2. Формируем группы по категориям
HAVING AVG(price) > 15000.00      -- 3. Фильтруем группы по значению агрегата
ORDER BY avg_price DESC;
```

### Фирменная функция агрегации Oracle: LISTAGG

Функция `LISTAGG` объединяет текстовые значения группы в единую строку через разделитель:

```sql
-- Вывести список названий товаров в каждой категории через запятую:
SELECT 
    category_id,
    LISTAGG(title, '; ') WITHIN GROUP (ORDER BY price DESC) AS catalog_items
FROM products
GROUP BY category_id;
```

---

## 7. Полезные встроенные скалярные функции Oracle

### 1. Преобразование типов (TO_CHAR, TO_DATE, TO_NUMBER)
Форматирование дат и чисел — одна из сильнейших сторон Oracle:

```sql
-- Преобразование даты в форматированную строку
SELECT TO_CHAR(SYSDATE, 'YYYY-MM-DD HH24:MI:SS') AS full_now FROM DUAL;

-- Парсинг строки в тип DATE
SELECT TO_DATE('2026-10-25', 'YYYY-MM-DD') FROM DUAL;

-- Форматирование денежных сумм с разделителями тысяч
SELECT TO_CHAR(1250000.50, '999,999,990.00') AS formatted_money FROM DUAL;
-- Результат: ' 1,250,000.50'
```

### 2. Ветвление логики: DECODE и CASE

* **`DECODE`** — компактная классическая функция Oracle (аналог `switch-case`):
  ```sql
  SELECT title, status,
         DECODE(status, 
                'ACTIVE', 'В продаже', 
                'OUT_OF_STOCK', 'Нет на складе', 
                'Неизвестно') AS status_desc
  FROM products;
  ```
* **`CASE`** — стандартное выражение ветвления:
  ```sql
  SELECT title, price,
      CASE 
          WHEN price < 10000 THEN 'Бюджетный сегмент'
          WHEN price BETWEEN 10000 AND 50000 THEN 'Средний сегмент'
          ELSE 'Премиум'
      END AS segment
  FROM products;
  ```

`Следующий материал:` [Лекция 4: Связи между таблицами (JOIN), внешние ключи, транзакции и уровни изоляции](../Lesson%204/lesson%204.md)
