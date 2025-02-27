# Используем базовый образ Python
FROM python:3.10-slim

# Устанавливаем зависимости для работы с CCXT и Telegram
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем скрипт в контейнер
COPY screener.py .

# Определяем переменные окружения
ENV API_KEY=""
ENV API_SECRET=""
ENV TELEGRAM_BOT_TOKEN=""
ENV TELEGRAM_CHAT_ID=""

# Запускаем скрипт при старте контейнера
CMD ["python", "screener.py"]
