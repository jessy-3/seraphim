import logging
import threading
import websocket
import time
import ssl, json
try:
    import thread
except ImportError:
    import _thread as thread
import redis
import channels.layers
from asgiref.sync import async_to_sync
logger = logging.getLogger('WebSocketClient')
logger.setLevel(logging.INFO)

REDIS_HOST = "redis"  # Use your Redis host
REDIS_PORT = 6379  # Use your Redis port

wsCli = None
# try:
#     thread.start_new_thread(print, ("Thread is imported",))
# except NameError:
#     print("Thread is not imported")

# unsubsample = {
#     "event": "bts:unsubscribe",
#     "data": {
#         "channel": "live_trades_ethusd"
#     }
# }

def eventdata(event_act, cha_name):
    return(
        {
            "event": "bts:"+event_act,
            "data": {
                "channel": cha_name
            }
        }
    )

class WebSocketClient(threading.Thread):

    def __init__(self, url):
        self.url = url
        threading.Thread.__init__(self)
        self.setDaemon(True)

    def run(self):
        # Running the run_forever() in a seperate thread.
        # websocket.enableTrace(True)
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
        if json.loads(message)['event'] == "trade":
            try:
                r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=0)
                if not r.ping():
                    r = True    # not connected
                    print("Connection to Redis failed.")
                    logger.info(f"Connection to Redis failed.")
            except redis.ConnectionError as e:
                r = True        # not connected
                logger.info(f"Connection error: {e}")
                print(f"Connection error: {e}")
            channel_layer = channels.layers.get_channel_layer()
            grp_name= json.loads(message)['channel']
            if not (r == True):       # redis connected
                sym= grp_name[grp_name.rfind('_')+1:].upper()
                pair = sym[:len(sym)-3]+'/'+sym[len(sym)-3:] + "_Price"
                data= json.loads(message)['data']
                r.hmset(pair, {"price": data["price_str"], "timestamp": data["timestamp"], "source":"live"})

            grp_name = grp_name[:grp_name.find('_', -10)]
            # print(grp_name)
            # sending data to vanilla websocket channel
            async_to_sync(channel_layer.group_send)(
                grp_name, {
                "type": 'live_ticks',
                "content": message,
            })
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

# ws_client handles the market websocket client
def ws_client(action, chaname = None):
    global wsCli
    if wsCli is None:
        wsCli = WebSocketClient("wss://ws.bitstamp.net")
    if action == 'start' and not (wsCli.is_alive()):
        wsCli.start()
    if chaname != None and wsCli.is_alive():
        wsCli.send(eventdata(action, chaname))      ## ws client using full bitstamp channel name now
        # wsCli.send(eventdata(action,"live_trades_"+chaname))
    if action == 'stop' and wsCli.is_alive():
        wsCli.stop()
        wsCli = None


if __name__ == "__main__":
    wsCli = WebSocketClient("wss://ws.bitstamp.net")
    # wsCli.daemon = True
    wsCli.start()
    wsCli.send(eventdata("subscribe","live_trades_btcusd"))
    # wsCli.send(eventdata("subscribe", "order_book_ethbtc"))
    time.sleep(15)
    wsCli.stop()
    time.sleep(3)
    #wsCli.join()
    print('After closing client...')