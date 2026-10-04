# Практика по теме «Создание и изменение таблиц»

Эта практическая работа позволит вам закрепить знания, полученные в модуле. Она не влияет на прохождение курса и не требует проверки, но её выполнение поможет вам глубже понять материал.

## Как строится работа
1. Внимательно прочтите условия задания, перейдите в DBeaver и выполните работу.
2. Когда задание будет готово, вернитесь в этот материал и нажмите «Посмотреть решение», чтобы открыть подробный разбор решения от эксперта.
3. Сравните свой вариант решения с предлагаемым. Нажмите «Продолжить», чтобы открыть новое задание.

Рекомендуем сначала выполнить задания самостоятельно и только потом смотреть решение. Так вы сможете потренироваться и понять, каким моментам стоит уделить больше внимания.

## Цели практической работы

Научиться:

* создавать таблицы для базы данных, связанной с фильмами;
* устанавливать связи между таблицами;
* заполнять таблицы тестовыми данными.

## Задание 1

Создайте таблицу **«Жанры» (Genres)** с полями:

* id (int, Primary Key, Auto-increment);
* genre_name (varchar(50), NOT NULL).

<details>
<summary><b> Посмотреть решение</b></summary>

### Решение к заданию 1:

<img src="https://go.skillbox.ru/media/files/share/1_twsCDwH.jpg" width="70%" alt="Окно просмотра SQL">
<img src="https://go.skillbox.ru/media/files/share/2_zLgdEZU.png" width="70%" alt="Вкладка Свойства">
<img src="https://go.skillbox.ru/media/files/share/3_cSdGetX.jpg" width="70%" alt="Вкладка Данные">
<img src="https://go.skillbox.ru/media/files/share/4_huRQJTy.jpg" width="70%" alt="Вкладка Диаграмма">

</details>

## Задание 2

Создайте таблицу **«Актёры» (Actors)** с полями:

* id (int, Primary Key, Auto-increment);
* name (varchar(100), NOT NULL);
* birthdate (date, NOT NULL).

<details>
<summary><b> Посмотреть решение</b></summary>

### Решение к заданию 2:

<img src="https://go.skillbox.ru/media/files/share/5_%D0%BD%D0%BE%D0%B2.jpg" width="50%" alt="Окно просмотра SQL">
<img src="1.https://go.skillbox.ru/media/files/share/6_%D0%BD%D0%BE%D0%B2.jpg" width="50%" alt="Вкладка Свойства">
<img src="https://go.skillbox.ru/media/files/share/7_%D0%BD%D0%BE%D0%B2.jpg" width="50%" alt="Вкладка Данные">
<img src="https://go.skillbox.ru/media/files/share/8_%D0%BD%D0%BE%D0%B2.jpg" width="50%" alt="Вкладка Диаграмма">

</details>

## Задание 3

1. Создайте таблицу **«Фильмы» (Films)** с полями:

* d (int, Primary Key, Auto-increment);
* title (varchar(100), NOT NULL);
* release_year (int, NOT NULL);
* genre_id (int, NOT NULL, Foreign Key, ссылается на id в таблице «Жанры»).

2. Установите связь между таблицами. В таблице «Фильмы» добавьте внешний ключ для поля genre_id, который будет ссылаться на таблицу «Жанры».

<details>
<summary><b> Посмотреть решение</b></summary>

### Решение к заданию 3:

<img src="https://go.skillbox.ru/media/files/share/9_aJ09wm1.png" width="70%" alt="Окно просмотра SQL">
<img src="https://go.skillbox.ru/media/files/share/10_%D0%BD%D0%BE%D0%B2.jpg" width="70%" alt="Вкладка Свойства">
<img src="https://go.skillbox.ru/media/files/share/11_21U3Dd1.png" width="70%" alt="Вкладка Данные">
<img src="https://go.skillbox.ru/media/files/share/12_IAls7mZ.png" width="70%" alt="Вкладка Диаграмма">
<img src="https://go.skillbox.ru/media/files/share/13_6dGll0Z.png" width="70%" alt="Вкладка Свойства1">
<img src="https://go.skillbox.ru/media/files/share/14_GVdMyNn.png" width="70%" alt="Вкладка Данные2">
<img src="https://go.skillbox.ru/media/files/share/16_SRvtIBE.png" width="70%" alt="Вкладка Диаграмма3">

</details>

## Задание 4

1. Заполните таблицы тестовыми данными. В таблицу **«Жанры»** добавьте несколько жанров, такие как «Комедия», «Драма», «Ужасы».
2. В таблицу **«Актёры»** добавьте актёров с их именами и датами рождения:
* Том Хэнкс 1956-07-09
* Мерил Стрип 1949-06-22
3. В таблицу **«Фильмы»** добавьте фильмы, указав их названия, годы выпуска и соответствующие жанры:
* «Форрест Гамп» 1994 1
* «Список Шиндлера» 1993 2
* «Пункт назначения» 2000 3

<details>
<summary><b> Посмотреть решение</b></summary>

### Решение к заданию 4:

<img src="https://go.skillbox.ru/media/files/share/1738838762230.png" width="70%" alt="Окно просмотра SQL">
<img src="https://go.skillbox.ru/media/files/share/1738838776655.png" width="70%" alt="Вкладка Свойства">
<img src="https://go.skillbox.ru/media/files/share/1738838795246.png" width="70%" alt="Вкладка Данные">

</details>

## Задание 5

Проверьте, сохранились ли ваши данные. Для этого сделайте запросы по очереди:

```sql
SELECT * FROM genres;
```

```sql
SELECT * FROM actors;
```

```sql
SELECT * FROM films;
```

<details>
<summary><b> Посмотреть решение</b></summary>

### Решение к заданию 5:

<img src="https://go.skillbox.ru/media/files/share/1738838921664.png" width="70%" alt="Окно просмотра SQL">
<img src="https://go.skillbox.ru/media/files/share/1738838934527.png" width="70%" alt="Вкладка Свойства">
<img src="https://go.skillbox.ru/media/files/share/1738838944770.png" width="70%" alt="Вкладка Данные">

</details>

## Задание 6
Проверьте связь между таблицами «Фильмы» и «Жанры» с помощью запроса:

```sql
SELECT
    *
FROM
    Films
JOIN
    Genres ON Films.genre_id = genres.genre_id ;
```
<details>
<summary><b> Посмотреть решение</b></summary>

### Решение к заданию 6:

<img src="https://go.skillbox.ru/media/files/share/%D1%80%D0%B5%D1%88%D0%B5%D0%BD%D0%B8%D0%B5_%D0%BA_%D0%B7%D0%B0%D0%B4%D0%B0%D0%BD%D0%B8%D1%8E_6_4mIFzU9.jpg" width="70%" alt="Окно просмотра SQL">

Отлично! Вы успешно выполнили задания на самопроверку. А значит, вы не просто проходите материал, но и учитесь применять его вна практике. Продолжайте в том же духе — впереди вас ждёт ещё больше увлекательных тем. Они сделают вас настоящим мастером работы с базами данных!

</details>