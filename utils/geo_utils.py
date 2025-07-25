# utils/geo_utils.py
import httpx
import logging

logger = logging.getLogger(__name__)

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"

async def geocode_address(address: str, limit: int = 1): # <<< Добавляем параметр limit
    """
    Геокодирует адрес, используя Nominatim OpenStreetMap.
    Возвращает список кортежей (latitude, longitude, formatted_address)
    или пустой список, если адрес не найден.
    """
    params = {
        "q": f"{address}, Bishkek", # Уточняем поиск по Бишкеку
        "format": "json",
        "limit": limit, # Используем limit
        "addressdetails": 0,
        "accept-language": "ru" # Предпочитаемый язык результатов
    }
    headers = {
        "User-Agent": "BishkekEcoMonitorBot/1.0 (contact@example.com)" # Хорошая практика: указать User-Agent
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(NOMINATIM_URL, params=params, headers=headers, timeout=10)
            response.raise_for_status() # Вызывает исключение для ошибок HTTP
            data = response.json()

            if data:
                # Если limit > 1, возвращаем список всех найденных совпадений
                return [(float(item['lat']), float(item['lon']), item['display_name']) for item in data]
            else:
                logger.info(f"Не удалось геокодировать адрес: {address}")
                return []
    except httpx.RequestError as e:
        logger.error(f"Ошибка запроса к Nominatim для адреса '{address}': {e}")
        return []
    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP ошибка от Nominatim для адреса '{address}': {e.response.status_code} - {e.response.text}")
        return []
    except Exception as e:
        logger.error(f"Неизвестная ошибка при геокодировании адреса '{address}': {e}")
        return []