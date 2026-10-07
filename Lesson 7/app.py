import time
import redis

# Инициализация подключения к Redis
# 💡 Добавлен флаг decode_responses=True, чтобы не перегружать код вызовами .decode('utf-8')
r = redis.Redis(
    host='localhost', 
    port=6379, 
    db=0, 
    decode_responses=True
)

def register_user(user_id, name, email):
    """1. Регистрация пользователя с использованием хэша (Hashes)"""
    user_key = f"user:{user_id}"
    r.hset(user_key, mapping={
        "name": name,
        "email": email,
        "created_at": time.strftime("%Y-%m-%d %H:%M:%S")
    })
    print(f"📦 [HSET] Пользователь {name} успешно сохранен в базу (Ключ: {user_key})")

def get_user_profile(user_id):
    """2. Получение профиля пользователя с механизмом кэширования (Strings + TTL)"""
    cache_key = f"cache:user:{user_id}"
    
    # Шаг A: Проверяем наличие профиля в быстром кэше Redis
    cached_data = r.get(cache_key)
    if cached_data:
        print(f"⚡ [CACHE HIT] Данные профиля {user_id} мгновенно извлечены из кэша:")
        return cached_data

    # Шаг Б: Если в кэше нет (CACHE MISS) — запрашиваем из основной структуры (Hashes)
    user_key = f"user:{user_id}"
    user_data = r.hgetall(user_key)
    
    if not user_data:
        print(f"❌ [NOT FOUND] Пользователь с ID {user_id} отсутствует в системе.")
        return None

    # Форматируем данные из словаря в читаемую строку
    profile_str = ", ".join([f"{k}: {v}" for k, v in user_data.items()])
    
    # Шаг В: Сохраняем результат в кэш на 15 секунд (SETEX) для последующих запросов
    r.setex(cache_key, 15, profile_str)
    print(f"🗄️ [CACHE MISS] Профиль {user_id} прочитан из БД и записан в кэш на 15 секунд.")
    return profile_str

def log_user_action(user_id, action):
    """3. Журналирование действий пользователя с использованием ограниченного списка (Lists + LTRIM)"""
    list_key = f"user:{user_id}:actions"
    timestamp = time.strftime('%H:%M:%S')
    
    # Добавляем новое действие в начало (голову) списка
    r.lpush(list_key, f"{timestamp} — {action}")
    
    # Ограничиваем список только последними 5 действиями, чтобы не раздувать память
    r.ltrim(list_key, 0, 4)
    print(f"📝 [LPUSH + LTRIM] Лог пользователя {user_id}: {action}")

def track_unique_visit(ip_address):
    """4. Подсчет уникальных визитов с помощью HyperLogLog (PFADD)"""
    is_new = r.pfadd("unique_visitors", ip_address)
    status = "Новый IP" if is_new == 1 else "Повторный IP (игнорируется)"
    print(f"🌐 [PFADD] Обработан визит с адреса {ip_address} ({status})")

def get_unique_visitors_count():
    """5. Получение количества уникальных посетителей (PFCOUNT)"""
    count = r.pfcount("unique_visitors")
    print(f"📊 [PFCOUNT] Аналитика: уникальных посетителей за всё время: {count}")
    return count

# --- Сценарий демонстрации работы приложения ---
if __name__ == "__main__":
    print("=" * 60)
    print("      ЗАПУСК ФИНАЛЬНОГО ПРАКТИЧЕСКОГО ПРОЕКТА REDIS + PYTHON      ")
    print("=" * 60 + "\n")
    
    # Очищаем демонстрационную базу перед стартом
    r.flushdb()
    
    print("--- Этап 1: Регистрация пользователей ---")
    register_user(101, "Alice", "alice@example.com")
    register_user(102, "Bob", "bob@example.com")
    print("-" * 40 + "\n")
    
    print("--- Этап 2: Проверка работы кэширования (Временные строки) ---")
    # 1-й вызов: Данных в кэше нет, скрипт пойдет в хэш-таблицу
    print(f"Запрос 1: {get_user_profile(101)}")
    
    # 2-й вызов: Данные уже в кэше, мгновенная отдача
    print(f"Запрос 2: {get_user_profile(101)}")
    print("-" * 40 + "\n")
    
    print("--- Этап 3: Ограниченное логирование (Списки) ---")
    log_user_action(101, "Авторизация в приложении")
    log_user_action(101, "Переход в корзину")
    log_user_action(101, "Изменение адреса доставки")
    log_user_action(101, "Оплата заказа #4112")
    log_user_action(101, "Выход из профиля")
    log_user_action(101, "Попытка повторного входа")  # Это шестое действие, первый лог сотрется
    
    # Выводим сохраненную историю действий
    actions = r.lrange("user:101:actions", 0, -1)
    print("\nПоследние 5 записей в журнале для пользователя 101:")
    for act in actions:
        print(f"  - {act}")
    print("-" * 40 + "\n")
    
    print("--- Этап 4: Вероятностная аналитика (HyperLogLog) ---")
    track_unique_visit("192.168.0.1")
    track_unique_visit("95.211.23.14")
    track_unique_visit("192.168.0.1")  # Полный дубликат
    track_unique_visit("174.12.93.55")
    
    get_unique_visitors_count()
    print("\n" + "=" * 60)
    print("               ДЕМОНСТРАЦИЯ УСПЕШНО ЗАВЕРШЕНА               ")
    print("=" * 60)
