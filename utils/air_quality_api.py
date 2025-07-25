# utils/air_quality_api.py
import httpx
import logging
from config import AQICN_API_KEY # Этот импорт оставляем, он нужен для доступа к ключу

logger = logging.getLogger(__name__)

AQICN_API_BASE_URL = "https://api.waqi.info/feed/geo:{lat};{lon}/"

async def get_air_quality_data(latitude: float, longitude: float) -> dict | None:
    """
    Получает данные о качестве воздуха для заданных координат с aqicn.org.
    Возвращает словарь с данными или None в случае ошибки.
    """
    if not AQICN_API_KEY:
        logger.error("AQICN_API_KEY не установлен. Невозможно получить данные о качестве воздуха.")
        return None

    url = AQICN_API_BASE_URL.format(lat=latitude, lon=longitude)
    params = {
        "token": AQICN_API_KEY
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()

            if data.get("status") == "ok":
                iaqi = data["data"].get("iaqi", {}) # Индивидуальные индексы загрязнителей
                aqi = data["data"].get("aqi") # Общий AQI
                city = data["data"].get("city", {}).get("name", "Неизвестно")
                time_data = data["data"].get("time", {})

                # Формируем отчет
                report_data = {
                    "overall_aqi": aqi,
                    "city_name": city,
                    "local_time": time_data.get("s", "Неизвестно"), # 's' - время станции
                    "iaqi": {}
                }

                # Извлекаем данные по основным загрязнителям
                if 'pm25' in iaqi:
                    report_data["iaqi"]["PM2.5"] = iaqi['pm25']['v']
                if 'pm10' in iaqi:
                    report_data["iaqi"]["PM10"] = iaqi['pm10']['v']
                if 'o3' in iaqi:
                    report_data["iaqi"]["O3"] = iaqi['o3']['v']
                if 'co' in iaqi:
                    report_data["iaqi"]["CO"] = iaqi['co']['v']
                if 'so2' in iaqi:
                    report_data["iaqi"]["SO2"] = iaqi['so2']['v']
                if 'no2' in iaqi:
                    report_data["iaqi"]["NO2"] = iaqi['no2']['v']

                return report_data
            else:
                logger.warning(f"Ошибка от AQICN API: {data.get('data', 'Нет данных или статус не OK')}")
                return None

    except httpx.RequestError as exc:
        logger.error(f"Ошибка запроса к AQICN API: {exc}")
        return None
    except httpx.HTTPStatusError as exc:
        logger.error(f"Ошибка HTTP статуса от AQICN API: {exc.response.status_code} - {exc.response.text}")
        return None
    except Exception as e:
        logger.error(f"Неожиданная ошибка при получении данных AQICN: {e}", exc_info=True)
        return None