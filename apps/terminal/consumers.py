import asyncio
import json
import socket
from services import store, ssh, auth
from channels.generic.websocket import AsyncWebsocketConsumer
from services import store, ssh


class TerminalConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        if not auth.scope_logged_in(self.scope):
            await self.close()
            return
        sid = self.scope['url_route']['kwargs']['sid']
        server = next((s for s in store.load()['servers'] if s['id'] == sid), None)
        await self.accept()
        if not server or server['os'] != 'linux' or ssh.get_password(sid) is None:
            await self.send(text_data='\r\nNot connected. Go back and press Connect first.\r\n')
            await self.close()
            return
        try:
            self.chan = await asyncio.to_thread(ssh.shell, server)
        except Exception as e:
            await self.send(text_data=f'\r\nError: {e}\r\n')
            await self.close()
            return
        self.alive = True
        self.task = asyncio.create_task(self._reader())

    def _recv(self):
        self.chan.settimeout(0.5)
        try:
            data = self.chan.recv(4096)
            return data if data else None
        except socket.timeout:
            return b''

    async def _reader(self):
        try:
            while self.alive:
                data = await asyncio.to_thread(self._recv)
                if data is None:
                    break
                if data:
                    await self.send(bytes_data=data)
        except Exception:
            pass
        await self.close()

    async def receive(self, text_data=None, bytes_data=None):
        chan = getattr(self, 'chan', None)
        if not chan:
            return
        msg = json.loads(text_data)
        if msg['type'] == 'input':
            chan.send(msg['data'])
        elif msg['type'] == 'resize':
            chan.resize_pty(width=msg['cols'], height=msg['rows'])

    async def disconnect(self, code):
        self.alive = False
        chan = getattr(self, 'chan', None)
        if chan:
            chan.close()