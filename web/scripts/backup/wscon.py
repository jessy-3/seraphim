'''
from channels.generic.websocket import AsyncJsonWebsocketConsumer

class PracticeConsumer(AsyncJsonWebsocketConsumer)

      async def connect(self):
           await self.accept()

      async def receive(self, text_data=None, bytes_data=None, **kwargs):
            if text_data == 'PING':
                 await self.send('PONG')
'''
from django.conf import settings
from asgiref.sync import async_to_sync
from channels.consumer import SyncConsumer

class TicksSyncConsumer(SyncConsumer):

    def websocket_connect(self, event):
        self.send({
            'type': 'websocket.accept'
        })

        # Join ticks group
        async_to_sync(self.channel_layer.group_add)(
            "btcusd",
            self.channel_name
        )
        self.send({
            'type': 'websocket.send',
            'text': "accepted",
        })

    def websocket_disconnect(self, event):
        # Leave ticks group
        async_to_sync(self.channel_layer.group_discard)(
            "btcusda",
            self.channel_name
        )

    def new_ticks(self, event):
        self.send({
            'type': 'websocket.send',
            'text': event['content'],
        })
