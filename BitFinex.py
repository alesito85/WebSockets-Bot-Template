from autobahn.asyncio.websocket import WebSocketClientProtocol
from autobahn.asyncio.websocket import WebSocketClientFactory
from settings import Settings
from helpers import loop, Logger
from asyncblink import signal
from time import sleep
import asyncio
import json
import ssl


class BitFinexClientProtocol(WebSocketClientProtocol):
    id = "BitFinex"
    pricesignal = signal('pricechange')

    def onConnect(self, response):
        Logger.info(self.id, "Server connected: {0}".format(response.peer))

    async def subscribePair(self, pair):
        self.sendMessage(
            '{{ "event": "subscribe", "channel": "ticker", "symbol": "{}"}}'.format(pair).encode('utf8'))

    async def onOpen(self):
        Logger.info(self.id, "Connection open.")
        for pair in Settings.bitfinexTickers:
            await self.subscribePair(pair)

    async def onMessage(self, payload, isBinary):
        if isBinary:
            Logger.debug(self.id, "Binary message received: {0} bytes".format(len(payload)))
        else:
            data = json.loads(payload.decode('utf8'))
            Logger.debug(self.id, "Text message received: {0}".format(data))
            if isinstance(data, dict):
                if data["event"] == "subscribed" and data["channel"] == "ticker":
                    Settings._bitFinexTickers[data["chanId"]] = data["symbol"]
            elif data[1] != 'hb':
                if Settings._bitFinexTickers[data[0]] not in Settings.chainRiftTickers:
                    return
                ticker = Settings.chainRiftTickers[Settings._bitFinexTickers[data[0]]]
                lastPrice = data[1][6]
                bidPrice = data[1][0]
                askPrice = data[1][2]
                if Settings.tickerPrices[ticker]["lastPrice"] != lastPrice:
                    Settings.tickerPrices[ticker]["lastPrice"] = lastPrice
                    Logger.debug(self.id, "Send signal", ticker, lastPrice, "lastPrice")
                    self.pricesignal.send((ticker, lastPrice, "lastPrice"))
                if Settings.tickerPrices[ticker]["buy"] != bidPrice:
                    Settings.tickerPrices[ticker]["buy"] = bidPrice
                    Logger.debug(self.id, "Send signal", ticker, bidPrice, "buy")
                    self.pricesignal.send((ticker, bidPrice, "buy"))
                if Settings.tickerPrices[ticker]["sell"] != askPrice:
                    Settings.tickerPrices[ticker]["sell"] = askPrice
                    Logger.debug(self.id, "Send signal", ticker, askPrice, "sell")
                    self.pricesignal.send((ticker, askPrice, "sell"))

    async def onClose(self, wasClean, code, reason):
        Logger.info(self.id, "WebSocket connection closed: {0}".format(reason))
        sleep(15)
        try:
            BFfactory = WebSocketClientFactory(u"wss://{}:{}/ws/2".format(Settings.bitfinex_ws_host, Settings.bitfinex_ws_port))
            BFfactory.protocol = BitFinexClientProtocol
            task = asyncio.ensure_future(loop.create_connection(BFfactory, Settings.bitfinex_ws_host, Settings.bitfinex_ws_port,
                                                            ssl=ssl.SSLContext() if Settings.bitfinex_ws_port == 443 else None))
            await task
        except Exception as e:
            Logger.info(self.id, "Reconnect failed", e)
            await self.onClose(wasClean, -1, "Trying to reconnect...")


BFfactory = WebSocketClientFactory(u"wss://{}:{}/ws/2".format(Settings.bitfinex_ws_host, Settings.bitfinex_ws_port))
BFfactory.protocol = BitFinexClientProtocol
