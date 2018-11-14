from ChainRift import Cfactory
from BitFinex import BFfactory
from Poloniex import Pfactory, poloniexCurrencies
from settings import Settings
from helpers import *
import asyncio
import ssl


if not Settings.apiid or not Settings.apikey:
    Logger.info("You have to set API id and key in settings file")
    exit(0)


for ticker in Settings.poloniexTickers:
    try:
        Settings._poloniexTickers[poloniexCurrencies[ticker]] = ticker
    except Exception as e:
        Logger.info("Poloniex ticker {} probably doesn't exist".format(ticker), e)


async def retry_until_connected():
    global conns  # Make sure we use the global tcp_server
    while True:
        try:
            conns = await loop.create_connection(Cfactory, Settings.chainrift_ws_host, Settings.chainrift_ws_port,
                                                  ssl=ssl.SSLContext() if Settings.chainrift_ws_port == 443 else None)
            conns = await loop.create_connection(BFfactory, Settings.bitfinex_ws_host, Settings.bitfinex_ws_port,
                                                  ssl=ssl.SSLContext() if Settings.bitfinex_ws_port == 443 else None)
            conns = await loop.create_connection(Pfactory, Settings.poloniex_ws_host, Settings.poloniex_ws_port,
                                                 ssl=ssl.SSLContext() if Settings.poloniex_ws_port == 443 else None)
        except OSError as e:
            Logger.info("Server not up retrying in 5 seconds...", e)
            await asyncio.sleep(5)
        else:
            break

while 1:
    try:
        loop.run_until_complete(asyncio.wait([retry_until_connected()]))
        loop.run_forever()
    except Exception as e:
        Logger.exception("Main loop exception", e)
loop.close()
