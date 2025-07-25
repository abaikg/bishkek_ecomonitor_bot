# handlers/subscriptions.py
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton # <<< Добавлено Update
from telegram.ext import ContextTypes, ConversationHandler
from database import db
from utils.air_quality_api import get_air_quality_data
from utils.geo_utils import geocode_address
from utils.markdown_helpers import escape_markdown_v2
import logging

logger = logging.getLogger(__name__)

# Состояния для ConversationHandler
GET_SUB_LOCATION = 1
GET_SUB_THRESHOLD = 2

async def subscribe_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Начинает процесс подписки."""
    await update.message.reply_text(
        "Для подписки на уведомления о качестве воздуха, пожалуйста, "
        "**отправьте свою геопозицию** через кнопку скрепки (скрепка > Геопозиция) или **введите название района/улицы**.\n\n"
        "Вы можете отменить подписку в любой момент, нажав /cancel."
    )
    return GET_SUB_LOCATION

async def handle_sub_location(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обрабатывает введенную локацию для подписки."""
    latitude, longitude, location_name = None, None, None

    if update.message.location:
        latitude = update.message.location.latitude
        longitude = update.message.location.longitude
        location_name = "Ваша текущая локация"
        await update.message.reply_text(f"Получена ваша геопозиция. {location_name}.")
    elif update.message.text:
        input_location = update.message.text
        
        coords_list = await geocode_address(input_location, limit=1)
        
        if coords_list:
            latitude, longitude, location_name = coords_list[0]
            await update.message.reply_text(f"Найдена локация: {escape_markdown_v2(location_name)}.")
        else:
            await update.message.reply_text(
                "К сожалению, не удалось найти такую локацию. Попробуйте ввести более точное название или отправьте геопозицию."
            )
            return GET_SUB_LOCATION

    if latitude is not None and longitude is not None:
        context.user_data['sub_latitude'] = latitude
        context.user_data['sub_longitude'] = longitude
        context.user_data['sub_location_name'] = location_name

        current_air_data = await get_air_quality_data(latitude, longitude)
        if current_air_data and current_air_data.get('overall_aqi') is not None:
            current_aqi = current_air_data['overall_aqi']
            category, _ = _get_aqi_category(current_aqi)
            await update.message.reply_text(
                f"Текущий AQI для {escape_markdown_v2(location_name)}: **{escape_markdown_v2(str(current_aqi))}** \\({escape_markdown_v2(category)}\\).\n"
                "При каком значении AQI вы бы хотели получать уведомления? "
                "Введите число \\(например, 100\\) или 0, если хотите получать все уведомления о существенных изменениях\\."
            )
        else:
            await update.message.reply_text(
                "Не удалось получить текущие данные AQI для этой локации. "
                "Вы можете ввести пороговое значение вручную или отменить подписку (/cancel)."
            )
        return GET_SUB_THRESHOLD
    
    return GET_SUB_LOCATION

async def handle_sub_threshold(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обрабатывает введенный порог AQI и сохраняет подписку."""
    try:
        aqi_threshold = int(update.message.text)
        if aqi_threshold < 0:
            raise ValueError
    except ValueError:
        await update.message.reply_text(
            "Пожалуйста, введите корректное число для порога AQI (например, 100) или 0."
        )
        return GET_SUB_THRESHOLD

    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    latitude = context.user_data.get('sub_latitude')
    longitude = context.user_data.get('sub_longitude')
    location_name = context.user_data.get('sub_location_name', "Неизвестная локация")

    if latitude is None or longitude is None:
        await update.message.reply_text("Произошла ошибка с локацией. Пожалуйста, попробуйте начать подписку снова (/subscribe).")
        return ConversationHandler.END

    db.add_subscription(user_id, chat_id, latitude, longitude, location_name, aqi_threshold)
    await update.message.reply_text(
        f"Вы успешно подписались на уведомления о качестве воздуха для {escape_markdown_v2(location_name)}. "
        f"Уведомления будут приходить при AQI от **{escape_markdown_v2(str(aqi_threshold))}** и выше (или при существенных изменениях, если 0)."
    )
    context.user_data.pop('sub_latitude', None)
    context.user_data.pop('sub_longitude', None)
    context.user_data.pop('sub_location_name', None)

    return ConversationHandler.END

async def unsubscribe_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Отменяет подписку для пользователя."""
    user_id = update.effective_user.id
    if db.remove_subscription(user_id):
        await update.message.reply_text("Вы успешно отписались от уведомлений о качестве воздуха.")
    else:
        await update.message.reply_text("У вас нет активных подписок.")

async def my_subscriptions_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Показывает текущие подписки пользователя."""
    user_id = update.effective_user.id
    subscription = db.get_subscription(user_id)
    if subscription:
        text = f"Ваша текущая подписка:\n\n"
        text += f"**Локация:** {escape_markdown_v2(subscription['location_name'])}\n"
        
        aqi_threshold_text = f"{subscription['aqi_threshold']} (0 = все существенные изменения)"
        text += f"**Порог AQI для уведомлений:** {escape_markdown_v2(aqi_threshold_text)}\n"
        
        await update.message.reply_markdown_v2(text)
    else:
        await update.message.reply_text("У вас нет активных подписок. Вы можете подписаться, нажав /subscribe.")

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
