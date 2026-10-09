# Лекция 7: Практический проект на Python и Redis

## 1. Введение и цель проекта

В финальном уроке курса рассматривается создание практического консольного приложения на языке Python с использованием базы данных Redis в качестве основного хранилища.

### Задачи приложения:

* **Регистрация пользователей:** Хранение структурированных профилей с использованием хэш-таблиц (`Hashes`).  
* **Кэширование данных:** Мгновенная отдача профилей пользователей с автоматическим истечением срока актуальности.  
* **Подсчет аналитики:** Эффективный учет уникальных визитов и пользователей за счет структуры `HyperLogLog`.  
* **Журналирование действий:** Ведение ограниченной истории последних событий пользователя с помощью списков (`Lists`).  
* **Управление временем жизни:** Ограничение частоты запросов и кэширование через параметры `TTL / EXPIRE`.

## 2. Архитектура и структура кода

### Полный код практического проекта

```python
import redis
import time

# Инициализация подключения к Redis
r = redis.Redis(host='localhost', port=6379, db=0)

def register_user(user_id, name, email):
    """Регистрация пользователя с использованием хэша (Hashes)"""
    user_key = f"user:{user_id}"
    r.hset(user_key, mapping={
        "name": name,
        "email": email,
        "created_at": time.strftime("%Y-%m-%d %H:%M:%S")
    })
    print(f"[+] Пользователь {name} зарегистрирован (Ключ: {user_key})")

def get_user_profile(user_id):
    """Получение профиля пользователя с механизмом кэширования"""
    cache_key = f"cache:user:{user_id}"
    
    # 1. Проверяем наличие профиля в кэше Redis
    cached_data = r.get(cache_key)
    if cached_data:
        print(f"[CACHE HIT] Профиль {user_id} получен из кэша:")
        return cached_data.decode('utf-8')

    # 2. Если в кэше нет (CACHE MISS) — запрашиваем из основной структуры (Hashes)
    user_key = f"user:{user_id}"
    user_data = r.hgetall(user_key)
    
    if not user_data:
        print(f"[-] Пользователь {user_id} не найден.")
        return None

    # Декодирование данных
    profile_str = ", ".join([f"{k.decode('utf-8')}: {v.decode('utf-8')}" for k, v in user_data.items()])
    
    # 3. Сохраняем результат в кэш на 30 секунд (SETEX)
    r.setex(cache_key, 30, profile_str)
    print(f"[DB READ] Профиль {user_id} прочитан из основной БД и закэширован на 30 сек.")
    return profile_str

def log_user_action(user_id, action):
    """Логирование действий пользователя с использованием списка (Lists)"""
    list_key = f"user:{user_id}:actions"
    # Добавляем действие в начало списка
    r.lpush(list_key, f"{time.strftime('%H:%M:%S')} - {action}")
    # Ограничиваем список только последними 10 действиями
    r.ltrim(list_key, 0, 9)
    print(f"[LOG] Зафиксировано действие пользователя {user_id}: {action}")

def track_unique_visit(ip_address):
    """Подсчет уникальных визитов с помощью HyperLogLog"""
    r.pfadd("unique_visitors", ip_address)

def get_unique_visitors_count():
    """Получение количества уникальных посетителей"""
    count = r.pfcount("unique_visitors")
    print(f"[ANALYTICS] Уникальных посетителей за всё время: {count}")
    return count

# --- Демонстрация работы приложения ---
if __name__ == "__main__":
    print("=== ЗАПУСК ПРАКТИЧЕСКОГО ПРОЕКТА REDIS + PYTHON ===\n")
    
    # 1. Регистрация пользователей
    register_user(101, "Alice", "alice@example.com")
    register_user(102, "Bob", "bob@example.com")
    
    print("\n--- Проверка работы кэширования ---")
    # Первый вызов — чтение из основной структуры и запись в кэш
    print(get_user_profile(101))
    
    # Повторный вызов — мгновенная отдача из кэша
    print(get_user_profile(101))
    
    print("\n--- Логирование действий ---")
    log_user_action(101, "Вход в систему")
    log_user_action(101, "Просмотр каталога товаров")
    log_user_action(101, "Оформление заказа")
    
    # Вывод истории действий
    actions = r.lrange("user:101:actions", 0, -1)
    print("История действий 101:")
    for act in actions:
        print(f" - {act.decode('utf-8')}")
        
    print("\n--- Аналитика уникальных посещений (HyperLogLog) ---")
    track_unique_visit("192.168.1.10")
    track_unique_visit("192.168.1.11")
    track_unique_visit("192.168.1.10") # Дубликат, не увеличит счетчик
    get_unique_visitors_count()
```

## 3. Заключение курса

За время изучения курса были освоены основные концепции работы с Redis и интеграция системы в реальные проекты:

* **Развертывание и инфраструктура:**  
&nbsp;&nbsp;&nbsp;&nbsp;Настройка и запуск Redis в различных окружениях (Linux, macOS, Docker на Windows, Redis Cloud). 
* **Базовые операции:**  
&nbsp;&nbsp;&nbsp;&nbsp;Применение команд манипуляции данными (`SET`, `GET`, `DEL`, `EXISTS`, `INCR`, `DECR`).  
* **Сложные структуры данных:**  
&nbsp;&nbsp;&nbsp;&nbsp;**Sets** — работа с уникальными множествами (`SADD`, `SMEMBERS`).  
&nbsp;&nbsp;&nbsp;&nbsp;**Sorted Sets (ZSet)** — создание рейтингов и таблиц лидеров с баллами Score (`ZADD`, `ZRANGE`).  
&nbsp;&nbsp;&nbsp;&nbsp;**Lists** — организация очередей и истории событий (`LPUSH`, `RPUSH`, `LPOP`, `RPOP`, `LTRIM`).  
&nbsp;&nbsp;&nbsp;&nbsp;**Hashes** — эффективное представление объектных моделей (`HSET`, `HGETALL`).  
&nbsp;&nbsp;&nbsp;&nbsp;**HyperLogLog** — вероятностный подсчет кардинальности с минимальным расходом памяти (`PFADD`, `PFCOUNT`).  
* **Управление памятью:**  
&nbsp;&nbsp;&nbsp;&nbsp;Настройка временных ключей и механизмов автоудаления (`TTL`, `EXPIRE`, `PERSIST`).  
* **Асинхронные коммуникации:**  
&nbsp;&nbsp;&nbsp;&nbsp;Построение событийно-ориентированных сервисов через механизмы `Pub/Sub`.  
* **Надежность и атомарность:**  
&nbsp;&nbsp;&nbsp;&nbsp;Выполнение пакетных транзакционных цепочек (`MULTI`, `EXEC`).  
* **Интеграция:**  
&nbsp;&nbsp;&nbsp;&nbsp;Проектирование высокопроизводительных бэкенд-сервисов на Python с использованием клиента `redis-py`.

