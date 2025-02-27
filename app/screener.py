import ccxt
import pandas_ta as ta
import asyncio
import logging
from aiohttp import ClientSession
import pandas as pd
import requests

# Конфигурация API и Telegram
api_key = 'your_api_key'  # Ваш API ключ
api_secret = 'your_api_secret'  # Ваш API секрет
telegram_bot_token = 'your_telegram_bot_token'  # Токен вашего бота
telegram_chat_id = 'your_telegram_chat_id'  # Ваш chat ID для отправки уведомлений

# Подключаемся к Binance
exchange = ccxt.binance({
    'apiKey': api_key,
    'secret': api_secret,
    'enableRateLimit': True,
})

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Функция для отправки уведомлений в Telegram
def send_telegram_message(message):
    url = f'https://api.telegram.org/bot{telegram_bot_token}/sendMessage'
    payload = {
        'chat_id': telegram_chat_id,
        'text': message
    }
    try:
        response = requests.post(url, data=payload)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        logger.error(f"Ошибка при отправке уведомления в Telegram: {e}")

# Функция для получения данных с биржи (асинхронная версия)
async def get_market_data_async(symbol, session):
    try:
        ticker = await exchange.fetch_ticker(symbol)
        return ticker
    except Exception as e:
        logger.error(f"Ошибка при получении данных для {symbol}: {e}")
        return None

# Функция для вычисления технических индикаторов
def calculate_indicators(symbol, timeframe='5m', limit=100):
    ohlcv = exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)
    df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])

    # Индикаторы
    df['rsi'] = ta.rsi(df['close'], length=14)  # Индикатор RSI
    df['ma_50'] = ta.sma(df['close'], length=50)  # 50-периодная скользящая средняя
    df['ma_200'] = ta.sma(df['close'], length=200)  # 200-периодная скользящая средняя
    df['bb_upper'], df['bb_middle'], df['bb_lower'] = ta.bbands(df['close'], length=20, std=2)  # Bollinger Bands

    # Возвращаем последние значения индикаторов
    return df.iloc[-1]

# Функция для фильтрации инструментов с техническим индикатором
async def filter_markets_with_indicators(min_volume=1000000, max_spread=0.1, volatility_threshold=0.5, session=None):
    markets = exchange.load_markets()
    filtered_markets = []

    for symbol in markets:
        ticker = await get_market_data_async(symbol, session)
        if ticker:
            volume = ticker['quoteVolume']  # Объем торгов
            bid_ask_spread = ticker['ask'] - ticker['bid']  # Спред Bid/Ask
            price_change = ticker['percentage']  # Волатильность по % (изменение цены)
            
            # Рассчитываем технический индикатор
            indicators = calculate_indicators(symbol)

            # Проверка условий фильтрации
            if volume >= min_volume and bid_ask_spread <= max_spread and abs(price_change) >= volatility_threshold:
                # Проверка для RSI, MA и Bollinger Bands
                if indicators['rsi'] < 30 and indicators['ma_50'] > indicators['ma_200'] and indicators['close'] < indicators['bb_lower']:
                    filtered_markets.append({
                        'symbol': symbol,
                        'volume': volume,
                        'bid_ask_spread': bid_ask_spread,
                        'price_change': price_change,
                        'rsi': indicators['rsi'],
                        'ma_50': indicators['ma_50'],
                        'ma_200': indicators['ma_200'],
                        'bb_lower': indicators['bb_lower'],
                    })
    
    return filtered_markets

# Асинхронная функция для сканирования рынка
async def scan_market():
    async with ClientSession() as session:
        while True:
            logger.info("Сканирование рынка...")
            filtered_markets = await filter_markets_with_indicators(min_volume=1000000, max_spread=0.1, volatility_threshold=0.5, session=session)

            if filtered_markets:
                for market in filtered_markets:
                    message = (
                        f"🚀 Найден подходящий инструмент: {market['symbol']}\n"
                        f"Объем: {market['volume']}\n"
                        f"Спред: {market['bid_ask_spread']}\n"
                        f"Волатильность: {market['price_change']}%\n"
                        f"RSI: {market['rsi']}\n"
                        f"50 MA: {market['ma_50']}\n"
                        f"200 MA: {market['ma_200']}\n"
                        f"Bollinger Bands Lower: {market['bb_lower']}\n"
                    )
                    send_telegram_message(message)
                    logger.info(f"Отправлено уведомление в Telegram для {market['symbol']}")
            else:
                logger.info("Не найдено подходящих инструментов.")

            # Задержка для следующего сканирования
            await asyncio.sleep(30)

if __name__ == "__main__":
    # Запуск асинхронного сканера
    asyncio.run(scan_market())
