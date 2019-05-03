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

from tradeexecutor import TradeExecutor
import config
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



