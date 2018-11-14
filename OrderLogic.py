from threading import Thread, Lock
from settings import Settings
from asyncblink import signal
from random import uniform
from helpers import Logger


curId = "OrderLogic"


class ChainRiftData(object):
    balances = {}
    openOrders = {}

    for ticker, orderTypes in Settings.chainRiftPairPlacement.items():
        for orderType in orderTypes:
            openOrders[ticker + orderType] = {"sum": 0, "orders": {}}

    @classmethod
    def get_balance(cls, coin):
        if coin in cls.balances:
            return cls.balances[coin]

    @classmethod
    def set_balances(cls, data):
        for balance in data:
            cls.balances[balance["coin"]] = balance["quantity"]

    @classmethod
    def process_balance_changes(cls, data):
        for change in data:
            if change["coin"] in cls.balances:
                cls.balances[change["coin"]] += change["quantity"]

    @classmethod
    def process_order_changes(cls, data):
        for change in data:
            orderKey = change["symbol"] + change["type"].lower()
            try:
                if change["action"] == "Add":
                    cls.openOrders[orderKey]["sum"] += change["leaveqty"]
                    cls.openOrders[orderKey]["orders"][change["orderid"]] = OrderItem(change)
                elif change["action"] == "Update":
                    try:
                        tmp = cls.openOrders[orderKey]["orders"].pop(change["orderid"])
                        cls.openOrders[orderKey]["sum"] -= tmp.leaveQty
                        cls.openOrders[orderKey]["sum"] += change["leaveqty"]
                        cls.openOrders[orderKey]["orders"][change["orderid"]] = OrderItem(change)
                    except:
                        pass
                elif change["action"] == "Remove":
                    try:
                        tmp = cls.openOrders[orderKey]["orders"].pop(change["orderid"])
                        cls.openOrders[orderKey]["sum"] -= tmp.leaveQty
                    except:
                        pass

            except Exception as e:
                Logger.info(curId, e, orderKey, cls.openOrders)
                raise e

    @classmethod
    def get_open_orders(cls):
        return cls.openOrders


class OrderActionsForPush(object):
    def __init__(self):
        self.init_storage()
        self.lock = Lock()

    def init_storage(self):
        self.place = []
        self.move = []
        self.cancel = []

    def place_order(self, pair, quantity, price, isbuy):
        order = {
            "symbol": pair,
            "quantity": format(quantity, '.8f'),
            "price": format(price, '.8f'),
            "type": isbuy,
            "tempid": uniform(0, 10000000000)
        }
        self.place.append(order)
        if len(self.place) + 1 >= Settings.chainriftMaxOrdersInBulk:
            raise MaxOrdersToPlaceException()

    def move_order(self, orderid, price):
        order = {
            "id": orderid,
            "price": format(price, '.8f'),
        }
        self.move.append(order)
        if len(self.move) + 1 >= Settings.chainriftMaxOrdersInBulk:
            raise MaxOrdersToMoveException()

    def cancel_order(self, orderid):
        self.cancel.append(orderid)
        if len(self.cancel) + 1 >= Settings.chainriftMaxOrdersInBulk:
            raise MaxOrdersToCancelException()


class OrderManagement(object):
    processOrdersSignal = signal('processorders')
    oafp = {}
    for ticker, orderTypes in Settings.chainRiftPairPlacement.items():
        for orderType in orderTypes:
            oafp[ticker + orderType] = OrderActionsForPush()

    @classmethod
    async def process_orders(cls, data):
        t = Thread(target=cls.process_orders2, args=(data,))
        t.start()

    @classmethod
    def process_orders2(cls, data):
        if data == "BalancesRetrieved":
            for ticker in Settings.chainRiftPairPlacement.keys():
                for isbuy in Settings.chainRiftPairPlacement[ticker]:
                    orderKey = ticker + isbuy
                    try:
                        cls.oafp[orderKey].lock.acquire()
                        cls.process_coinpair_orders(ticker, isbuy)
                        cls.process_oafp_leftovers(orderKey)
                    finally:
                        cls.oafp[orderKey].init_storage()
                        cls.oafp[orderKey].lock.release()

        else:
            ticker = data[0]
            priceUpdate = data[2]
            if priceUpdate != "lastPrice":
                if ticker in Settings.chainRiftPairPlacement:
                    orderKey = ticker + priceUpdate
                    try:
                        cls.oafp[orderKey].lock.acquire()
                        cls.process_coinpair_orders(ticker, priceUpdate)
                        cls.process_oafp_leftovers(orderKey)
                    finally:
                        cls.oafp[orderKey].init_storage()
                        cls.oafp[orderKey].lock.release()

    @classmethod
    def process_oafp_leftovers(cls, orderKey):
        # Process leftover orders that might have not been sent
        if len(cls.oafp[orderKey].place) > 0:
            cls.processOrdersSignal.send(("place", cls.oafp[orderKey].place))
        if len(cls.oafp[orderKey].move) > 0:
            cls.processOrdersSignal.send(("move", cls.oafp[orderKey].move))
        if len(cls.oafp[orderKey].cancel) > 0:
            cls.processOrdersSignal.send(("cancel", cls.oafp[orderKey].cancel))

    @classmethod
    def is_order_price_in_range(cls, order):
        orderType = "buy" if order.isBuy else "sell"
        curTicker = Settings.tickerPrices[order.symbol][orderType]
        return curTicker * Settings.priceRanges[orderType][0] <= order.price <= curTicker * Settings.priceRanges[orderType][1]

    @classmethod
    def process_coinpair_orders(cls, ticker, isbuy):
        # Maintain temporary cumulative for ticker/isbuy + currently cumulative already placed
        tmp = 0
        orderKey = ticker + isbuy
        maxQuantity = Settings.chainRiftPairPlacement[ticker][isbuy]

        # If price is 0 (default) do not place orders
        if Settings.tickerPrices[ticker][isbuy] == 0:
            return

        # Move orders that need moving considering the range
        for order in sorted(ChainRiftData.openOrders[orderKey]["orders"].values(),
                                     key=lambda o: o.price, reverse=True if isbuy == "buy" else False):
            isPriceInRange = cls.is_order_price_in_range(order)
            if isPriceInRange:
                continue
            else:
                price = Settings.tickerPrices[ticker][isbuy] * uniform(Settings.priceRanges[isbuy][0], Settings.priceRanges[isbuy][1])
                try:
                    cls.oafp[orderKey].move_order(order.orderId, price)
                except MaxOrdersToMoveException:
                    cls.processOrdersSignal.send(("move", cls.oafp[orderKey].move))
                    cls.oafp[orderKey].move = []
                except Exception as e:
                    Logger.exception(curId, "Unexpected exception occurred while moving order", order.orderId, e)

        # Place new orders
        errorCounter = 0
        while tmp + ChainRiftData.openOrders[orderKey]["sum"] < maxQuantity:
            quantity = maxQuantity * 0.1 * uniform(0.3, 0.7)

            price = Settings.tickerPrices[ticker][isbuy] * uniform(Settings.priceRanges[isbuy][0], Settings.priceRanges[isbuy][1])
            try:
                cls.oafp[orderKey].place_order(ticker, quantity, price, isbuy)
                tmp += quantity
            except MaxOrdersToPlaceException:
                errorCounter += 1
                cls.processOrdersSignal.send(("place", cls.oafp[orderKey].place))
                cls.oafp[orderKey].place = []
            except MaxOrdersToMoveException:
                errorCounter += 1
                cls.processOrdersSignal.send(("move", cls.oafp[orderKey].move))
                cls.oafp[orderKey].move = []
            except MaxOrdersToCancelException:
                errorCounter += 1
                cls.processOrdersSignal.send(("cancel", cls.oafp[orderKey].cancel))
                cls.oafp[orderKey].cancel = []
            except Exception as e:
                errorCounter += 1
                Logger.exception(curId, "Unexpected exception occurred while preparing orders", e)

            if errorCounter >= 5:
                Logger.info(curId, "An error occurred while preparing orders for", ticker)
                break


processChangedOrdersSignal = signal('processchangedorders')
processChangedOrdersSignal.connect(ChainRiftData.process_order_changes)
processChangedBalancesSignal = signal('processchangedbalances')
processChangedBalancesSignal.connect(ChainRiftData.process_balance_changes)


class MaxOrdersToPlaceException(Exception):
    pass


class MaxOrdersToMoveException(Exception):
    pass


class MaxOrdersToCancelException(Exception):
    pass


class OrderItem(object):
    def __init__(self, jsonOrder):
        self.orderId = jsonOrder["orderid"]
        self.symbol = jsonOrder["symbol"]
        self.leaveQty = jsonOrder["leaveqty"]
        self.quantity = jsonOrder["quantity"]
        self.price = jsonOrder["price"]
        self.isBuy = True if jsonOrder["type"].lower() == "buy" else False

    def __str__(self):
        return "{" + ', '.join(['{key}: {value}'.format(key=key, value=self.__dict__.get(key)) for key in self.__dict__]) + "}"

    def __repr__(self):
        return self.__str__()
