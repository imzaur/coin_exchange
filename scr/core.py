import asyncio
import logging

from ccxt import (
    Exchange,
    ExchangeError,
    OrderNotFound
)

from model import LongTrade, ShortTrade


class CryptoExchange(object):
    def __init__(self, exchange: Exchange):
        self.exchange = exchange
        self.exchange.load_markets()

    @property
    def free_balance(self):
        balance = self.exchange.fetch_free_balance()

        return {k: v for k, v in balance.items() if v > 0}

    def fetch_open_orders(self, symbol: str = None):
        return self.exchange.fetch_open_orders(symbol=symbol)

    def fetch_order(self, order_id: int):
        return self.exchange.fetch_open_order(order_id)

    def cancel_order(self, order_id: int):
        try:
            self.exchange.cancel_order(order_id)
        except OrderNotFound:
            pass

    def create_sell_order(self, symbol: str, amount: float, price: float):
        return self.exchange.create_order(
            symbol=symbol,
            type='limit',
            side='sell',
            amount=amount,
            price=price
        )

    def create_buy_order(self, symbol: str, amount: float, price: float):
        return self.exchange.create_order(
            symbol=symbol,
            type='limit',
            side='sell',
            amount=amount,
            price=price
        )


class TradeExecutor(object):
    def __init__(self, exchange, check_timeout: int = 15):
        self.check_timeout = check_timeout
        self.exchange = exchange

    async def execute_trade(self, trade):
        if isinstance(trade, ShortTrade):
            await self.execute_short_trade(trade)
        elif isinstance(trade, LongTrade):
            await self.execute_long_trade(trade)

    async def execute_short_trade(self, trade: ShortTrade):
        sell_price = trade.start_price
        buy_price = trade.exit_price
        symbol = trade.exchange_symbol
        amount = trade.amount

        order = self.exchange.create_sell_order(symbol, amount, price)
        logging.info(
            f'Opened sell order: {amount} of {symbol}. Target sell '
            f'{sell_price}, buy price {buy_price}'
        )

        await self._wait_order_complete(order['id'])

        order = self.exchange.create_buy_order(symbol, amount, price)

        await self._wait_order_complete(order['id'])
        logging.info(
            f'Completed short trade: {amount} of {symbol}. '
            f'Sold at {sell_price} and bought at {buy_price}'
        )

    async def execute_long_trade(self, trade: LongTrade):
        buy_price = trade.start_price
        sell_price = trade.exit_price



