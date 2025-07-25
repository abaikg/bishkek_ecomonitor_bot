# handlers/subscriptions.py
from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler
from telegram.constants import ParseMode
from telegram import KeyboardButton, ReplyKeyboardMarkup

from database import db
from utils.air_quality_api import get_air_quality_data
from utils.geo_utils import geocode_address
from utils.markdown_helpers import escape_markdown_v2

import logging

logger = logging.getLogger(__name__)

GET_SUB_LOCATION = 1
GET_SUB_THRESHOLD = 2

# ---------- Команда /subscribe ----------
async def subscribe_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text(
        "📍 Чтобы подписаться на уведомления о качестве воздуха:",
        reply_markup=ReplyKeyboardMarkup(
            [[KeyboardButton("📍 Отправить геопозицию", request_location=True)]],
            resize_keyboard=True,
            one_time_keyboard=True
        )
    )
    await update.message.reply_text(
        "Или отправьте текстом название района/улицы.\n\nКоманду можно отменить: /cancel"
    )
    return GET_SUB_LOCATION

# ---------- Обработка локации ----------
async def handle_sub_location(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    latitude, longitude, location_name = None, None, None

    if update.message.location:
        latitude = update.message.location.latitude
        longitude = update.message.location.longitude
        location_name = "ваша текущая геопозиция"
        await update.message.reply_text("📌 Геопозиция получена.")

    elif update.message.text:
        input_location = update.message.text.strip()
        coords_list = await geocode_address(input_location, limit=1)

        if coords_list:
            latitude, longitude, location_name = coords_list[0]
            await update.message.reply_text(f"📍 Найдено: *{escape_markdown_v2(location_name)}*", parse_mode=ParseMode.MARKDOWN_V2)
        else:
            await update.message.reply_text(
                "❌ Локация не найдена. Попробуйте снова или отправьте геопозицию."
            )
            return GET_SUB_LOCATION

    if latitude and longitude:
        context.user_data['sub_latitude'] = latitude
        context.user_data['sub_longitude'] = longitude
        context.user_data['sub_location_name'] = location_name

        current_air_data = await get_air_quality_data(latitude, longitude)

        if current_air_data and current_air_data.get("overall_aqi") is not None:
            current_aqi = current_air_data["overall_aqi"]
            category, emoji = _get_aqi_category(current_aqi)
            await update.message.reply_text(
                f"📊 AQI в {escape_markdown_v2(location_name)}: *{current_aqi}* ({category} {emoji})\n"
                "💬 Укажите значение AQI, при превышении которого вы хотите получать уведомления.\n"
                "Например: *100* или *0*, если хотите получать все существенные изменения.",
                parse_mode=ParseMode.MARKDOWN_V2
            )
        else:
            await update.message.reply_text(
                "⚠️ Не удалось получить текущий AQI. Вы можете продолжить, указав порог вручную, или отменить подписку (/cancel)."
            )
        return GET_SUB_THRESHOLD

    return GET_SUB_LOCATION

# ---------- Обработка порога AQI ----------
async def handle_sub_threshold(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        aqi_threshold = int(update.message.text)
        if aqi_threshold < 0:
            raise ValueError
    except ValueError:
        await update.message.reply_text("🚫 Введите корректное число (например, 100) или 0.")
        return GET_SUB_THRESHOLD

    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    latitude = context.user_data.get('sub_latitude')
    longitude = context.user_data.get('sub_longitude')
    location_name = context.user_data.get('sub_location_name', 'Неизвестная локация')

    if latitude is None or longitude is None:
        await update.message.reply_text("⚠️ Не удалось сохранить локацию. Попробуйте /subscribe заново.")
        return ConversationHandler.END

    db.add_subscription(user_id, chat_id, latitude, longitude, location_name, aqi_threshold)

    await update.message.reply_text(
        f"✅ Подписка оформлена!\n\n📍 Локация: *{escape_markdown_v2(location_name)}*\n"
        f"📈 Уведомления при AQI от: *{escape_markdown_v2(str(aqi_threshold))}*",
        parse_mode=ParseMode.MARKDOWN_V2
    )

    context.user_data.clear()
    return ConversationHandler.END

# ---------- Команда /unsubscribe ----------
async def unsubscribe_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    if db.remove_subscription(user_id):
        await update.message.reply_text("🔕 Вы отписались от уведомлений.")
    else:
        await update.message.reply_text("ℹ️ У вас нет активных подписок.")

# ---------- Команда /mysub ----------
async def my_subscriptions_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    subscription = db.get_subscription(user_id)

    if subscription:
        text = (
            "📬 *Ваша подписка:*\n\n"
            f"📍 Локация: *{escape_markdown_v2(subscription['location_name'])}*\n"
            f"📈 Порог AQI: *{subscription['aqi_threshold']}*"
        )
        if subscription['aqi_threshold'] == 0:
            text += " (все существенные изменения)"

        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN_V2)
    else:
        await update.message.reply_text("ℹ️ У вас нет активных подписок. Используйте /subscribe.")

# ---------- Категории AQI ----------
def _get_aqi_category(aqi: int) -> tuple[str, str]:
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
