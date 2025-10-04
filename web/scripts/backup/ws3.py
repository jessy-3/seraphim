# this program is using websockes instead of websocket.
import asyncio
import websockets
import json
import ssl

async def bitstamp_connect():
    uri = "wss://ws.bitstamp.net/"
    ssl_context = ssl.SSLContext()
#    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE
    subscription = {
          "event": "bts:subscribe",
          "data": {
            "channel": "live_trades_btcusd"
          }
        }
    async with websockets.connect(uri,ssl=ssl_context) as ws:
        await ws.send(json.dumps(subscription))

        data = await ws.recv()
        print(data)

asyncio.get_event_loop().run_until_complete(bitstamp_connect())
