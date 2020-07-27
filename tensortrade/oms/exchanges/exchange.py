# Copyright 2019 The TensorTrade Authors.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


from typing import Callable, Union
from decimal import Decimal

from tensortrade.core import Component, TimedIdentifiable
from tensortrade.oms.instruments import TradingPair


class ExchangeOptions:

    def __init__(self,
                 commission: float = 0.003,
                 min_trade_size: float = 1e-6,
                 max_trade_size: float = 1e6,
                 min_trade_price: float = 1e-8,
                 max_trade_price: float = 1e8,
                 is_live: bool = False):
        self.commission = commission
        self.min_trade_size = min_trade_size
        self.max_trade_size = max_trade_size
        self.min_trade_price = min_trade_price
        self.max_trade_price = max_trade_price
        self.is_live = is_live


class Exchange(Component, TimedIdentifiable):
    """An abstract exchange for use within a trading environment."""

    registered_name = "exchanges"

    def __init__(self,
                 name: str,
                 service: Union[Callable, str],
                 options: ExchangeOptions = None):
        super().__init__()
        self.name = name
        self._service = service
        self._options = options if options else ExchangeOptions()
        self._price_streams = {}

    @property
    def options(self):
        return self._options

    def __call__(self, *streams):
        for s in streams:
            pair = "".join([c if c.isalnum() else "/" for c in s.name])
            self._price_streams[pair] = s.rename(self.name + ":/" + s.name)
        return self

    def streams(self) -> "List[Stream[float]]":
        return list(self._price_streams.values())

    def quote_price(self, trading_pair: 'TradingPair') -> Decimal:
        """The quote price of a trading pair on the exchange, denoted in the core instrument.

        Arguments:
            trading_pair: The `TradingPair` to get the quote price for.

        Returns:
            The quote price of the specified trading pair, denoted in the core instrument.
        """
        price = Decimal(self._price_streams[str(trading_pair)].value)
        price = price.quantize(Decimal(10)**-trading_pair.base.precision)
        return price

    def is_pair_tradable(self, trading_pair: 'TradingPair') -> bool:
        """Whether or not the specified trading pair is tradable on this exchange.

        Args:
            trading_pair: The `TradingPair` to test the tradability of.

        Returns:
            A bool designating whether or not the pair is tradable.
        """
        return str(trading_pair) in self._price_streams.keys()

    def execute_order(self, order: 'Order', portfolio: 'Portfolio'):
        """Execute an order on the exchange.

        Arguments:
            order: The order to execute.
            portfolio: The portfolio to use.
        """
        trade = self._service(
            order=order,
            base_wallet=portfolio.get_wallet(self.id, order.pair.base),
            quote_wallet=portfolio.get_wallet(self.id, order.pair.quote),
            current_price=self.quote_price(order.pair),
            options=self.options,
            clock=self.clock
        )

        if trade:
            order.fill(trade)
