import time
import redis

# ==============================================================================
# 1. ПОДКЛЮЧЕНИЕ К REDIS
# ==============================================================================

# Использование decode_responses=True автоматически конвертирует байты (b'...') 
# в привычные строки Python (str). Это избавляет от необходимости писать .decode('utf-8')!
client = redis.Redis(
    host='localhost',
    port=6379,
    db=0,
    decode_responses=True  # 💡 Лайфхак: автоматически декодирует ответы сервера
)

def run_redis_demo():
    try:
        # Проверяем соединение
        if not client.ping():
            print("❌ Не удалось связаться с сервером Redis.")
            return
        print("✅ Успешное подключение к Redis!\n")
    except redis.ConnectionError as e:
        print(f"❌ Ошибка подключения: {e}")
        print("👉 Убедитесь, что запущен redis-server или Docker-контейнер.")
        return

    # Очищаем базу данных перед демонстрацией, чтобы примеры запускались корректно
    client.flushdb()

    # ==============================================================================
    # 2. РАБОТА СО СТРОКАМИ (STRINGS) И СЧЕТЧИКАМИ
    # ==============================================================================
    print("--- 2. Строки и Счетчики ---")
    
    # Запись и чтение
    client.set('name', 'Alice')
    user_name = client.get('name')  # Без decode_responses тут было бы b'Alice'
    print(f"Имя пользователя из Redis: {user_name}")

    # Установка TTL (Время жизни ключа)
    client.setex('session_token', 3, 'Active')  # Поставим 3 секунды для теста
    print(f"Ключ 'session_token' записан. Оставшееся время (TTL): {client.ttl('session_token')} сек.")

    # Инкременты (Счетчики)
    client.set('user:1:age', 30)
    client.incr('user:1:age')        # +1 -> 31
    client.incrby('user:1:age', 5)   # +5 -> 36
    client.decrby('user:1:age', 9)   # -9 -> 27
    print(f"Текущий возраст пользователя после инкрементов: {client.get('user:1:age')}")
    print("-" * 30 + "\n")

    # ==============================================================================
    # 3. СЛОЖНЫЕ СТРУКТУРЫ ДАННЫХ
    # ==============================================================================
    
    # СПИСКИ (Lists) — Очереди задач
    print("--- 3. Списки (Очереди) ---")
    client.rpush('tasks', 'Сгенерировать отчет', 'Отправить email', 'Очистить кэш')
    tasks = client.lrange('tasks', 0, -1)
    print(f"Список фоновых задач: {tasks}")
    print("-" * 30 + "\n")

    # МНОЖЕСТВА (Sets) — Уникальные теги
    print("--- 4. Множества (Уникальные элементы) ---")
    client.sadd('tags', 'python', 'redis', 'backend', 'python')  # Дубликат 'python' проигнорируется
    tags = client.smembers('tags')
    print(f"Уникальные теги проекта: {tags}")
    print("-" * 30 + "\n")

    # ХЭШ-ТАБЛИЦЫ (Hashes) — Структурированные объекты
    print("--- 5. Хэши (Объекты) ---")
    client.hset('user:1001', mapping={
        'name': 'John Doe',
        'role': 'admin',
        'email': 'john@mail.com'
    })
    user_data = client.hgetall('user:1001')
    print(f"Данные из хэша пользователя 1001: {user_data}")
    print(f"Конкретное поле (role): {client.hget('user:1001', 'role')}")
    print("-" * 30 + "\n")

    # УПОРЯДОЧЕННЫЕ МНОЖЕСТВА (Sorted Sets) — Лидерборды
    print("--- 6. Упорядоченные множества (Рейтинги) ---")
    client.zadd('leaderboard', {'Alex': 150, 'Mary': 230, 'John': 90})
    
    # Запрашиваем элементы, отсортированные по Score (withscores=True возвращает кортежи)
    leaders = client.zrange('leaderboard', 0, -1, withscores=True, desc=True) # desc=True для сортировки от лучших к худшим
    print("Таблица лидеров (Топ игроков):")
    for place, (player, score) in enumerate(leaders, start=1):
        print(f"  {place}. {player} — {int(score)} очков")
    print("-" * 30 + "\n")

    # ==============================================================================
    # 4. ДЕМОНСТРАЦИЯ УДАЛЕНИЯ И ЖИЗНЕННОГО ЦИКЛА
    # ==============================================================================
    print("--- 7. Проверка удаления ключей ---")
    if client.exists('name'):
        client.delete('name')
        print("Ключ 'name' успешно удален.")
    
    print("Ожидаем истечения TTL ключа 'session_token' (3 секунды)...")
    time.sleep(3)
    if not client.exists('session_token'):
        print("Ключ 'session_token' автоматически удалился по истечении времени.")

if __name__ == '__main__':
    run_redis_demo()
