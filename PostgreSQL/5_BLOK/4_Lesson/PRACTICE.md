 # Практика по теме «Использование транзакций»
Это практическое задание поможет вам закрепить знания по теме «Использование транзакций». Его выполнение не влияет на прохождение курса и не требует отправки на проверку, но важно для более глубокого понимания материала.


### Как выстроена работа

1. Внимательно прочтите условия задания, перейдите в DBeaver и выполните работу.
2. Когда закончите работу над заданием, вернитесь к этому материалу и нажмите кнопку «Посмотреть решение». Так вы откроете скрипт решения от эксперта.
3. Сравните свой вариант решения с предлагаемым, а затем нажмите кнопку «Продолжить», чтобы открыть новую задачу.<br><br>
Рекомендуем сначала выполнить задания самостоятельно, а потом посмотреть решение.<br>


### Цели практической работы

- Ознакомиться с принципами использования транзакций в SQL.
- Научиться применять команды BEGIN TRANSACTION, COMMIT и ROLLBACK для управления транзакциями.
- Исследовать механизмы обеспечения целостности данных при выполнении последовательности операций.
- Научиться применять транзакции для обработки данных, включая работу с ошибками и восстановление изменений.

## Задание 1. Добавление данных с использованием транзакции
Добавьте нового пользователя в таблицу Users и сразу же внесите его первый рейтинг для фильма «Начало». Если любая из операций завершится неудачей, обе должны быть отменены.

<br><strong>Решение к заданию 1</strong><br>
<details>
<summary> Нажмите, чтоб посмотреть решение </summary>

```BEGIN```<br>

```INSERT INTO Users (username, email, password_hash)```<br>
```VALUES ('new_user', 'new_user@example.com', 'hashed_password');```<br>

```INSERT INTO Ratings (user_id, movie_id, rating)```<br>
```VALUES ((SELECT user_id FROM Users WHERE username = 'new_user')```<br>,
```  (SELECT movie_id FROM Movies WHERE title = 'Начало'), 9);```<br>

```COMMIT;``` <br>

</details>

## Задание 2. Обновление с отменой
Обновите страну производства фильма с названием «Аватар» на USA. Затем попробуйте удалить все связанные с ним жанры. Если операция удаления завершится неудачей, изменения в стране производства не должны сохраниться.

<br><strong>Решение к заданию 2</strong><br>
<details>
<summary> Нажмите, чтоб посмотреть решение </summary>

```BEGIN;```<br>
```UPDATE Movies```<br>
```SET country = 'USA'```<br>
```WHERE title = 'Аватар';```<br>
```DELETE FROM MovieGenres```<br>
```WHERE movie_id = (SELECT movie_id FROM Movies WHERE title = 'Аватар');```<br>
```COMMIT;```<br>

</details>

## Задание 3. Добавление избранного с проверкой
Добавьте фильм «Матрица» в избранное для пользователя с именем john_doe. Если этого пользователя или фильма не существует, транзакция должна быть отменена.

<br><strong>Решение к заданию 3</strong><br>
<details>
<summary> Нажмите, чтоб посмотреть решение </summary>

```BEGIN;```<br>

```INSERT INTO Favorites (user_id, movie_id)```<br>
```VALUES (```<br>
  ```(SELECT user_id FROM Users WHERE username = 'john_doe'),```<br>
  ```(SELECT movie_id FROM Movies WHERE title = 'Матрица')```<br>
```);```<br>
```COMMIT;```<br>


</details>

## Задание 4. Одновременное добавление нескольких записей
Добавьте двух новых пользователей в таблицу Users и сразу же внесите для каждого из них по одной рецензии на фильм «Начало». Если любая из операций завершится неудачей, транзакция должна быть отменена.

<br><strong>Решение к заданию 4</strong><br>
<details>
<summary> Нажмите, чтоб посмотреть решение </summary>

```BEGIN;```<br>

```INSERT INTO Users (username, email, password_hash)```<br>
```VALUES ('user1', 'user1@example.com', 'hashed_password1'),```<br>
```  ('user2', 'user2@example.com', 'hashed_password2');```<br>

```INSERT INTO Reviews (user_id, movie_id, review_text)```<br>
```VALUES ((SELECT user_id FROM Users WHERE username = 'user1'),```<br>
```  (SELECT movie_id FROM Movies WHERE title = 'Начало'),```<br>
```  'Потрясающий фильм!'),```<br>
```  ((SELECT user_id FROM Users WHERE username = 'user2'),```<br>
```  (SELECT movie_id FROM Movies WHERE title = 'Начало'),```<br>
```  'Шедевр!');```<br>

```COMMIT;```<br>

</details>

## Задание 5. Удаление данных с проверкой
Удалите фильм «Титаник» из базы данных, а также все связанные с ним жанры, оценки, избранное и рецензии. Если удаление любой из этих записей завершится ошибкой, транзакция должна быть отменена.

<br><strong>Решение к заданию 5</strong><br>
<details>
<summary> Нажмите, чтоб посмотреть решение </summary>

```BEGIN;```<br>

```DELETE FROM MovieGenres```<br>
```WHERE movie_id = (SELECT movie_id FROM Movies WHERE title = 'Титаник');```<br>

```DELETE FROM Ratings```<br>
```WHERE movie_id = (SELECT movie_id FROM Movies WHERE title = 'Титаник');```<br>

```DELETE FROM Favorites```<br>
```WHERE movie_id = (SELECT movie_id FROM Movies WHERE title = 'Титаник');```<br>

```DELETE FROM Reviews```<br>
```WHERE movie_id = (SELECT movie_id FROM Movies WHERE title = 'Титаник');```<br>

```DELETE FROM Movies```<br>
```WHERE title = 'Титаник';```<br>

```COMMIT;```<br>

</details>





























































