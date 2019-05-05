import logging
import os

import ccxt
import yaml

from tradeexecutor import CryptoExchange, TradeExecutor
from telegram_bot import TelegramBot


if __name__ == '__main__':
    logging.basicConfig(
        format='%(asctime)s - %(levelname)s - %(message)s',
        level=logging.INFO
    )
    c_dir = os.path.dirname(__file__)
    with open(os.path.join(c_dir, "..", "secret_key.yml")) as f:
        file_data = yaml.safe_load(f)

    ccxt_ex = ccxt.bitfinex()
    ccxt_ex.apiKey = file_data['api_key']
    ccxt_ex.secret = file_data['secret']

    exchange = CryptoExchange(ccxt_ex)
    trade_executor = TradeExecutor(exchange)
    telegram_bot = TelegramBot(
        file_data['telegram_ktn'],
        file_data['user_id'],
        trade_executor
    )

    telegram_bot.start_bot()