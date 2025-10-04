'''
from django.conf import settings
from asgiref.sync import async_to_sync
from channels.consumer import SyncConsumer
'''
import json
from asyncio import sleep
from channels.generic.websocket import AsyncJsonWebsocketConsumer

# vanilla websocket consumer
class TicksAsyncConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        await self.accept()
        await self.send(json.dumps({
            'type': 'websocket.accept'
        }))

    async def disconnect(self, code):
        print(f"Disconnected : {self.channel_name } from {self.subs_group_name}")
        await self.channel_layer.group_discard(
            self.subs_group_name,
            self.channel_name
        )

    async def receive(self, text_data=None, bytes_data=None, **kwargs):
        if text_data == "PING":
            print("Ping-Pong")
            await self.send("PONG")
            return
        try:
            jdata = json.loads(text_data)
            if jdata['event'] == 'subscribe':               ## ws server channel no currency symbol now
                print('subscribe', jdata['content'])
                self.subs_group_name = jdata['content']
                await self.channel_layer.group_add(
                    self.subs_group_name,
                    self.channel_name
                )
                await self.send(jdata['content'] + ' channel subscribed')
                return
            if jdata['event'] == 'unsubscribe':
                print('unsubscribe', jdata['content'])
                self.subs_group_name = jdata['content']
                await self.channel_layer.group_discard(
                    self.subs_group_name,
                    self.channel_name
                )
                await self.send(jdata['content'] + ' channel unsubscribed')
                return
        except Exception as e:
            print("Error in parsing websocket event: " + text_data)
        await self.send(text_data)

    async def send_message(self, event):
        # Send message to WebSocket
        await self.send(text_data=json.dumps({
            "payload": event,
        }))

    async def live_ticks(self, event):
        # print(f"Event: {event['content']} for {self.channel_name}")
        await self.send(event['content'])

    async def timer_ticks(self, event):
        # print(f"Event: {event['content']} for {self.channel_name}")
        await self.send(event['content'])
