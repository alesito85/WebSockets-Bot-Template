from autobahn.asyncio.websocket import WebSocketClientProtocol
from autobahn.asyncio.websocket import WebSocketClientFactory
from OrderLogic import OrderManagement, ChainRiftData
from helpers import loop, Logger
from settings import Settings
from datetime import datetime
from asyncblink import signal
from time import sleep
import threading
import asyncio
import json
import ssl
import rsa


def get_nonce():
    return int(datetime.utcnow().strftime("%Y%m%d%H%M%S%f"))


def authenticate(protocol):
    key = rsa.PrivateKey.load_pkcs1(Settings.apikey)
    curNonce = get_nonce()
    apiauthpayload = "Login" + str(curNonce)
    signature = rsa.sign(apiauthpayload.encode(), key, "SHA-256").hex()
    
    data = {
        "apikey": Settings.apiid,
        "apisignature": signature,
        "apiauthpayload": apiauthpayload
    }
    
    command = {
        "name": "Login",
        "nonce": curNonce,
        "data": data
    }
    
    protocol.sendMessage(json.dumps(command).encode('utf8'))


def get_balances(protocol):
    command = {
        "name": "GetBalances",
        "apinonce": 0
    }

    protocol.sendMessage(json.dumps(command).encode('utf8'))


def private_subscriptions(protocol):
    for commandName in ["SubscribeMyOrders", "SubscribeMyBalanceChanges"]:
        command = {
            "name": commandName,
            "apinonce": 0
        }
        protocol.sendMessage(json.dumps(command).encode('utf8'))


def place_orders(protocol, orders):
    command = {
        "name": "PlaceOrders",
        "data": orders,
        "apinonce": 0
    }
    protocol.sendMessage(json.dumps(command).encode("utf8"))


def move_orders(protocol, orders):
    command = {
        "name": "MoveOrders",
        "data": orders,
        "apinonce": 0
    }
    protocol.sendMessage(json.dumps(command).encode("utf8"))


def cancel_all_orders(protocol, data=[]):
    command = {
        "name": "CancelAllOrders",
        "data": data,
        "apinonce": 0
    }
    protocol.sendMessage(json.dumps(command).encode("utf8"))


class ChainRiftClientProtocol(WebSocketClientProtocol):
    id = "ChainRift"
    placedOrders = 0
    ordersToPlace = []
    lock = threading.Lock()
    priceSignal = signal('pricechange')
    processOrdersSignal = signal('processorders')
    processChangedOrdersSignal = signal('processchangedorders')
    processChangedBalancesSignal = signal('processchangedbalances')
    mandatorySubscribed = 0

    async def process_price_update(self, data):
        if self.mandatorySubscribed < 2:
            return
        await OrderManagement.process_orders(data)

    def process_orders(self, data):
        Logger.info(self.id, "Process orders", data)
        if data[0] == "place":
            place_orders(self, data[1])
        elif data[0] == "move":
            move_orders(self, data[1])
        elif data[0] == "cancel":
            cancel_all_orders(self, data[1])

    def onConnect(self, response):
        Logger.info(self.id, "Server connected: {0}".format(response.peer))
        self.priceSignal.connect(self.process_price_update)
        self.processOrdersSignal.connect(self.process_orders)

    async def onOpen(self):
        Logger.info(self.id, "WebSocket connection open.")
        authenticate(self)

    async def onMessage(self, payload, isBinary):
        if isBinary:
            Logger.debug(self.id, "Binary message received: {0} bytes".format(len(payload)))
        else:
            data = payload.decode('utf8')
            # Logger.debug(self.id, "Text message received: {0}".format(data))
            obj = json.loads(data)
            if obj["method"] == "Login" and obj["success"]:
                # Upon login get balances
                get_balances(self)
                private_subscriptions(self)
            
            elif obj["method"] == "GetBalances" and obj["success"]:
                # Emit signal to place orders
                ChainRiftData.set_balances(obj["data"])

            elif obj["method"] in ("SubscribeMyOrders", "SubscribeMyBalanceChanges"):
                self.mandatorySubscribed += 1
                if self.mandatorySubscribed >= 2:
                    self.priceSignal.send("BalancesRetrieved")

            elif obj["method"] == "myorderschanged":
                self.processChangedOrdersSignal.send(obj["data"])

            elif obj["method"] == "mybalanceschanged":
                self.processChangedBalancesSignal.send(obj["data"])

    async def onClose(self, wasClean, code, reason):
        Logger.info(self.id, "WebSocket connection closed: {0}".format(reason))
        sleep(15)
        try:
            Cfactory = WebSocketClientFactory(u"ws"+(u"s" if Settings.chainrift_ws_port == "443" else u"")+u"://{}:{}/v1".format(Settings.chainrift_ws_host, Settings.chainrift_ws_port))
            Cfactory.protocol = ChainRiftClientProtocol
            Cfactory.openHandshakeTimeout = 0
            task = asyncio.ensure_future(
                loop.create_connection(Cfactory, Settings.chainrift_ws_host, Settings.chainrift_ws_port, ssl=ssl.SSLContext() if Settings.chainrift_ws_port == 443 else None))
            await task
        except Exception as e:
            Logger.exception(self.id, "Reconnect failed", e)
            await self.onClose(wasClean, -1, "Trying to reconnect...")


Cfactory = WebSocketClientFactory(u"ws"+(u"s" if Settings.chainrift_ws_port == "443" else u"")+u"://{}:{}/v1".format(Settings.chainrift_ws_host, Settings.chainrift_ws_port))
Cfactory.protocol = ChainRiftClientProtocol
Cfactory.openHandshakeTimeout = 0
