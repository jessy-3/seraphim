import _thread
import websocket
import time
import ssl, json

try:
    import thread
except ImportError:
    import _thread as thread

#f = open("webSocketTester.log", "a")
subs = {
            "event": "bts:subscribe",
            "data": {
                "channel": "live_trades_btcusd"
            }
        }
unsubs = {
            "event": "bts:unsubscribe",
            "data": {
                "channel": "live_trades_btcusd"
            }
        }
heartbeep = {
    "event": "bts:heartbeat"
}

def on_message(ws, message):
    print(message)
#    f.write(message  +  "\n" )
#    f.flush()

def on_error(ws, error):
    print(error)

def on_close(ws,close_status_code, close_msg):
    def run(*args):
        print("### closed ###")

def on_open(ws):
    print("Opened connection")
    def run(*args):
        ws.send(json.dumps(subs))
    thread.start_new_thread(run, ())

if __name__ == "__main__":
#    websocket.enableTrace(True)
    ws = websocket.WebSocketApp("wss://ws.bitstamp.net",
                              on_open = on_open,
                              on_message = on_message,
                              on_error = on_error,
                              on_close = on_close)
    ws.run_forever(sslopt={"cert_reqs": ssl.CERT_NONE}, reconnect=5)
    
