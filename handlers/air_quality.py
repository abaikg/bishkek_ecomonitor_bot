# handlers/air_quality.py
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes, ConversationHandler
from utils.air_quality_api import get_air_quality_data
from utils.geo_utils import geocode_address
from utils.markdown_helpers import escape_markdown_v2
from handlers.start import start_command # Импортируем start_command для возврата основного меню
import logging

logger = logging.getLogger(__name__)

# Состояния для ConversationHandler
GET_LOCATION_FOR_AQI = 1 # Единое состояние для получения локации (текст или геопозиция)


async def aqi_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Начинает процесс получения AQI.
    Это entry_point для ConversationHandler AQI.
    """
    # Если пользователь отправил локацию сразу (без нажатия кнопки "Отправить мою локацию")
    if update.message and update.message.location:
        # Передаем управление в handle_location_input для обработки локации
        return await handle_location_input(update, context)
    
    # Если пользователь нажал кнопку "Качество воздуха сейчас" или "Найти по названию"
    reply_keyboard = [[KeyboardButton("Отправить мою геопозицию", request_location=True)]]
    markup = ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True, resize_keyboard=True)

    # Применяем escape_markdown_v2 ко всему тексту сообщения
    message_text = (
        "Для получения информации о качестве воздуха, пожалуйста, "
        "**отправьте свою геопозицию** через кнопку скрепки (скрепка > Геопозиция) или **введите название района/улицы**.\n\n"
        "Вы можете отменить в любой момент, нажав /cancel."
    )
    
    await update.message.reply_text(
        escape_markdown_v2(message_text), # Применяем escape_markdown_v2
        reply_markup=markup,
        parse_mode='MarkdownV2'
    )
    return GET_LOCATION_FOR_AQI

async def handle_location_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Обрабатывает ввод локации (геопозиция или текст) для AQI.
    Это обработчик состояния GET_LOCATION_FOR_AQI.
    """
    latitude, longitude, location_name = None, None, None

    if update.message.location:
        latitude = update.message.location.latitude
        longitude = update.message.location.longitude
        location_name = "Ваша текущая локация"
        # Применяем escape_markdown_v2 к тексту
        await update.message.reply_text(escape_markdown_v2(f"Получена ваша геопозиция. {location_name}."), parse_mode='MarkdownV2')
    elif update.message.text:
        input_location = update.message.text
        # Применяем escape_markdown_v2 к тексту
        await update.message.reply_text(escape_markdown_v2(f"Ищу данные для '{input_location}'..."), parse_mode='MarkdownV2')

        results = await geocode_address(input_location, limit=5) # Запрашиваем до 5 совпадений

        if results:
            if len(results) == 1:
                # Если найдено только одно совпадение, сразу используем его
                latitude, longitude, location_name = results[0]
                # Применяем escape_markdown_v2 к тексту
                await update.message.reply_text(escape_markdown_v2(f"Найден адрес: {location_name}. Получаю данные..."), parse_mode='MarkdownV2')
            else:
                # Если найдено несколько совпадений, предлагаем выбрать
                keyboard = []
                context.user_data['geocode_results'] = {} # Сохраняем результаты для последующего выбора

                for i, (lat, lon, addr) in enumerate(results):
                    callback_data = f"select_location_{i}"
                    keyboard.append([InlineKeyboardButton(escape_markdown_v2(addr), callback_data=callback_data)])
                    context.user_data['geocode_results'][callback_data] = {'latitude': lat, 'longitude': lon, 'address': addr}
                
                keyboard.append([InlineKeyboardButton("Отмена", callback_data="cancel_selection")])

                reply_markup = InlineKeyboardMarkup(keyboard)
                # Применяем escape_markdown_v2 к тексту
                await update.message.reply_text(
                    escape_markdown_v2("Найдено несколько локаций. Пожалуйста, уточните, какую вы имели в виду:"),
                    reply_markup=reply_markup,
                    parse_mode='MarkdownV2'
                )
                return GET_LOCATION_FOR_AQI 
        else:
            # Применяем escape_markdown_v2 к тексту
            await update.message.reply_text(
                escape_markdown_v2("К сожалению, не удалось найти такую локацию в Бишкеке. Попробуйте ввести более точное название или отправьте геопозицию."),
                parse_mode='MarkdownV2'
            )
            return GET_LOCATION_FOR_AQI
    else:
        # Применяем escape_markdown_v2 к тексту
        await update.message.reply_text(
            escape_markdown_v2("Не удалось определить локацию. Пожалуйста, попробуйте еще раз, отправив геопозицию или введя название."),
            parse_mode='MarkdownV2'
        )
        return GET_LOCATION_FOR_AQI

    # Если координаты были успешно получены (из location или из text/geocode_address)
    if latitude is not None and longitude is not None:
        air_data = await get_air_quality_data(latitude, longitude)
        if air_data:
            await _send_air_quality_report(update, context, air_data, location_name=location_name)
        else:
            # Применяем escape_markdown_v2 к тексту
            await update.message.reply_text(
                escape_markdown_v2("К сожалению, не удалось получить данные о качестве воздуха для этой локации. Попробуйте позже."),
                parse_mode='MarkdownV2'
            )
        # ВОЗВРАЩАЕМ ГЛАВНОЕ МЕНЮ
        await start_command(update, context) # Вызываем start_command для возврата клавиатуры
        return ConversationHandler.END
    
    return GET_LOCATION_FOR_AQI


async def handle_location_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обрабатывает выбор локации из Inline-кнопок."""
    query = update.callback_query
    await query.answer()

    if query.data == "cancel_selection":
        # Применяем escape_markdown_v2 к тексту
        await query.edit_message_text(escape_markdown_v2("Выбор локации отменен. Чтобы начать снова, введите название или отправьте геопозицию."), parse_mode='MarkdownV2')
        context.user_data.pop('geocode_results', None)
        # ВОЗВРАЩАЕМ ГЛАВНОЕ МЕНЮ
        await start_command(update, context) # Вызываем start_command для возврата клавиатуры
        return ConversationHandler.END

    selected_data = context.user_data.get('geocode_results', {}).get(query.data)

    if selected_data:
        latitude = selected_data['latitude']
        longitude = selected_data['longitude']
        formatted_address = selected_data['address']

        # Применяем escape_markdown_v2 к тексту
        await query.edit_message_text(escape_markdown_v2(f"Выбрана локация: {formatted_address}. Получаю данные..."), parse_mode='MarkdownV2')
        
        air_data = await get_air_quality_data(latitude, longitude)
        await _send_air_quality_report(update, context, air_data, location_name=formatted_address)
        
        context.user_data.pop('geocode_results', None)
        # ВОЗВРАЩАЕМ ГЛАВНОЕ МЕНЮ
        await start_command(update, context) # Вызываем start_command для возврата клавиатуры
        return ConversationHandler.END
    else:
        # Применяем escape_markdown_v2 к тексту
        await query.edit_message_text(escape_markdown_v2("Произошла ошибка при выборе локации. Пожалуйста, попробуйте снова."), parse_mode='MarkdownV2')
        context.user_data.pop('geocode_results', None)
        # ВОЗВРАЩАЕМ ГЛАВНОЕ МЕНЮ
        await start_command(update, context) # Вызываем start_command для возврата клавиатуры
        return ConversationHandler.END


async def _send_air_quality_report(update: Update, context: ContextTypes.DEFAULT_TYPE, air_data: dict | None, location_name: str = "вашей локации") -> None:
    """Вспомогательная функция для отправки отчета о качестве воздуха."""
    if air_data and air_data.get('overall_aqi') is not None:
        city_name_display = air_data.get('city_name', location_name)
        
        escaped_city_name = escape_markdown_v2(city_name_display)
        escaped_local_time = escape_markdown_v2(air_data.get('local_time', 'неизвестно'))
        
        report_text = f"**Качество воздуха для {escaped_city_name}**:\n"
        report_text += f"📅 Время данных: `{escaped_local_time}`\n\n"

        overall_aqi = air_data['overall_aqi']
        category, emoji = _get_aqi_category(overall_aqi)
        
        report_text += f"**Общий AQI**: `{escape_markdown_v2(str(overall_aqi))}` {emoji} \\({escape_markdown_v2(category)}\\)\n"

        iaqi = air_data.get('iaqi', {})
        if iaqi:
            report_text += "\n**Основные загрязнители**:\n"
            for pollutant, value in iaqi.items():
                report_text += f"  • **{escape_markdown_v2(pollutant)}**: `{escape_markdown_v2(str(value))}`\n"

        report_text += "\n"
        report_text += escape_markdown_v2(_get_basic_recommendations(overall_aqi))
        
        report_text += "\n"
        report_text += escape_markdown_v2("ℹ️ Данные от aqicn.org (World Air Quality Index project).")

        if update.callback_query:
            await update.callback_query.edit_message_text(report_text, parse_mode='MarkdownV2')
        else:
            await update.message.reply_markdown_v2(report_text)
    else:
        if update.callback_query:
            await update.callback_query.edit_message_text(
                escape_markdown_v2("К сожалению, не удалось получить данные о качестве воздуха для выбранной локации. "
                "Это может быть связано с отсутствием ближайших станций мониторинга или временными проблемами с сервисом."
                "Попробуйте еще раз или выберите другой район."),
                parse_mode='MarkdownV2'
            )
        else:
            await update.message.reply_text(
                escape_markdown_v2("К сожалению, не удалось получить данные о качестве воздуха для выбранной локации. "
                "Это может быть связано с отсутствием ближайших станций мониторинга или временными проблемами с сервисом."
                "Попробуйте еще раз или выберите другой район."),
                parse_mode='MarkdownV2'
            )


def _get_aqi_category(aqi: int) -> tuple[str, str]:
    """Возвращает категорию и эмодзи для AQI."""
    if aqi <= 50:
        return "Хорошо", "🟢"
    elif aqi <= 100:
        return "Умеренно", "🟡"
    elif aqi <= 150:
        return "Неблагоприятно для чувствительных групп", "🟠"
    elif aqi <= 200:
        return "Неблагоприятно", "🔴"
    elif aqi <= 300:
        return "Очень неблагоприятно", "🟣"
    else:
        return "Опасно", "🟤"

def _get_basic_recommendations(aqi: int) -> str:
    """Возвращает базовые рекомендации на основе AQI."""
    if aqi <= 50:
        return "Качество воздуха хорошее. Наслаждайтесь активностями на свежем воздухе!"
    elif aqi <= 100:
        return "Качество воздуха умеренное. Чувствительным людям стоит ограничить длительные нагрузки на улице."
    elif aqi <= 150:
        return "Неблагоприятно для чувствительных групп. Людям с заболеваниями дыхания и сердца, детям и пожилым следует сократить время на улице."
    elif aqi <= 200:
        return "Качество воздуха неблагоприятное. Избегайте длительного нахождения на улице, особенно при физических нагрузках. Закройте окна."
    elif aqi <= 300:
        return "Очень неблагоприятное. Старайтесь оставаться дома, используйте очистители воздуха. На улице используйте респираторы."
    else:
        return "Качество воздуха опасно! Максимально сократите время нахождения на улице. Используйте защиту органов дыхания. Закройте окна, включите очистители."
