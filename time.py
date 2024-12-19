import schedule
import time
import asyncio

from Horoscope import main
# from test import main

# Асинхронный запуск основной задачи
def run_daily_task():
    print("Запуск задачи на отправку гороскопа и карты дня...")
    asyncio.run(main())

# Запуск задачи по расписанию в 9:01
schedule.every().day.at("08:29").do(run_daily_task)

print("Планировщик запущен. Ожидание следующего запуска...")

# Постоянный цикл для выполнения задач по расписанию
while True:
    schedule.run_pending()
    time.sleep(1)
