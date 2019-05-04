import abc


class TradeDetails(metaclass=abc.ABCMeta):
    def __init__(
            self,
            start_price: float,
            symbol: str,
            amount: float,
            currency: str = 'USD'):
        self.start_price = start_price
        self.symbol = symbol.upper()
        self.amount = amount
        self.currency = currency

    @property
    def exchange_symbol(self):
        return f"{self.symbol.upper()}/{self.currency}"

    @property
    @abc.abstractmethod
    def exit_price(self):
        pass

    def __str__(self) -> str:
        return f'order for {self.amount} {self.exchange_symbol} with either '\
               f'price: {self.start_price:.5}, exit_price: {self.exit_price:.5}'


class LongTrade(TradeDetails):
    def __init__(
            self,
            start_price: float,
            symbol: str,
            amount: float,
            percent_change: float = 0.5,
            currency: str = 'USD'
    ) -> None:
        super().__init__(start_price, symbol, amount, currency)
        self.end_price = start_price * (1 + percent_change)

    @property
    def exit_price(self):
        return self.end_price

    def __str__(self) -> str:
        return "Long " + super().__str__()


class ShortTrade(TradeDetails):
    def __init__(
            self,
            start_price: float,
            symbol: str,
            amount: float,
            percent_change: float = 0.5,
            currency: str = 'USD'
    ) -> None:
        super().__init__(start_price, symbol, amount, currency)
        self.end_price = start_price * (1 - percent_change / 100)

    @property
    def exit_price(self):
        return self.end_price

    def __str__(self) -> str:
        return "Short " + super().__str__()