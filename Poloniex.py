from autobahn.asyncio.websocket import WebSocketClientProtocol
from autobahn.asyncio.websocket import WebSocketClientFactory
from settings import Settings
from helpers import loop, Logger
from asyncblink import signal
from time import sleep
import asyncio
import json
import ssl


poloniexCurrencies = {"BTC_BCN": 7, "BTC_BTS": 14, "BTC_BURST": 15, "BTC_CLAM": 20, "BTC_DGB": 25, "BTC_DOGE": 27, "BTC_DASH": 24, "BTC_GAME": 38, "BTC_HUC": 43, "BTC_LTC": 50, "BTC_MAID": 51, "BTC_OMNI": 58, "BTC_NAV": 61, "BTC_NMC": 64, "BTC_NXT": 69, "BTC_PPC": 75, "BTC_STR": 89, "BTC_SYS": 92, "BTC_VIA": 97, "BTC_VTC": 100, "BTC_XCP": 108, "BTC_XMR": 114, "BTC_XPM": 116, "BTC_XRP": 117, "BTC_XEM": 112, "BTC_ETH": 148, "BTC_SC": 150, "BTC_FCT": 155, "BTC_DCR": 162, "BTC_LSK": 163, "BTC_LBC": 167, "BTC_STEEM": 168, "BTC_SBD": 170, "BTC_ETC": 171, "BTC_REP": 174, "BTC_ARDR": 177, "BTC_ZEC": 178, "BTC_STRAT": 182, "BTC_PASC": 184, "BTC_GNT": 185, "BTC_BCH": 189, "BTC_ZRX": 192, "BTC_CVC": 194, "BTC_OMG": 196, "BTC_GAS": 198, "BTC_STORJ": 200, "BTC_EOS": 201, "BTC_SNT": 204, "BTC_KNC": 207, "BTC_BAT": 210, "BTC_LOOM": 213, "BTC_QTUM": 221, "BTC_BNT": 232, "BTC_MANA": 229, "USDT_BTC": 121, "USDT_DOGE": 216, "USDT_DASH": 122, "USDT_LTC": 123, "USDT_NXT": 124, "USDT_STR": 125, "USDT_XMR": 126, "USDT_XRP": 127, "USDT_ETH": 149, "USDT_SC": 219, "USDT_LSK": 218, "USDT_ETC": 173, "USDT_REP": 175, "USDT_ZEC": 180, "USDT_GNT": 217, "USDT_BCH": 191, "USDT_ZRX": 220, "USDT_EOS": 203, "USDT_SNT": 206, "USDT_KNC": 209, "USDT_BAT": 212, "USDT_LOOM": 215, "USDT_QTUM": 223, "USDT_BNT": 234, "USDT_MANA": 231, "XMR_BCN": 129, "XMR_DASH": 132, "XMR_LTC": 137, "XMR_MAID": 138, "XMR_NXT": 140, "XMR_ZEC": 181, "ETH_LSK": 166, "ETH_STEEM": 169, "ETH_ETC": 172, "ETH_REP": 176, "ETH_ZEC": 179, "ETH_GNT": 186, "ETH_BCH": 190, "ETH_ZRX": 193, "ETH_CVC": 195, "ETH_OMG": 197, "ETH_GAS": 199, "ETH_EOS": 202, "ETH_SNT": 205, "ETH_KNC": 208, "ETH_BAT": 211, "ETH_LOOM": 214, "ETH_QTUM": 222, "ETH_BNT": 233, "ETH_MANA": 230, "USDC_BTC": 224, "USDC_USDT": 226, "USDC_ETH": 225}


class PoloniexClientProtocol(WebSocketClientProtocol):
    id = "Poloniex"
    pricesignal = signal('pricechange')

    def onConnect(self, response):
        Logger.info(self.id, "Server connected: {0}".format(response.peer))

    async def onOpen(self):
        Logger.info(self.id, "Connection open.")
        self.sendMessage('{ "command": "subscribe", "channel": "1002"}'.encode('utf8'))

    async def onMessage(self, payload, isBinary):
        if isBinary:
            Logger.info(self.id, "Binary message received: {0} bytes".format(len(payload)))
        else:
            data = json.loads(payload.decode('utf8'))
            #Logger.debug(self.id, "Text message received: {0}".format(data))
            if data[0] == 1002 and len(data) > 2 and data[2][0] in Settings._poloniexTickers:
                if Settings._poloniexTickers[data[2][0]] not in Settings.chainRiftTickers:
                    return
                Logger.debug(self.id, "Text message received: {0}".format(data))
                ticker = Settings.chainRiftTickers[Settings._poloniexTickers[data[2][0]]]
                lastPrice = float(data[2][1])
                bidPrice = float(data[2][3])
                askPrice = float(data[2][2])
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
        Logger.info(self.id, self.id, "WebSocket connection closed: {0}".format(reason))
        sleep(15)
        try:
            Pfactory = WebSocketClientFactory(u"wss://{}:{}".format(Settings.poloniex_ws_host, Settings.poloniex_ws_port))
            Pfactory.protocol = PoloniexClientProtocol
            task = asyncio.ensure_future(loop.create_connection(Pfactory, Settings.poloniex_ws_host, Settings.poloniex_ws_port,
                                                            ssl=ssl.SSLContext() if Settings.poloniex_ws_port == 443 else None))
            await task
        except Exception as e:
            Logger.info(self.id, "Reconnect failed", e)
            await self.onClose(wasClean, -1, "Trying to reconnect...")


Pfactory = WebSocketClientFactory(u"wss://{}:{}".format(Settings.poloniex_ws_host, Settings.poloniex_ws_port))
Pfactory.protocol = PoloniexClientProtocol
Pfactory.openHandshakeTimeout = 0
