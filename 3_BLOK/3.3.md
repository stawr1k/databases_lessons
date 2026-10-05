#  Практика по теме «Команды Create и Alter»

Это практическое задание поможет вам закрепить знания по теме «Команды Create и Alter». Его выполнение не влияет на прохождение курса и не требует отправки на проверку, но важно для более глубокого понимания материала.

## Как выстроена работа

1. Внимательно прочитайте условия задания, перейдите в DBeaver и выполните работу.
2. Когда закончите работу над заданием, вернитесь к этому материалу и нажмите кнопку «Посмотреть решение». Так вы откроете скрипт решения от эксперта.
3. Сравните свой вариант решения с предлагаемым, а затем нажмите кнопку «Продолжить», чтобы открыть новую задачу.

Рекомендуем сначала выполнить задания самостоятельно, а потом смотреть решение.

## Цели практической работы

- Создать таблицы для базы данных, связанной с фильмами.
- Добавить и изменить структуру таблиц с помощью SQL-команд CREATE TABLE и ALTER TABLE.
- Установить связи между таблицами.

Заполните таблицы тестовыми данными и проверьте связи.

---

# Задание 1. Создание базы данных

Создайте базу данных с именем Cinema, в ней будет храниться информация о кинотеатрах и фильмах. Убедитесь, что база данных создана с кодировкой UTF-8.

### Решение к заданию 1
<details>
<summary> Нажмите, чтоб посмотреть решение </summary>

```CREATE TABLE Cinemas (```<br>
    ```id SERIAL PRIMARY KEY,```<br>
    ```cinema_name VARCHAR(100)NOT NULL,```<br>
    ```location VARCHAR(100)NoT NULL,```<br>
   ``` capacity INT```<br>
);<br>

```CREATE TABLE Movies (```<br>
    ```id SERIAL PRIMARY KEY,```<br>
    ```title VARCHAR(100) NOT NULL,```<br>
    ```release_year INT NOT NULL,```<br>
    ```duration INT```<br>
);<br>
</details>

# Задание 2

## Создание базовых таблиц

Создайте подключение и сделайте несколько таблиц:

таблицу «Кинотеатры» (Cinemas) с полями:
id (INT, PRIMARY KEY, Auto-increment);<br>
cinema_name (VARCHAR(100), NOT NULL);<br>
location (VARCHAR(100), NOT NULL);<br>
capacity (INT) — вместимость зала;<br>
таблицу «Фильмы» (Movies) с полями:<br>
id (INT, PRIMARY KEY, Auto-increment);<br>
title (VARCHAR(100), NOT NULL);<br>
release_year (INT, NOT NULL);<br>
duration (INT) — продолжительность фильма в минутах.<br>
Примечание: в PostgreSQL вместо auto-increment используется обозначение SERIAL.<br>

<details>
<summary> Нажмите, чтоб посмотреть решение</summary>

1. Используйте скрипт создания таблицы «Кинотеатры» (Cinemas):

```CREATE TABLE Cinemas (```<br>
   ``` id SERIAL PRIMARY KEY,```<br>
   ``` cinema_name VARCHAR(100) NOT NULL,```<br>
    ```location VARCHAR(100) NOT NULL,```<br>
    ```capacity INT```<br>
);<br>

2. Используйте скрипт создания таблицы «Фильмы» (Movies):

```CREATE TABLE Movies (```<br>
    ```id SERIAL PRIMARY KEY,```<br>
    ```title VARCHAR(100) NOT NULL,```<br>
    ```release_year INT NOT NULL,```<br>
    ```duration INT```<br>
);<br>
</details>
