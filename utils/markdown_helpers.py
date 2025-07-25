# utils/markdown_helpers.py

def escape_markdown_v2(text: str) -> str:
    """
    Экранирует специальные символы MarkdownV2.
    Используется для любого текста, который будет отправлен с parse_mode='MarkdownV2',
    чтобы предотвратить ошибки парсинга Telegram.
    """
    escape_chars = r'_*[]()~`>#+-=|{}.!'
    return "".join(['\\' + char if char in escape_chars else char for char in text])

# Если понадобятся другие утилиты для Markdown, добавляем сюда.