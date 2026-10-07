import time
import redis

# Настройка подключения к локальному серверу Redis
client = redis.Redis(host="localhost", port=6379, db=0)

def fake_api_query(user_id):
    """Имитация тяжелого и долгих запросов к API или БД"""
    print(f" [API] Запрос для пользователя {user_id} отправлен в тяжелую БД...")
    time.sleep(2)  # Искусственная задержка
    return f"User Profile. User ID: {user_id}"

def get_user_profile(user_id):
    """Функция получения профиля с логикой кэширования"""
    cache_key = f"user:{user_id}:profile"
    
    # [GET] Проверяем наличие ключа в Redis
    cached_data = client.get(cache_key)
    
    if cached_data:
        print("[ CACHE HIT] Данные взяты напрямую из кэша Redis!")
        return cached_data.decode('utf-8')
        
    # [CACHE MISS] Если в кэше пусто — идем в тяжелую функцию
    print("[ CACHE MISS] В кэше пусто. Обращаемся к источнику данных...")
    profile_data = fake_api_query(user_id)
    
    # [SETEX] Записываем результат в Redis на 60 секунд
    client.setex(cache_key, 60, profile_data)
    print(f" [REDIS] Данные закэшированы в ключ '{cache_key}' на 60 секунд.")
    
    return profile_data

if __name__ == "__main__":
    print("=== ТЕСТИРОВАНИЕ СИСТЕМЫ КЭШИРОВАНИЯ ===\n")
    
    # Очищаем базу перед тестом
    client.flushdb()
    
    print("Вызов функции в первый раз:")
    print(get_user_profile(1))
    print("-" * 40)
    
    print("Вызов функции во второй раз:")
    print(get_user_profile(1))
    print("-" * 40)
