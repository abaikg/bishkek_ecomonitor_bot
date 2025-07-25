# handlers/start.py
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import ContextTypes
from utils.markdown_helpers import escape_markdown_v2

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обрабатывает команду /start и отображает основное меню."""
    user = update.effective_user

    # Определяем, какой объект сообщения использовать для ответа
    # Если это прямое сообщение, используем update.message
    # Если это callback_query, используем update.callback_query.message
    message_to_reply = update.message
    if not message_to_reply and update.callback_query:
        message_to_reply = update.callback_query.message

    # Запасной вариант, если ни один объект сообщения недоступен (в идеале не должно происходить, но для надежности)
    if not message_to_reply:
        # Если мы действительно не можем найти объект сообщения для ответа, отправляем новое сообщение
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=f"Привет, {user.mention_html()}! 👋\nЯ здесь, чтобы помочь. Выбери действие из меню ниже.",
            parse_mode='HTML'
        )
        return

    keyboard = [
        [
            KeyboardButton("📊 Качество воздуха сейчас"),
        ],
        [
            KeyboardButton("📍 Отправить мою локацию"),
            KeyboardButton("◀️ Назад"),
            KeyboardButton("🔎 Найти по названию")
        ],
        [
            KeyboardButton("🔔 Подписаться"),
            KeyboardButton("🔕 Отписаться"),
            KeyboardButton("📋 Мои подписки")
        ],
        [
            KeyboardButton("💡 Рекомендации"),
            KeyboardButton("❓ О боте"),
            KeyboardButton("💖 Поддержать проект")
        ],
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False)

    await message_to_reply.reply_html( # Используем определенный объект message_to_reply
        f"Привет, {user.mention_html()}! 👋\n"
        "Я твой личный помощник по **мониторингу качества воздуха и воды** в Бишкеке.\n"
        "Выбери действие из меню ниже, чтобы узнать актуальную информацию или получить полезные советы.\n\n"
        "Для управления уведомлениями о качестве воздуха используй кнопки подписки\\."
        ,
        reply_markup=reply_markup
    )
