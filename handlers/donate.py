# handlers/donate.py
from telegram import Update
from telegram.ext import ContextTypes
from utils.markdown_helpers import escape_markdown_v2 # Если будете использовать MarkdownV2 в тексте

async def donate_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Отправляет сообщение с информацией о пожертвованиях."""
    # Весь текст сообщения о пожертвованиях
    raw_donation_message = (
        "✨ *Ваша поддержка – это чистый воздух Бишкека!* ✨\n\n"
        "Привет! Мы, команда \"Бишкек ЭкоМонитор\", искренне благодарны за то, что вы с нами. "
        "Наш бот работает 24/7, чтобы каждый житель Бишкека имел доступ к актуальной информации "
        "о качестве воздуха и мог принимать осознанные решения для своего здоровья.\n\n"
        "Поддержание работы бота требует постоянных затрат: оплата серверов, "
        "доступа к данным и разработка новых, полезных функций. "
        "Мы стремимся не просто информировать, но и помогать вам дышать свободнее.\n\n"
        "Если вы цените наш вклад и хотите, чтобы бот продолжал развиваться "
        "и становился еще лучше (например, с более точными прогнозами, "
        "расширенным покрытием районов или функцией мониторинга воды), "
        "ваша помощь будет бесценна! Даже небольшой вклад помогает нам двигаться вперед и поддерживать проект.\n\n"
        "*Как вы можете помочь прямо сейчас:*\n"
        "💳 *MBank Online*: `[0779715638]`\n\n" # Оставил ваш номер, замените на актуальный
        "Этот бот был разработан [@abaikb]`\n\n" # Оставил ваш номер, замените на актуальный
        "Каждый ваш сом — это глоток свежего воздуха для Бишкека. "
        "Огромное спасибо за вашу поддержку, доверие и заботу о нашем общем будущем!\n"
        "С благодарностью,\n"
        "Команда \"Бишкек ЭкоМонитор\""
    )

    # Применяем escape_markdown_v2 ко всей строке сообщения
    donation_message = escape_markdown_v2(raw_donation_message)

    # Выбираем, куда отправить сообщение: в update.message или update.callback_query.message
    message_to_send = update.message
    if not message_to_send and update.callback_query:
        message_to_send = update.callback_query.message

    if message_to_send:
        await message_to_send.reply_markdown_v2(donation_message)
    else:
        # Fallback, если по какой-то причине нет ни update.message, ни update.callback_query.message
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=escape_markdown_v2("Не удалось отправить сообщение о донате. Пожалуйста, попробуйте еще раз."),
            parse_mode='MarkdownV2'
        )
