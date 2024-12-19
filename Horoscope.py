from PIL import Image, ImageDraw, ImageFont
import os
import openai
import asyncio
from telegram import Bot, InputMediaPhoto
import random
import time
from datetime import datetime

# API-ключи
TELEGRAM_BOT_TOKEN = ""
CHANNEL_ID = ""

# API-ключ OpenAI
openai.api_key = ""

# Папки для изображений
TEMP_IMAGE_PATH = "./horoscope_images"
TARO_PATH = os.path.join(os.path.expanduser("~"), "Desktop", "TARO")
os.makedirs(TEMP_IMAGE_PATH, exist_ok=True)

# Список знаков зодиака
ZODIAC_SIGNS = [
    "Овен", "Телец", "Близнецы", "Рак",
    "Лев", "Дева", "Весы", "Скорпион",
    "Стрелец", "Козерог", "Водолей", "Рыбы"
]

# Пример карт Таро
TARO_CARDS = [
    {"name": "Шут", "image": os.path.join(TARO_PATH, "fool.jpg.webp")},
    {"name": "Маг", "image": os.path.join(TARO_PATH, "magician.jpg.webp")},
    {"name": "Жрица", "image": os.path.join(TARO_PATH, "high_priestess.jpg.webp")},
    {"name": "Императрица", "image": os.path.join(TARO_PATH, "empress.jpg.webp")},
    {"name": "Император", "image": os.path.join(TARO_PATH, "emperor.jpg.webp")},
    {"name": "Иерофант", "image": os.path.join(TARO_PATH, "hierophant.jpg.webp")},
    {"name": "Влюблённые", "image": os.path.join(TARO_PATH, "lovers.jpg.webp")},
    {"name": "Колесница", "image": os.path.join(TARO_PATH, "chariot.jpg.webp")},
    {"name": "Сила", "image": os.path.join(TARO_PATH, "strength.jpg.webp")},
    {"name": "Отшельник", "image": os.path.join(TARO_PATH, "hermit.jpg.webp")},
    {"name": "Колесо Фортуны", "image": os.path.join(TARO_PATH, "wheel_of_fortune.jpg.webp")},
    {"name": "Справедливость", "image": os.path.join(TARO_PATH, "justice.jpg.webp")},
    {"name": "Повешенный", "image": os.path.join(TARO_PATH, "hanged_man.jpg.webp")},
    {"name": "Смерть", "image": os.path.join(TARO_PATH, "death.jpg.webp")},
    {"name": "Умеренность", "image": os.path.join(TARO_PATH, "temperance.jpg.webp")},
    {"name": "Дьявол", "image": os.path.join(TARO_PATH, "devil.jpg.webp")},
    {"name": "Башня", "image": os.path.join(TARO_PATH, "tower.jpg.webp")},
    {"name": "Звезда", "image": os.path.join(TARO_PATH, "star.jpg.webp")},
    {"name": "Луна", "image": os.path.join(TARO_PATH, "moon.jpg.webp")},
    {"name": "Солнце", "image": os.path.join(TARO_PATH, "sun.jpg.webp")},
    {"name": "Суд", "image": os.path.join(TARO_PATH, "judgment.jpg.webp")},
    {"name": "Мир", "image": os.path.join(TARO_PATH, "world.jpg.webp")},
]

# Генерация текущей даты
def get_today_date():
    return datetime.now().strftime("%d.%m.%Y")

# Функция для генерации гороскопа
def generate_horoscope(sign):
    prompt = f"Создай гороскоп на сегодня для знака зодиака {sign} в реалистичном стиле."
    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "Ты генератор гороскопов. Отвечай реалистично и разнообразно, кратко, без использования эмодзи, в первом предложении всегда упоминай к какому знаку относится прогноз"},
            {"role": "user", "content": prompt}
        ]
    )
    return response.choices[0].message.content

def create_horoscope_image(sign, text, output_path):
    img_width, img_height = 1080, 1080
    background_color = (255, 255, 255)  # Белый фон
    text_color = (0, 0, 0)  # Чёрный текст
    font_path = "/System/Library/Fonts/Supplemental/Arial.ttf"  # Проверьте путь шрифта
    title_font_size = 70  # Увеличенный шрифт для заголовка
    text_font_size = 40  # Обычный шрифт для текста
    line_spacing = 20  # Межстрочный интервал

    # Создание изображения
    image = Image.new("RGB", (img_width, img_height), color=background_color)
    draw = ImageDraw.Draw(image)
    try:
        title_font = ImageFont.truetype(font_path, title_font_size)
        text_font = ImageFont.truetype(font_path, text_font_size)
    except Exception as e:
        print(f"Ошибка загрузки шрифта: {e}")
        return

    # Рисуем заголовок
    title_bbox = draw.textbbox((0, 0), sign, font=title_font)
    title_width = title_bbox[2] - title_bbox[0]
    title_x = (img_width - title_width) / 2
    title_y = 50  # Отступ сверху для заголовка
    draw.text((title_x, title_y), sign, font=title_font, fill=text_color)

    # Разбиение текста на строки
    max_text_width = img_width - 100
    words = text.split()
    lines = []
    current_line = ""

    for word in words:
        test_line = f"{current_line} {word}".strip()
        test_line_bbox = draw.textbbox((0, 0), test_line, font=text_font)
        test_line_width = test_line_bbox[2] - test_line_bbox[0]
        if test_line_width <= max_text_width:
            current_line = test_line
        else:
            lines.append(current_line)
            current_line = word
    lines.append(current_line)

    # Центрирование текста ниже заголовка
    text_y_start = title_y + title_font_size + 50  # Отступ после заголовка
    total_text_height = len(lines) * (text_font_size + line_spacing)
    y_offset = text_y_start + (img_height - text_y_start - total_text_height) // 2

    for line in lines:
        line_bbox = draw.textbbox((0, 0), line, font=text_font)
        line_width = line_bbox[2] - line_bbox[0]
        draw.text(((img_width - line_width) / 2, y_offset), line, font=text_font, fill=text_color)
        y_offset += text_font_size + line_spacing

    try:
        image.save(output_path)
        print(f"Изображение сохранено: {output_path}")
    except Exception as e:
        print(f"Ошибка сохранения изображения: {e}")




# # Функция для генерации влияния ретроградного Меркурия
# def generate_mercury_effect():
#     prompt = "Опиши влияние ретроградного Меркурия на каждый знак зодиака сегодня."
#     response = openai.ChatCompletion.create(
#         model="gpt-3.5-turbo",
#         messages=[
#             {"role": "system", "content": "Ты эксперт по астрологии. Отвечай кратко и структурированно."},
#             {"role": "user", "content": prompt}
#         ]
#     )
#     return response.choices[0].message.content

# Асинхронная функция для отправки медиа
async def send_media_in_batches(bot, chat_id, media_files, batch_size=6, delay=5):
    for i in range(0, len(media_files), batch_size):
        batch = media_files[i:i + batch_size]
        media_group = [InputMediaPhoto(open(file, "rb")) for file in batch]
        try:
            await bot.send_media_group(chat_id=chat_id, media=media_group)
            print(f"Отправлена группа из {len(batch)} изображений.")
        except Exception as e:
            print(f"Ошибка при отправке группы: {e}")
        await asyncio.sleep(delay)

# Генерация карты дня
async def generate_card_of_the_day(bot):
    card = random.choice(TARO_CARDS)
    card_name = card["name"]
    card_image = card["image"]

    # Генерация описания карты
    prompt = f"Создай описание для карты Таро '{card_name}', объясни её значение и советы на день."
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "Ты эксперт по картам Таро. Отвечай кратко и ясно."},
            {"role": "user", "content": prompt}
        ]
    )
    card_description = response.choices[0].message.content

    # Отправка карты дня
    try:
        with open(card_image, "rb") as image_file:
            await bot.send_photo(
                chat_id=CHANNEL_ID,
                photo=image_file,
                caption=f"🌟 Карта дня ({get_today_date()}): {card_name}\n\n{card_description}"
            )
        print("Карта дня отправлена.")
    except Exception as e:
        print(f"Ошибка при отправке карты дня: {e}")

# # Генерация влияния ретроградного Меркурия
# async def generate_mercury_message(bot):
#     mercury_effect = generate_mercury_effect()
#     try:
#         await bot.send_message(
#             chat_id=CHANNEL_ID,
#             text=f"📅 Влияние Ретроградного Меркурия ({get_today_date()}):\n\n{mercury_effect}"
#         )
#         print("Влияние ретроградного Меркурия отправлено.")
#     except Exception as e:
#         print(f"Ошибка при отправке влияния ретроградного Меркурия: {e}")

# Основной процесс
async def main():
    bot = Bot(token=TELEGRAM_BOT_TOKEN)

    # Гороскопы
    horoscope_images = []
    for sign in ZODIAC_SIGNS:
        try:
            horoscope_text = generate_horoscope(sign)
            output_path = os.path.join(TEMP_IMAGE_PATH, f"{sign}.jpg")
            create_horoscope_image(sign, horoscope_text, output_path)
            horoscope_images.append(output_path)
        except Exception as e:
            print(f"Ошибка при создании гороскопа для {sign}: {e}")

    # Отправка гороскопов
    await send_media_in_batches(bot, CHANNEL_ID, horoscope_images)

    # Карта дня
    await generate_card_of_the_day(bot)

    # # Влияние ретроградного Меркурия
    # await generate_mercury_message(bot)

# Запуск
if __name__ == "__main__":
    asyncio.run(main())
