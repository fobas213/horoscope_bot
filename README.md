# horoscope_bot
Бот отправляющий ежедневный гороскоп в телеграм канал и бот для создания натальной карты, расчета совместимости, финансового расчета и сонник в телеграм.
Horoscope - скрипт на Python создающий гороскоп в виде изображжения для каждого знака зодиака, а так же выбирает карту таро дня. Карты таро сгенерированы с помощью Dalle и хранятся в отдельном репозитории. Формирование гороскопа происходит через OpenAI API.
Time - скрипт планировщик запускающий выполнение Horoscope по расписанию.
Starbutts - скрипт бота для телеграм создающий натальную карту, расчет совместимости, финансовый расчет и сонник. Логика работы: пользователь вводит свои данные по шаблону, идет расчет положения планет и звезд по api skyfield, после создания отчета, он отправляется на OpenAI API и по заданому промту создается интерпритация. 
Совместимость и финансовый расчет создаются по натальным картам.
