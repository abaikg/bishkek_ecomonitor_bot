# main.py
import logging
from telegram import Update
from telegram.ext import (
    Application, CommandHandler, MessageHandler, filters,
    ConversationHandler, ContextTypes, CallbackQueryHandler
)
from config import TELEGRAM_BOT_TOKEN, AQICN_API_KEY
from handlers.start import start_command
from handlers.air_quality import (
    aqi_command, # <<< ИЗМЕНЕНО: вместо get_air_quality_by_location и request_location_by_name
    handle_location_input, # <<< ИЗМЕНЕНО: вместо handle_location_name_input
    handle_location_selection,
    GET_LOCATION_FOR_AQI # <<< ИЗМЕНЕНО: новое имя состояния
)
from handlers.info import show_recommendations, show_about_bot
from handlers.subscriptions import (
    subscribe_command,
    handle_sub_location,
    handle_sub_threshold,
    unsubscribe_command,
    my_subscriptions_command,
    GET_SUB_LOCATION,
    GET_SUB_THRESHOLD
)
from database import db
from utils.air_quality_api import get_air_quality_data
from utils.markdown_helpers import escape_markdown_v2

# Настройка логирования
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logging.getLogger("httpx").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)

# Проверка наличия API ключа AQICN при запуске
if not AQICN_API_KEY:
    logger.critical("AQICN_API_KEY не установлен! Бот не сможет получать данные о качестве воздуха.")

# --- Функции для фонового задания уведомлений ---
def _get_aqi_category_for_notifications(aqi: int) -> tuple[str, str]:
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


async def send_aqi_notifications(context: ContextTypes.DEFAULT_TYPE):
    """Фоновое задание для отправки уведомлений о качестве воздуха."""
    logger.info("Запуск задачи по рассылке уведомлений о качестве воздуха.")
    subscriptions = db.get_all_active_subscriptions()
    if not subscriptions:
        logger.info("Нет активных подписок для рассылки.")
        return

    for sub in subscriptions:
        user_id = sub['user_id']
        chat_id = sub['chat_id']
        latitude = sub['latitude']
        longitude = sub['longitude']
        location_name = sub['location_name']
        aqi_threshold = sub['aqi_threshold']
        last_notified_aqi = sub['last_notified_aqi']

        try:
            current_air_data = await get_air_quality_data(latitude, longitude)
            if not current_air_data or current_air_data.get('overall_aqi') is None:
                logger.warning(f"Не удалось получить AQI для подписки {user_id} на локации {location_name}.")
                continue

            current_aqi = current_air_data['overall_aqi']
            category, emoji = _get_aqi_category_for_notifications(current_aqi)

            should_notify = False
            if aqi_threshold is not None and current_aqi >= aqi_threshold:
                if last_notified_aqi is None or current_aqi >= last_notified_aqi + 20 or current_aqi <= last_notified_aqi - 20:
                    should_notify = True
            elif aqi_threshold == 0:
                 if last_notified_aqi is None or abs(current_aqi - last_notified_aqi) >= 15:
                     should_notify = True


            if should_notify:
                report_text = (
                    f"🔔 *Уведомление о качестве воздуха*\n\n"
                    f"**Локация:** {escape_markdown_v2(location_name)}\n"
                    f"**Текущий AQI:** `{escape_markdown_v2(str(current_aqi))}` {emoji} \\({escape_markdown_v2(category)}\\)\n"
                    f"📅 Время данных: `{escape_markdown_v2(current_air_data.get('local_time', 'неизвестно'))}`\n\n"
                    "ℹ️ Для подробной информации используйте /airquality"
                )
                await context.bot.send_message(
                    chat_id=chat_id,
                    text=report_text,
                    parse_mode='MarkdownV2'
                )
                db.update_last_notified_aqi(user_id, current_aqi)
                logger.info(f"Уведомление отправлено пользователю {user_id} для {location_name} (AQI: {current_aqi}).")
        except Exception as e:
            logger.error(f"Ошибка при отправке уведомления для пользователя {user_id}: {e}", exc_info=True)


def main() -> None:
    """Запускает бота."""
    # Инициализация базы данных при запуске бота
    db.init_db()

    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    # Добавляем обработчик для команды /start
    application.add_handler(CommandHandler("start", start_command))

    # ConversationHandler для получения AQI
    # Теперь он обрабатывает как отправку локации, так и ввод названия
    aqi_conv_handler = ConversationHandler(
        entry_points=[
            MessageHandler(filters.Regex("^📊 Качество воздуха сейчас$"), aqi_command), # Кнопка "Качество воздуха сейчас"
            MessageHandler(filters.LOCATION, aqi_command), # Прямая отправка локации
            MessageHandler(filters.Regex("^🔎 Найти по названию$"), aqi_command) # Кнопка "Найти по названию"
        ],
        states={
            GET_LOCATION_FOR_AQI: [
                MessageHandler(filters.LOCATION, handle_location_input),
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_location_input),
                CallbackQueryHandler(handle_location_selection, pattern="^select_location_.*|^cancel_selection$")
            ],
        },
        fallbacks=[CommandHandler("cancel", start_command)],
    )
    application.add_handler(aqi_conv_handler)
    
    # Удаляем старый обработчик для кнопки "📊 Качество воздуха сейчас",
    # так как он теперь интегрирован в aqi_conv_handler
    # application.add_handler(MessageHandler(filters.Regex("^📊 Качество воздуха сейчас$"), 
    #                                        lambda update, context: update.message.reply_text(
    #                                            "Чтобы узнать качество воздуха, пожалуйста, **отправьте мне свою геопозицию** "
    #                                            "через кнопку скрепки (скрепка > Геопозиция) или **нажмите 'Найти по названию'** и введите название района."
    #                                        )))


    # Обработчики для новых кнопок "Рекомендации" и "О боте"
    application.add_handler(MessageHandler(filters.Regex("^💡 Рекомендации$"), show_recommendations))
    application.add_handler(MessageHandler(filters.Regex("^❓ О боте$"), show_about_bot))

    # Обработчики для подписок
    sub_conv_handler = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^🔔 Подписаться$"), subscribe_command)],
        states={
            GET_SUB_LOCATION: [
                MessageHandler(filters.LOCATION, handle_sub_location),
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_sub_location)
            ],
            GET_SUB_THRESHOLD: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_sub_threshold)]
        },
        fallbacks=[CommandHandler("cancel", start_command)]
    )
    application.add_handler(sub_conv_handler)
    application.add_handler(MessageHandler(filters.Regex("^🔕 Отписаться$"), unsubscribe_command))
    application.add_handler(MessageHandler(filters.Regex("^📋 Мои подписки$"), my_subscriptions_command))

    # Планируем фоновое задание для отправки уведомлений
    application.job_queue.run_repeating(send_aqi_notifications, interval=1800, first=60)
    logger.info("Задача по рассылке уведомлений запланирована.")


    logger.info("Бот запущен! Ожидание команд...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
