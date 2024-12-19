import logging
import swisseph as swe
from geopy.geocoders import Nominatim
from timezonefinder import TimezoneFinder
from pytz import timezone, utc
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
import openai
import os
from dotenv import load_dotenv
from fpdf import FPDF
from skyfield.api import load
from datetime import datetime
from telegram import ReplyKeyboardMarkup


# Загрузка переменных окружения
load_dotenv()

# Укажите токены
BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
openai.api_key = OPENAI_API_KEY

# Логирование
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Отключаем HTTP-логи
logging.getLogger('httpx').setLevel(logging.WARNING)
logging.getLogger('urllib3').setLevel(logging.WARNING)

# Установка пути к файлам эфемерид
swe.set_ephe_path('./ephemeris')

# Инициализация Geopy и TimezoneFinder
geolocator = Nominatim(user_agent="astro_app")
tf = TimezoneFinder()


# Преобразование градуса в знак зодиака
def degree_to_sign(degree):
    signs = [
        "Овен", "Телец", "Близнецы", "Рак",
        "Лев", "Дева", "Весы", "Скорпион",
        "Стрелец", "Козерог", "Водолей", "Рыбы"
    ]
    sign_index = int(degree // 30)
    degree_in_sign = degree % 30
    return f"{signs[sign_index]} {degree_in_sign:.2f}°"


# Функция для получения координат и часового пояса
def get_coordinates_and_timezone(location_name):
    location = geolocator.geocode(location_name)
    if not location:
        raise ValueError(f"Место не найдено: {location_name}")

    latitude = location.latitude
    longitude = location.longitude

    tz_name = tf.timezone_at(lng=longitude, lat=latitude)
    if not tz_name:
        raise ValueError(f"Не удалось определить часовой пояс для координат: {latitude}, {longitude}")

    return latitude, longitude, tz_name


# Функция для конвертации времени в UTC
def convert_to_utc(date, time, tz_name):
    local_tz = timezone(tz_name)
    local_time = datetime.strptime(f"{date} {time}", "%d.%m.%Y %H:%M")
    local_time = local_tz.localize(local_time)
    utc_time = local_time.astimezone(utc)
    return utc_time


# Расчёт натальной карты
def calculate_chart(year, month, day, hour, latitude, longitude):
    julian_day = swe.julday(year, month, day, hour)
    planets = {
        "Солнце": swe.SUN,
        "Луна": swe.MOON,
        "Меркурий": swe.MERCURY,
        "Венера": swe.VENUS,
        "Марс": swe.MARS,
        "Юпитер": swe.JUPITER,
        "Сатурн": swe.SATURN,
        "Уран": swe.URANUS,
        "Нептун": swe.NEPTUNE,
        "Плутон": swe.PLUTO,
    }
    chart = {}
    for planet_name, planet_code in planets.items():
        planet_pos = swe.calc_ut(julian_day, planet_code)[0][0]
        chart[planet_name] = degree_to_sign(planet_pos)

    return chart


# Расчёт домов
def calculate_houses(year, month, day, hour, latitude, longitude):
    julian_day = swe.julday(year, month, day, hour)
    house_positions = swe.houses(julian_day, latitude, longitude, b'P')  # Система домов Плацидуса
    house_cusps = house_positions[0]  # Границы домов
    ascendant = degree_to_sign(house_positions[1][0])  # Асцендент
    houses = {f"Дом {i+1}": degree_to_sign(house_cusps[i]) for i in range(len(house_cusps))}
    return houses, ascendant


# Функция для создания PDF
def create_pdf(chart, houses, ascendant, detailed_interpretation):
    pdf = FPDF()
    pdf.add_page()

    # Указываем путь к шрифтам
    pdf.add_font('DejaVu', '', './fonts/DejaVuSans.ttf', uni=True)
    pdf.add_font('DejaVu', 'B', './fonts/DejaVuSans-Bold.ttf', uni=True)
    pdf.add_font('DejaVu', 'I', './fonts/DejaVuSans-Oblique.ttf', uni=True)
    pdf.set_font("DejaVu", size=12)

    pdf.cell(200, 10, txt="Натальная карта", ln=True, align='C')
    pdf.ln(10)

    pdf.set_font("DejaVu", style="B", size=12)
    pdf.cell(200, 10, txt="Планеты и Асцендент", ln=True, align='L')
    pdf.set_font("DejaVu", size=12)
    for key, value in chart.items():
        pdf.cell(200, 10, txt=f"{key}: {value}", ln=True, align='L')

    pdf.ln(10)
    pdf.set_font("DejaVu", style="B", size=12)
    pdf.cell(200, 10, txt="Дома", ln=True, align='L')
    pdf.set_font("DejaVu", size=12)
    for key, value in houses.items():
        pdf.cell(200, 10, txt=f"{key}: {value}", ln=True, align='L')

    pdf.cell(200, 10, txt=f"Асцендент: {ascendant}", ln=True, align='L')

    pdf.ln(10)
    pdf.set_font("DejaVu", style="B", size=12)
    pdf.cell(200, 10, txt="Детальная интерпретация", ln=True, align='L')
    pdf.set_font("DejaVu", size=12)
    pdf.multi_cell(0, 10, detailed_interpretation)

    file_path = "./natal_chart.pdf"
    pdf.output(file_path)
    return file_path


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Создаем клавиатуру с кнопкой "Старт"
    reply_keyboard = [["Старт"]]
    markup = ReplyKeyboardMarkup(reply_keyboard, resize_keyboard=True, one_time_keyboard=False)

    # Inline-клавиатура для выбора действий
    keyboard = [
        [InlineKeyboardButton("Создать натальную карту", callback_data='create_chart')],
        [InlineKeyboardButton("Расчет совместимости", callback_data='calculate_compatibility')],
        [InlineKeyboardButton("Финансовый расклад", callback_data='financial_analysis')],
        [InlineKeyboardButton("Толкование сна", callback_data='dream_interpretation')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    # Отправляем сообщение с основным меню
    await update.message.reply_text(
        "Добро пожаловать! Выберите действие:",
        reply_markup=reply_markup
    )

    # Добавляем кнопку "Старт" для повторного запуска
    await update.message.reply_text(
        "Для перезапуска меню нажмите 'Старт'.",
        reply_markup=markup
    )


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == 'create_chart':
        await query.message.reply_text(
            "Введите данные в формате:\nИмя, Дата рождения (ДД.ММ.ГГГГ), Время рождения (ЧЧ:ММ), Город\n"
            "Пример: Екатерина, 01.10.2002, 14:10, Москва"
        )
        context.user_data['awaiting_data'] = 'individual'

    elif query.data == 'calculate_compatibility':
        await query.message.reply_text(
            "Введите данные первого человека в формате:\nИмя, Дата рождения (ДД.ММ.ГГГГ), Время рождения (ЧЧ:ММ), Город\n"
            "Пример: Екатерина, 01.10.2002, 14:10, Москва"
        )
        context.user_data['awaiting_data'] = 'person1'

    elif query.data == 'financial_analysis':
        await query.message.reply_text(
            "Введите данные в формате:\nИмя, Дата рождения (ДД.ММ.ГГГГ), Время рождения (ЧЧ:ММ), Город\n"
            "Пример: Иван, 01.01.1990, 12:00, Москва"
        )
        context.user_data['awaiting_data'] = 'financial'

    elif query.data == 'dream_interpretation':
        await query.message.reply_text(
            "Введите описание вашего сна. Например: \"Я видел, как летал над лесом, а затем встретил белую лошадь.\""
        )
        context.user_data['awaiting_data'] = 'dream'


from telegram import ReplyKeyboardMarkup

# Обработчик сообщений с добавлением кнопки "Старт"
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Логируем данные, введенные пользователем
    user_input = update.message.text.strip().lower()
    user_name = update.message.from_user.full_name
    logger.info(f"Ввод пользователя: {user_name} - {user_input}")

    # Кнопка "Старт" перезапускает главное меню
    if user_input == "старт":
        await start(update, context)
        return

    if context.user_data.get('awaiting_data') == 'individual':
        await calculate_individual_chart(update, context)

    elif context.user_data.get('awaiting_data') == 'financial':
        try:
            # Парсим данные пользователя
            data = user_input.split(",")
            if len(data) != 4:
                await update.message.reply_text(
                    "Ошибка! Формат ввода: Имя, Дата рождения (ДД.ММ.ГГГГ), Время (ЧЧ:ММ), Город"
                )
                return

            name, date, time, location = map(str.strip, data)
            logger.info(f"Пользователь {user_name} ввел данные для финансового анализа: Имя={name}, Дата={date}, Время={time}, Город={location}")

            # Получаем координаты и часовой пояс
            latitude, longitude, tz_name = get_coordinates_and_timezone(location)

            # Конвертируем время в UTC
            utc_time = convert_to_utc(date, time, tz_name)

            # Вызываем функцию анализа
            await calculate_financial_analysis(update, context, name, utc_time, latitude, longitude)

        except Exception as e:
            logger.error(f"Ошибка обработки данных: {str(e)}")
            await update.message.reply_text("Произошла ошибка. Проверьте формат ввода.")

    elif context.user_data.get('awaiting_data') == 'person1':
        # Сохраняем данные первого человека
        context.user_data['person1_data'] = user_input
        logger.info(f"Пользователь {user_name} ввел данные для первого человека: {user_input}")
        await update.message.reply_text(
            "Введите данные второго человека в формате:\nИмя, Дата рождения (ДД.ММ.ГГГГ), Время рождения (ЧЧ:ММ), Город\n"
            "Пример: Иван, 05.06.1990, 10:30, Санкт-Петербург"
        )
        context.user_data['awaiting_data'] = 'person2'

    elif context.user_data.get('awaiting_data') == 'person2':
        # Сохраняем данные второго человека
        context.user_data['person2_data'] = user_input
        logger.info(f"Пользователь {user_name} ввел данные для второго человека: {user_input}")
        await calculate_compatibility(update, context)
        context.user_data['awaiting_data'] = None  # Сбрасываем состояние

    elif context.user_data.get('awaiting_data') == 'dream':
        logger.info(f"Пользователь {user_name} ввел описание сна: {user_input}")
        await interpret_dream(update, context)
        context.user_data['awaiting_data'] = None  # Сбрасываем состояние

    else:
        # Сообщение, если пользователь ввел что-то некорректное
        reply_keyboard = [["Старт"]]
        markup = ReplyKeyboardMarkup(reply_keyboard, resize_keyboard=True, one_time_keyboard=False)
        await update.message.reply_text(
            "Непонятный запрос. Нажмите 'Старт', чтобы вернуться в главное меню.",
            reply_markup=markup
        )


async def interpret_dream(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        # Получаем описание сна от пользователя
        dream_description = update.message.text

        # Генерация толкования сна через OpenAI API
        dream_prompt = (
            f"Ты профессиональный толкователь снов. Пользователь описал свой сон следующим образом:\n"
            f"\"{dream_description}\"\n"
            f"Пожалуйста, дай подробное, но реалистичное толкование этого сна, выдели основные символы и их значение, "
            f"а также общий смысл сна и возможные рекомендации для пользователя."
        )

        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[{"role": "user", "content": dream_prompt}],
            max_tokens=1500
        )

        interpretation = response['choices'][0]['message']['content'].strip()

        # Отправка толкования пользователю
        await update.message.reply_text(f"Толкование сна:\n\n{interpretation}")

    except Exception as e:
        logger.error(f"Ошибка толкования сна: {str(e)}")
        await update.message.reply_text("Произошла ошибка при толковании сна. Пожалуйста, попробуйте снова.")


async def calculate_individual_chart(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        # Парсим данные
        data = update.message.text.split(",")
        if len(data) != 4:
            await update.message.reply_text(
                "Ошибка! Формат ввода: Имя, Дата рождения (ДД.ММ.ГГГГ), Время (ЧЧ:ММ), Город"
            )
            return

        name, date, time, location = map(str.strip, data)

        # Получаем координаты и часовой пояс
        latitude, longitude, tz_name = get_coordinates_and_timezone(location)

        # Конвертируем время в UTC
        utc_time = convert_to_utc(date, time, tz_name)

        # Рассчитываем натальную карту
        hour_utc = utc_time.hour + utc_time.minute / 60.0
        chart = calculate_chart(utc_time.year, utc_time.month, utc_time.day, hour_utc, latitude, longitude)

        # Рассчитываем дома
        houses, ascendant = calculate_houses(utc_time.year, utc_time.month, utc_time.day, hour_utc, latitude, longitude)

        # Формируем вывод для пользователя
        result = "\n".join([f"{key}: {value}" for key, value in chart.items()])
        house_data = "\n".join([f"{key}: {value}" for key, value in houses.items()])
        await update.message.reply_text(
            f"Рассчитанные данные:\n\nПланеты:\n{result}\n\nДома:\n{house_data}\n\nАсцендент: {ascendant}"
        )

        # Запрос краткой интерпретации
        short_prompt = (
            f"Ты профессиональный астролог. Твоя задача — составить краткую, но реалистичную, убедительную и грамотно структурированную натальную карту "
            f"на основе предоставленных данных. Структура ответа должна состоять из 8 пунктов описывающих влияние планет,пункта асцендента, а в конце общий вывод. Используй классические астрологические трактовки, уделяя внимание каждому аспекту, "
            f"взаимодействиям планет и их влиянию на личность. ответ должен быть до 4000 символов. Избегай противоречий в трактовках. "
            f"Вот данные:\nПланеты:\n{result}\nАсцендент: {ascendant}"
        )
        short_response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": short_prompt}],
            max_tokens=1500
        )
        short_interpretation = short_response['choices'][0]['message']['content'].strip()
        await update.message.reply_text(f"Краткая интерпретация:\n{short_interpretation}")

        # Полная интерпретация
        detailed_prompt = (
            f"Ты профессиональный астролог. Твоя задача — составить полную, реалистичную, убедительную и грамотно структурированную натальную карту "
            f"на основе предоставленных данных. Структура ответа должна содержать: полное и детальное описание 10 планет, Детальное описание каждого дома по пунктам, общий полный вывод по всему описанию. Используй классические астрологические трактовки."
            f"Ответ должен быть максимально полным и не противоречить краткому."
            f"Планеты:\n{result}\nДома:\n{house_data}\nАсцендент: {ascendant}"
        )
        detailed_response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[{"role": "user", "content": detailed_prompt}],
            max_tokens=3000
        )
        detailed_interpretation = detailed_response['choices'][0]['message']['content'].strip()

        # Создаем PDF
        pdf_path = create_pdf(chart, houses, ascendant, detailed_interpretation)

        # Отправляем PDF пользователю
        await update.message.reply_document(document=pdf_path)

    except Exception as e:
        logger.error(f"Ошибка обработки данных: {str(e)}")
        await update.message.reply_text("Произошла ошибка. Проверьте формат ввода.")


async def calculate_compatibility(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        # Извлекаем данные
        person1_data = context.user_data['person1_data'].split(",")
        person2_data = context.user_data['person2_data'].split(",")

        if len(person1_data) != 4 or len(person2_data) != 4:
            await update.message.reply_text(
                "Ошибка! Проверьте формат ввода данных для обоих людей."
            )
            return

        # Получаем координаты, UTC и натальные карты для обоих
        name1, date1, time1, location1 = map(str.strip, person1_data)
        latitude1, longitude1, tz_name1 = get_coordinates_and_timezone(location1)
        utc_time1 = convert_to_utc(date1, time1, tz_name1)
        hour_utc1 = utc_time1.hour + utc_time1.minute / 60.0
        chart1 = calculate_chart(utc_time1.year, utc_time1.month, utc_time1.day, hour_utc1, latitude1, longitude1)

        name2, date2, time2, location2 = map(str.strip, person2_data)
        latitude2, longitude2, tz_name2 = get_coordinates_and_timezone(location2)
        utc_time2 = convert_to_utc(date2, time2, tz_name2)
        hour_utc2 = utc_time2.hour + utc_time2.minute / 60.0
        chart2 = calculate_chart(utc_time2.year, utc_time2.month, utc_time2.day, hour_utc2, latitude2, longitude2)

        # Анализ совместимости
        compatibility_prompt = (
            f"Ты астрологический эксперт. Сделай полный и подробный анализ совместимости на основе данных двух натальных карт. \n"
            f"Данные первого человека:\nПланеты:\n{chart1}\n"
            f"Данные второго человека:\nПланеты:\n{chart2}\n"
            "Опиши совместимость, выделив сильные и слабые стороны взаимодействия. Описывай черты характера и сопоставляй их. Давай больше индивидуальной конкретики. Например: первый человек идеен и оптимистичен, второй предпочитает комфорт и бездятельность, это негативно влияет на совместимость."
        )
        compatibility_response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[{"role": "user", "content": compatibility_prompt}],
            max_tokens=2000
        )
        compatibility_text = compatibility_response['choices'][0]['message']['content'].strip()

        # Отправляем пользователю результат
        await update.message.reply_text(f"Совместимость:\n\n{compatibility_text}")
    except Exception as e:
        logger.error(f"Ошибка расчета совместимости: {str(e)}")
        await update.message.reply_text("Произошла ошибка при расчете совместимости.")

from datetime import datetime

async def calculate_financial_analysis(update: Update, context: ContextTypes.DEFAULT_TYPE, name: str, utc_time: datetime, latitude: float, longitude: float):
    try:
        # Используем текущую дату и время, если это необходимо
        current_time = datetime.utcnow()

        # Часовой расчет времени
        hour_utc = current_time.hour + current_time.minute / 60.0

        # Расчет натальной карты
        chart = calculate_chart(current_time.year, current_time.month, current_time.day, hour_utc, latitude, longitude)

        # Расчет домов
        houses, ascendant = calculate_houses(current_time.year, current_time.month, current_time.day, hour_utc, latitude, longitude)

        # Формируем текстовый вывод
        chart_output = "\n".join([f"{key}: {value}" for key, value in chart.items()])
        houses_output = "\n".join([f"{key}: {value}" for key, value in houses.items()])

        # Генерация интерпретации финансовой карты
        prompt = (
            f"Ты профессиональный финансовый астролог. Составь финансовую интерпретацию на основе натальной карты "
            f"для {name}. Используй текущую дату ({current_time.strftime('%d.%m.%Y %H:%M UTC')}) и данные:\n"
            f"Расположение планет:\n{chart_output}\n"
            f"Дома:\n{houses_output}\nАсцендент: {ascendant}.\n"
            f"Опиши основные сильные и слабые стороны финансового положения и дай рекомендации. Сохраняй структуру - сильные стороны, слабые стороны, рекомендации. Давай больше конкретных рекомендаций. Пиши текст как человек, четко обращаясь к клиенту"
        )

        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=1500
        )

        interpretation = response['choices'][0]['message']['content'].strip()

        # Отправка результата пользователю
        await update.message.reply_text(
            f"Финансовый расклад для {name}:\n\n"
            f"Планеты:\n{chart_output}\n\n"
            # f"Дома:\n{houses_output}\n\n"
            # f"Асцендент: {ascendant}\n\n"
            f"\n{interpretation}"
        )

    except Exception as e:
        logger.error(f"Ошибка финансового анализа: {e}")
        await update.message.reply_text("Произошла ошибка при расчете финансового расклада. Проверьте данные.")


# Основной запуск бота
def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    app.run_polling()


if __name__ == "__main__":
    main()
