import asyncio
import logging

from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    BaseFilter,
    CallbackQueryHandler,
    CommandHandler,
    ConversationHandler,
    MessageHandler,
    Updater,
    Filters,
    run_async
)

import config
from exchange import LongTrade, ShortTrade
from tradeexecutor import TradeExecutor
import utils


class TelegramBot(object):
    class PrivateUserFilter(BaseFilter):
        def __init__(self, user_id):
            self.user_id = int(user_id)

        def filter(self, message):
            return message.from_user.id == self.user_id

    def __init__(
            self,
            token: str,
            allowed_user_id,
            trade_executor: TradeExecutor
    ):
        self.updater = Updater(token=token)
        self.dispatcher = self.updater.dispatcher
        self.trade_executor = trade_executor
        self.exchange = self.trade_executor.exchange
        self.private_filter = self.PrivateUserFilter(allowed_user_id)
        self._prepare()

    def _prepare(self):

        def show_help(bot, update):
            update.effective_message.reply_text('Type /trade to show options')

        def show_options(bot, update):
            button_list = [
                [InlineKeyboardButton("Short trade",
                                      callback_data=config.SHORT_TRADE),
                 InlineKeyboardButton("Long trade",
                                      callback_data=config.LONG_TRADE), ],
                [InlineKeyboardButton("Open orders",
                                      callback_data=config.OPEN_ORDERS),
                 InlineKeyboardButton("Available balance",
                                      callback_data=config.FREE_BALANCE)],
            ]

            update.message.reply_text(
                "Trade options:",
                reply_markup=InlineKeyboardMarkup(button_list)
            )
            return config.SELECTION

        def process_trade_selection(bot, update, user_data):
            query = update.callback_query
            selection = query.data

            if selection == config.OPEN_ORDERS:
                orders = self.exchange.fetch_open_orders()

                if len(orders) == 0:
                    bot.edit_message_text(
                        text="No any open orders",
                        chat_id=query.message.chat_id,
                        message_id=query.message.message_id
                    )
                    return ConversationHandler.END

                keyboard = [
                    [InlineKeyboardButton("Ok",
                                          callback_data=config.CONFIRM),
                     InlineKeyboardButton("Cancel order",
                                          callback_data=config.CANCEL)]
                ]

                bot.edit_message_text(
                    text=utils.format_open_orders(orders),
                    chat_id=query.message.chat_id,
                    message_id=query.message.message_id,
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
                user_data[config.OPEN_ORDERS] = orders
                return config.CANCEL_ORD

            elif selection == config.FREE_BALANCE:
                balance = self.exchange.free_balance

                if len(balance) == 0:
                    msg = "You don't have any available balance"
                else:
                    msg = f"Your available balance: " \
                        f"\n{utils.format_balance(balance)}"

                bot.edit_message_text(
                    text=msg,
                    chat_id=query.message.chat_id,
                    message_id=query.message.message_id
                )
                return ConversationHandler.END

            user_data[config.SELECTION] = selection
            bot.edit_message_text(
                text=f'Enter coin name for {selection}',
                chat_id=query.message.chat_id,
                message_id=query.message.message_id
            )

            return config.COIN_NAME

        def cancel_order(bot, update):
            query = update.callback_query

            if query.data == config.CANCEL:
                query.message.reply_text("Enter order index to cancel")
                return config.PROCESS_ORD_CANCEL

            show_help(bot, update)
            return ConversationHandler.END

        def process_order_cancel(bot, update, user_data):
            idx = int(update.message.text)
            order = user_data[config.OPEN_ORDERS][idx]
            self.exchange.cancel_order(order['id'])
            update.message.reply_text(
                f'Canceled order: {utils.format_order(order)}'
            )
            return ConversationHandler.END

        def process_coin_name(bot, update, user_data):
            user_data[config.COIN_NAME] = update.message.text.upper()
            update.message.reply_text(
                f'What amount of {user_data[config.COIN_NAME]}'
            )
            return config.AMOUNT

        def process_amount(bot, update, user_data):
            user_data[config.AMOUNT] = float(update.message.text)
            update.message.reply_text(
                f'What percent change for {user_data[config.AMOUNT]} '
                f'{user_data[config.COIN_NAME]}'
            )
            return config.PERCENT_CHANGE

        def process_percent(bot, update, user_data):
            user_data[config.PERCENT_CHANGE] = float(update.message.text)
            update.message.reply_text(
                f'What price for 1 unit of {user_data[config.COIN]}'
            )
            return config.PRICE

        def process_price(bot, update, user_data):
            user_data[config.PRICE] = float(update.message.text)

            keyboard = [
                [InlineKeyboardButton("Confirm",
                                      callback_data=config.CONFIRM),
                 InlineKeyboardButton("Cancel",
                                      callback_data=config.CANCEL)]
            ]

            update.message.reply_text(
                f"Confirm the trade: '{TelegramBot.build_trade(user_data)}'",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            return config.PROCESS_TRADE

        def process_trade(bot, update, user_data):
            query = update.callback_query

            if query.data == config.CONFIRM:
                trade = TelegramBot.build_trade(user_data)
                self._execute_trade(trade)
                update.callback_query.message.reply_text(f'Scheduled: {trade}')
            else:
                show_help(bot, update)

            return ConversationHandler.END

        def handle_error(bot, update, error):
            logging.warning('Update "%s" caused error "%s"', update, error)
            update.message.reply_text(f'Unexpected error:\n{error}')

        def build_conversation_handler():
            entry_handler = CommandHandler(
                'trade',
                filters=self.private_filter,
                callback=show_options
            )
            conversation_handler = ConversationHandler(
                entry_points=[entry_handler],
                fallbacks=[entry_handler],
                states={
                    config.SELECTION: [CallbackQueryHandler(
                        process_trade_selection,
                        pass_user_data=True
                    )],
                    config.CANCEL_ORD: [CallbackQueryHandler(
                        cancel_order,
                        pass_user_data=True
                    )],
                    config.PROCESS_ORD_CANCEL: [MessageHandler(
                        filters=Filters.text,
                        callback=process_order_cancel,
                        pass_user_data=True
                    )],
                    config.COIN_NAME: [MessageHandler(
                        filters=Filters.text,
                        callback=process_coin_name,
                        pass_user_data=True
                    )],
                    config.AMOUNT: [MessageHandler(
                        filters=Filters.text,
                        callback=process_amount,
                        pass_user_data=True
                    )],
                    config.PERCENT_CHANGE: [MessageHandler(
                        filters=Filters.text,
                        callback=process_percent,
                        pass_user_data=True
                    )],
                    config.PRICE: [MessageHandler(
                        filters=Filters.text,
                        callback=process_price,
                        pass_user_data=True
                    )],
                    config.PROCESS_TRADE: [CallbackQueryHandler(
                        process_trade,
                        pass_user_data=True
                    )]
                }
            )

            return conversation_handler

        self.dispatcher.add_handler(CommandHandler(
            'start',
            filters=Filters.text,
            callback=show_help
        ))
        self.dispatcher.add_handler(build_conversation_handler())
        self.dispatcher.add_error_handler(handle_error)

    def start_bot(self):
        self.updater.start_polling()

    @run_async
    def _execute_trade(self, trade):
        loop = asyncio.new_event_loop()
        task = loop.create_task(self.trade_executor.execute_trade(trade))
        loop.run_until_complete(task)

    @staticmethod
    def build_trade(user_data):
        current_trade = user_data[config.SELECTION]
        price = user_data[config.PRICE]
        coin_name = user_data[config.COIN_NAME]
        amount = user_data[config.AMOUNT]
        percent_change = user_data[config.PERCENT_CHANGE]

        if current_trade == config.LONG_TRADE:
            return LongTrade(price, coin_name, amount, percent_change)
        elif current_trade == config.SHORT_TRADE:
            return ShortTrade(price, coin_name, amount, percent_change)
        else:
            raise NotImplementedError
