import threading
import websocket
import time
import ssl, json
try:
    import thread
except ImportError:
    import _thread as thread

subs = {
    "event": "bts:subscribe",
    "data": {
        "channel": "live_trades_btcusd"
    }
}
sub2 = {
    "event": "bts:subscribe",
    "data": {
        "channel": "order_book_btcusd"
    }
}
unsubs = {
    "event": "bts:unsubscribe",
    "data": {
        "channel": "live_trades_btcusd"
    }
}

wsCli = None
class WebSocketClient(threading.Thread):
    def __init__(self, url):
        self.url = url
        threading.Thread.__init__(self)
        self.setDaemon(True)

    def run(self):
        # Running the run_forever() in a seperate thread.
        #websocket.enableTrace(True)
        self.ws = websocket.WebSocketApp(self.url,
                                         on_message = self.on_message,
                                         on_error = self.on_error,
                                         on_close = self.on_close)
        self.ws.on_open = self.on_open
        self.ws.run_forever(sslopt={"cert_reqs": ssl.CERT_NONE})

    def stop(self):
        print('Stopping the websocket...')
        self.ws.keep_running = False

    def send(self, data):
        # Wait till websocket is connected.
        while not self.ws.sock.connected:
            time.sleep(0.25)
        print('Sending: ', data)
        self.ws.send(json.dumps(data))

    def on_message(self, ws, message):
        print('Received: ', message)
    #    f.write(message  +  "\n" )
    #    f.flush()

    def on_open(self, ws):
        print('Opened the connection...')

    def on_close(self, ws):
        print('Closed the connection...')

    def on_error(self, ws, error):
        print('Websocket received error...')
        print(error)


#f = open("webSocketTester.log", "a")

def ws_client(action):
    global wsCli
    if wsCli is None:
        wsCli = WebSocketClient("wss://ws.bitstamp.net")
    if action == 'start' and not (wsCli.is_alive()):
        wsCli.start()
        wsCli.send(subs)
    if action == 'stop' and wsCli.is_alive():
        wsCli.stop()
        wsCli = None


if __name__ == "__main__":
    wsCli = WebSocketClient("wss://ws.bitstamp.net")
    # wsCli.daemon = True
    wsCli.start()
    wsCli.send(sub2)
    # wsCli.send(sub2)
    time.sleep(15)
    wsCli.stop()
    time.sleep(5)
    #wsCli.join()
    print('After closing client...')