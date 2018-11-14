class Settings(object):
    # How many orders can be sent at once
    # This depends on how many orders you generate per coin pair and will be automatically split if you generate more
    # Beware of the limit on the amount of orders at ChainRift per pair
    chainriftMaxOrdersInBulk = 50

    # Set tickers you're interested in from BitFinex and Poloniex
    bitfinexTickers = ["tBTCUSD", "tETHBTC", "tEOSBTC", "tXLMBTC", "tXMRBTC"]
    poloniexTickers = ["USDT_BTC", "BTC_LTC", "BTC_XMR"]

    # Map tickers from different sources to ChainRift
    chainRiftTickers = {"tBTCUSD": "BTC/USD", "tETHBTC": "ETH/BTC", "USDT_BTC": "BTC/USDT", "BTC_LTC": "LTC/BTC",
                        "tEOSBTC": "EOS/BTC", "tXLMBTC": "XLM/BTC", "tXMRBTC": "XMR/BTC", "BTC_XMR": "XMR/BTC"}

    # Select price range that shall be used for determining price to place orders (based on input bid/ask)
    priceRanges = {"buy": (0.997, 0.99999), "sell": (1.00001, 1.003)}

    # Set pairs to buy and/or sell with max quantities that are allowed to be used for order placement
    chainRiftPairPlacement = {"EOS/BTC": {"buy": 4, "sell": 15}, "XMR/BTC": {"buy": 4, "sell": 15}}

    # Insert API access information from ChainRift
    apiid = ""
    apikey = """"""

    # WS API hosts
    poloniex_ws_host = "api2.poloniex.com"
    poloniex_ws_port = 443

    bitfinex_ws_host = "api.bitfinex.com"
    bitfinex_ws_port = 443

    chainrift_ws_host = "ws.21mil.com"
    chainrift_ws_port = 443
    #chainrift_ws_host = "localhost"
    #chainrift_ws_port = 51735

    # Do not touch
    tickerPrices = {}
    for pair in chainRiftTickers.values():
        tickerPrices[pair] = {"buy": 0, "sell": 0, "lastPrice": 0}
    _bitFinexTickers = {}
    _poloniexTickers = {}
