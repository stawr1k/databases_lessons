# Лекция 5: Подключение и работа с Redis на языке Python


## 1. Введение и подготовка окружения

Для работы с Redis из языка Python используется официальная клиентская библиотека `redis`.

### Шаг 1. Проверка установки Python

Перед началом работы убедитесь, что Python установлен в системе.

```sh
python --version
```

или для Linux / macOS:

```sh
python3 --version
```

Если команда не найдена или версия ниже 3.8 — установите Python с официального сайта [python.org](https://www.python.org/downloads/) (для Windows обязательно отметьте галочку **Add Python to PATH** во время установки).

> **Важно:** в VS Code также необходимо установить расширение **Python** (от Microsoft) — оно добавляет подсветку синтаксиса, автодополнение, запуск и отладку кода, а также автоматически подхватывает созданное виртуальное окружение.

### Шаг 2. Создание виртуального окружения

Виртуальное окружение изолирует зависимости проекта от глобальных пакетов системы.

| Система | Команда |
|---------|---------|
| Windows | `python -m venv .venv` |
| Linux | `python3 -m venv .venv` |
| macOS | `python3 -m venv .venv` |

### Шаг 3. Активация виртуального окружения

```sh
# Windows (cmd)
.venv\Scripts\activate.bat

# Windows (PowerShell)
.venv\Scripts\Activate.ps1

# Linux / macOS
source .venv/bin/activate
```

После активации в начале строки терминала появится префикс `(.venv)`.

### Шаг 4. Установка библиотеки

```sh
pip install redis
```

### Проверка версии библиотеки в Python

```python
import redis

print(redis.__version__)
```

## 2. Подключение к серверу Redis

Перед подключением из Python необходимо запустить сервер Redis (например, `redis-server` в терминале или через Docker).

### Код подключения и проверка связи

```python
import redis

# Создание клиента подключения
client = redis.Redis(
    host='localhost', # Адрес хоста (локальный или удаленный Redis Cloud)
    port=6379,        # Стандартный порт Redis
    db=0              # Номер базы данных (по умолчанию 0)
)

try:
    # Проверка соединения с помощью ping()
    response = client.ping()
    print(f"Connection to Redis: {response}") # Возвращает True при успешном подключении
except redis.ConnectionError as e:
    print(f"Connection failed: {e}")
```

## 3. Базовые операции с ключами и строками (Strings)

### Команды set(), get(), delete(), exists()

В Python ответы от Redis возвращаются в виде байтовых строк (`b'value'`), поэтому для получения обычной строки вызывается метод `.decode('utf-8')`.

```python
# Запись и чтение
client.set('name', 'Alice')
user_name = client.get('name').decode('utf-8')
print(f"User Name: {user_name}") # Alice

# Проверка существования и удаление
if client.exists('name'):
    print("Key exists")
    client.delete('name')
```

## 4. Установка времени жизни (TTL / EXPIRE)

### Метод setex() и ttl()

```python
# Установка ключа 'session' со значением 'Active' на 3600 секунд (1 час)
client.setex('session', 3600, 'Active')

# Получение оставшегося времени жизни в секундах
time_left = client.ttl('session')
print(f"Left: {time_left} seconds")
```

## 5. Инкременты и декременты (INCR / DECR)

```python
client.set('user:1:age', 30)

# Увеличение на 1 и на заданный шаг
client.incr('user:1:age')        # Станет 31
client.incrby('user:1:age', 5)   # Станет 36

# Уменьшение на 1 и на заданный шаг
client.decr('user:1:age')        # Станет 35
client.decrby('user:1:age', 8)   # Станет 27

current_age = client.get('user:1:age').decode('utf-8')
print(f"Current Age: {current_age}") # 27
```

## 6. Работа со сложными структурами данных

### Списки (Lists)

```python
# Добавление элементов в конец списка (RPUSH)
client.rpush('tasks', 'Task 1', 'Task 2', 'Task 3')

# Получение всех элементов списка (LRANGE 0 -1)
raw_tasks = client.lrange('tasks', 0, -1)
tasks = [task.decode('utf-8') for task in raw_tasks]
print(f"Tasks: {tasks}") # ['Task 1', 'Task 2', 'Task 3']
```

### Множества (Sets)

```python
# Добавление уникальных элементов (SADD)
client.sadd('tags', 'python', 'redis', 'backend')

# Получение всех элементов множества (SMEMBERS)
raw_tags = client.smembers('tags')
tags = [tag.decode('utf-8') for tag in raw_tags]
print(f"Tags: {tags}")
```

### Хэш-таблицы (Hashes)

```python
# Запись объекта в хэш-таблицу (HSET)
client.hset('user:1001', mapping={
    'name': 'John',
    'age': 30,
    'email': 'john@mail.com'
})

# Получение всех полей и значений объекта (HGETALL)
raw_user = client.hgetall('user:1001')
user_data = {k.decode('utf-8'): v.decode('utf-8') for k, v in raw_user.items()}
print(f"User Data: {user_data}")
```

### Упорядоченные множества (Sorted Sets)

```python
# Добавление элементов с баллами Score (ZADD)
client.zadd('leaderboard', {'player1': 100, 'player2': 90})

# Получение элементов с их очками (ZRANGE withscores=True)
leaders = client.zrange('leaderboard', 0, -1, withscores=True)

for player, score in leaders:
    print(f"Player: {player.decode('utf-8')}, Score: {score}")
```

`Следующий материал:` [Лекция 6: Кеширование данных с помощью Redis на Python](../Lesson%206/lesson%206.md)