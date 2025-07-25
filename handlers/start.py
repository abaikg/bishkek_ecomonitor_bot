# handlers/start.py
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import ContextTypes
from utils.markdown_helpers import escape_markdown_v2

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обрабатывает команду /start и отображает основное меню."""
    user = update.effective_user

    keyboard = [
        [
            KeyboardButton("📊 Качество воздуха сейчас"),
        ],
        [
            KeyboardButton("📍 Отправить мою локацию"),
            KeyboardButton("🔎 Найти по названию")
        ],
        [
            KeyboardButton("🔔 Подписаться"),
            KeyboardButton("🔕 Отписаться"),
            KeyboardButton("📋 Мои подписки")
        ],
        [
            KeyboardButton("💡 Рекомендации"),
            KeyboardButton("❓ О боте")
        ],
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False)

    await update.message.reply_html(
        f"Привет, {user.mention_html()}! 👋\n"
        "Я твой личный помощник по **мониторингу качества воздуха и воды** в Бишкеке.\n"
        "Выбери действие из меню ниже, чтобы узнать актуальную информацию или получить полезные советы.\n\n"
        "Для управления уведомлениями о качестве воздуха используй кнопки подписки\\."
        ,
        reply_markup=reply_markup
    )
