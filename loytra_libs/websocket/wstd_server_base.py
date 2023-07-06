import asyncio
import secrets
import websockets
from enum import Enum
from typing import Any, Optional
from loytra_libs.logging import logutil


# constants
_TOPIC_AUTHORIZE    = "_auth_"
_TOPIC_DEAUTHORIZE  = "_deauth_"
_FIELD_TUNNEL_ID    = "_tid_"
_TUNNEL_NONE        = "_"
_TUNNEL_CONTROLLER  = "@"
_TUNNEL_CLIENTS     = "*"


# enums
class WebsocketMessageTransport(Enum):
    MSGPACK = 1
    JSON = 2

class WebsocketTunnelTarget(Enum):
    ALL = 1
    CONTROLLER = 2
    CLIENTS = 3


# client and socket model
class _WebsocketClient:
    def __init__(self, socket_id: str, client_id: str, tunnel_id: str, intent: list[str], info: Any):
        self.socket_id = socket_id
        self.client_id = client_id
        self.tunnel_id = tunnel_id
        self.intent: list[str] = intent
        self.info: Any = info


class _WebsocketReference:
    def __init__(self, socket, socket_id: str, path: str) -> None:
        self.socket = socket
        self.socket_id = socket_id
        self.path = path
        self.clients: dict[str, str] = {}
        self.is_tunnel = False

#Websocket Topic-Data Server Base class
class WSTDServerBase:
    def __init__(self,
            debug_mode: bool,
            port: int,
            allow_remote_connect: bool = True,
            transport: WebsocketMessageTransport = WebsocketMessageTransport.MSGPACK):

        if transport == WebsocketMessageTransport.MSGPACK:
            import msgpack
            self._transport_pack = lambda obj: msgpack.packb(obj)
            self._transport_unpack = lambda raw: msgpack.unpackb(raw)
        elif transport == WebsocketMessageTransport.JSON:
            import json
            self._transport_pack = lambda obj: json.dumps(obj)
            self._transport_unpack = lambda raw: json.loads(raw)
        else:
            raise RuntimeError("Invalid transport specified!")

        self._debug_mode = debug_mode
        self._host = '' if allow_remote_connect else '127.0.0.1'
        self._port = port
        self._transport = transport

        self._logger = logutil.get(name="api_server", tag="API_SERVER")

        self._clients: dict[str, _WebsocketClient] = {}
        self._wsrefs: dict[str, _WebsocketReference] = {}

    # util
    def _is_tunnel_controller(self, tunnel_id: str) -> bool:
        return bool(tunnel_id == _TUNNEL_CONTROLLER)

    # base
    async def _on_run_websocket_server(self):
        pass

    async def _on_client_connected(self, client_id: str):
        pass

    async def _on_client_authorized(self, client_id: str, intent: list[str], info: Any):
        pass

    async def _on_client_disconnected(self, client_id: str):
        pass

    async def _on_tunnel_controller_connected(self, client_id: str):
        pass

    async def _on_tunnel_controller_disconnected(self, client_id: str):
        pass

    async def _on_message_received(self, client_id: str, topic: str, data: Any, message: dict[str, Any], client_is_tunnel_controller: bool):
        pass

    def _on_destroy(self):
        pass

    # impl
    def _debug_log(self, msg: str):
        if self._debug_mode:
            self._logger.debug(msg)

    def get_connected_clients(self, include_tunnel_controllers: bool = False) -> list[tuple[str, list[str], Any]]:
        result: list[tuple[str, list[str], Any]] = []
        for client_id, client in self._clients.items():
            if client.tunnel_id != _TUNNEL_CONTROLLER or include_tunnel_controllers:
                result.append((client_id, client.intent, client.info))
        return result

    def get_connected_tunnel_controllers(self) -> list[tuple[str, list[str], Any]]:
        result: list[tuple[str, list[str], Any]] = []
        for client_id, client in self._clients.items():
            if client.tunnel_id == _TUNNEL_CONTROLLER:
                result.append((client_id, client.intent, client.info))
        return result

    def get_client(self, client_id: str) -> Optional[tuple[list[str], Any]]:
        client = self._clients.get(client_id)
        if client is None:
            return None
        return (client.intent, client.info)

    def client_count(self, include_tunnel_controllers: bool = False) -> int:
        if include_tunnel_controllers:
            return len(self._clients)
        else:
            result = 0
            for client in self._clients.values():
                if client.tunnel_id != _TUNNEL_CONTROLLER or include_tunnel_controllers:
                    result += 1
            return result

    async def _send_socket_message(self,
            wsref: _WebsocketReference,
            topic: str,
            data: Any,
            tunnel_id: Optional[str] = None,
            client_id: Optional[str] = None,
            extra: Optional[dict[str, Any]] = None):

        tunnel_id = tunnel_id if wsref.is_tunnel and tunnel_id != _TUNNEL_NONE else None

        msg_data = {}
        if extra is not None:
            msg_data.update(extra)

        msg_data["topic"] = topic
        msg_data["data"] = data
        if tunnel_id is not None:
            msg_data[_FIELD_TUNNEL_ID] = tunnel_id

        tuninfo = "DIRECT"
        if wsref.is_tunnel:
            tuninfo = f"TUNNEL:{tunnel_id}" if tunnel_id is not None else f"TUNNEL:TUNNEL"
        if client_id is None:
            client_id = "*" if tunnel_id == _TUNNEL_CLIENTS else "TUNNEL"

        self._debug_log(f"[SEND on {wsref.socket_id} to {client_id}][{tuninfo}] {topic}")
        msg = self._transport_pack(msg_data)
        try:
            await wsref.socket.send(msg)
            return True
        except:
            self._logger.error(f"Error during SEND on {wsref.socket_id} to {client_id}!", exc_info=True)
            return False

    async def send_tunnel_message(self, topic: str, data: Any, target: WebsocketTunnelTarget, extra: Optional[dict[str, Any]] = None) -> bool:
        results: list[bool] = []
        for wsref in self._wsrefs.values():
            if wsref.is_tunnel:
                tunnel_id = _TUNNEL_NONE
                if target == WebsocketTunnelTarget.ALL:
                    tunnel_id = _TUNNEL_NONE
                elif target == WebsocketTunnelTarget.CONTROLLER:
                    tunnel_id = _TUNNEL_CONTROLLER
                elif target == WebsocketTunnelTarget.CLIENTS:
                    tunnel_id = _TUNNEL_CLIENTS
                results.append(await self._send_socket_message(wsref, topic, data, tunnel_id, extra=extra))
        return len(results) > 0 and all(results)

    async def send_client_message(self, topic: str, data: Any, client_id: str, extra: Optional[dict[str, Any]] = None) -> bool:
        client = self._clients.get(client_id)
        if client is None:
            return False
        wsref = self._wsrefs.get(client.socket_id)
        if wsref is None:
            return False
        return await self._send_socket_message(wsref, topic, data, client.tunnel_id, client_id=client_id, extra=extra)

    async def send_broadcast_message(self, topic: str, data: Any, intent_filter: Optional[str] = None, extra: Optional[dict[str, Any]] = None):
        for wsref in self._wsrefs.values():
            if not wsref.is_tunnel:
                for client_id in wsref.clients.values():
                    client = self._clients.get(client_id)
                    if client is not None and (intent_filter is None or intent_filter in client.intent):
                        await self._send_socket_message(wsref, topic, data, client_id=client.client_id, extra=extra)
            else:
                send_tunnel_broadcast = True
                target_clients: list[_WebsocketClient] = []
                if intent_filter is not None:
                    for client_id in wsref.clients.values():
                        client = self._clients.get(client_id)
                        if client is not None:
                            if intent_filter in client.intent or client.tunnel_id == _TUNNEL_CONTROLLER:
                                target_clients.append(client)
                            else:
                                send_tunnel_broadcast = False

                if send_tunnel_broadcast:
                    await self._send_socket_message(wsref, topic, data, tunnel_id=_TUNNEL_CLIENTS, extra=extra)
                else:
                    for client in target_clients:
                        await self._send_socket_message(wsref, topic, data, tunnel_id=client.tunnel_id, client_id=client.client_id, extra=extra)

    async def send_message(self, topic: str, data: Any, client_id: Optional[str], intent_filter: Optional[str] = None, extra: Optional[dict[str, Any]] = None):
        client_id = client_id if isinstance(client_id, str) else None
        if client_id is not None and len(client_id) > 0:
            await self.send_client_message(topic, data, client_id, extra=extra)
        else:
            await self.send_broadcast_message(topic, data, intent_filter, extra=extra)

    async def _authorize_client(self, socket_id: str, tunnel_id: str, data: Any) -> bool:
        # check if is tunnel controller
        is_tunnel_controller = self._is_tunnel_controller(tunnel_id)

        # validate direct or tunnelled client and update wsref is_tunnel flag
        wsref = self._wsrefs[socket_id]
        if wsref.is_tunnel:
            if tunnel_id == _TUNNEL_NONE:
                self._logger.warning(f"Non-tunnelled client tried to authorize to a tunnelled socket [{socket_id}]!")
                return False
        else:
            if tunnel_id != _TUNNEL_NONE:
                if len(wsref.clients) == 0:
                    self._wsrefs[socket_id].is_tunnel = True
                else:
                    self._logger.warning(f"Tunnelled client tried to authorize with tunnel id [{tunnel_id}] on a direct socket [{socket_id}]!")
                    return False

        # get client data
        info: Any = None
        intent: list = []
        if data is not None and isinstance(data, dict):
            info = data.get('info')
            intent_data = data.get('intent')
            if intent_data is not None and isinstance(intent_data, list):
                intent = intent_data

        # find or generate client id
        client_id: str = ""
        existing_client_id = self._wsrefs[socket_id].clients.get(tunnel_id)
        existing_client: Optional[_WebsocketClient] = None
        if existing_client_id is not None:
            client_id = existing_client_id
            existing_client = self._clients.get(existing_client_id)
        else:
            client_id = secrets.token_hex(6)

        # add or update client
        self._clients[client_id] = _WebsocketClient(
            socket_id=socket_id,
            client_id=client_id,
            tunnel_id=tunnel_id,
            intent=intent,
            info=info)
        # store client reference in the socket tunneling map
        self._wsrefs[socket_id].clients[tunnel_id] = client_id

        # notify client connected listeners when new client is authorized
        if existing_client_id is None:
            self._logger.info(f"Client [{client_id}] on socket [{socket_id}] connected!")
            if is_tunnel_controller:
                await self._on_tunnel_controller_connected(client_id)
            else:
                await self._on_client_connected(client_id)

        # confirm authorization
        if not is_tunnel_controller:
            await self._send_socket_message(wsref, _TOPIC_AUTHORIZE, { 'client_id': client_id, 'intent': intent }, tunnel_id, client_id=client_id)

        # log client authorized
        if is_tunnel_controller:
            self._logger.info(f"Tunnel controller client [{client_id}] authorized on socket [{socket_id}] with info [{info}]!")
        else:
            self._logger.info(f"Client [{client_id}] on socket [{socket_id}] authorized as {intent}!")

        # notify authorized
        if existing_client is None or existing_client.intent != intent or existing_client.info != info:
            await self._on_client_authorized(client_id, intent, info)

        return True

    async def _deauthorize_client(self, socket_id: str, tunnel_id: str) -> bool:
        # check if is tunnel controller
        is_tunnel_controller = self._is_tunnel_controller(tunnel_id)
        client_id = self._wsrefs[socket_id].clients.get(tunnel_id)
        if client_id is not None:
            del self._wsrefs[socket_id].clients[tunnel_id]
        if client_id in self._clients:
            del self._clients[client_id]
            self._logger.info(f"Client [{client_id}] on socket [{socket_id}] disconnected!")

            # notify client disconnected
            if is_tunnel_controller:
                await self._on_tunnel_controller_disconnected(client_id)
            else:
                await self._on_client_disconnected(client_id)

            return True
        else:
            return False

    async def _handler(self, websocket, path):
        socket_id = secrets.token_hex(6)

        # store reference
        self._wsrefs[socket_id] = _WebsocketReference(websocket, socket_id, path)

        self._logger.info(f"Socket [{socket_id}] connected!")
        tasks = set()

        try:
            async for message in websocket:
                parsed = self._transport_unpack(message)
                topic = None
                data = None
                if isinstance(parsed, dict):
                    # check topic
                    topic = parsed.get("topic")
                    if topic is None or not isinstance(topic, str):
                        continue

                    # parse message
                    data = parsed.get("data")
                    tunnel_id = parsed.get(_FIELD_TUNNEL_ID)

                    # check tunnel id
                    if tunnel_id is not None and not isinstance(tunnel_id, str):
                        self._logger.warning(f"Invalid message tunneling id on socket [{socket_id}]! Tunnelling id must be none or a string!")
                        return False
                    if tunnel_id is None or not isinstance(tunnel_id, str):
                        tunnel_id = _TUNNEL_NONE

                    # handle messages
                    if topic == _TOPIC_AUTHORIZE:
                        await self._authorize_client(
                                socket_id=socket_id,
                                tunnel_id=tunnel_id,
                                data=data)
                    elif topic == _TOPIC_DEAUTHORIZE:
                        await self._deauthorize_client(
                                socket_id=socket_id,
                                tunnel_id=tunnel_id)
                    else:
                        client: Optional[_WebsocketClient] = None
                        client_id = self._wsrefs[socket_id].clients.get(tunnel_id)
                        if client_id is not None:
                            client = self._clients.get(client_id)

                        if client_id is None or client is None:
                            self._logger.warning(f"Socket [{socket_id}] received messsage ['{topic}'] from unauthorized client!")
                            continue

                        self._debug_log(f"[RECV on [{socket_id}] from {client_id}] {topic}")
                        is_tunnel_controller = self._is_tunnel_controller(tunnel_id)
                        task = asyncio.get_running_loop().create_task(self._on_message_received(client_id, topic, data, parsed, is_tunnel_controller))
                        tasks.add(task)
                        task.add_done_callback(tasks.discard)

        except:
            self._logger.error(f"Unexpected socket [{socket_id}] error in handler loop!", exc_info=True)

        # socket closed - get all clients and remove socket reference
        disconnect_clients: list[str] = list(self._wsrefs[socket_id].clients.values())
        del self._wsrefs[socket_id]

        if len(tasks) > 0:
            self._logger.info(f"Socket [{socket_id}] disconnected, cancelling {len(tasks)} pending tasks...")
            for task in tasks:
                try:
                    task.cancel()
                except:
                    pass

        if len(disconnect_clients) > 0:
            self._logger.info(f"Socket [{socket_id}] disconnected, removing {len(disconnect_clients)} clients...")
            for client_id in disconnect_clients:
                client = self._clients.get(client_id)
                if client is not None:
                    is_tunnel_controller = self._is_tunnel_controller(client.tunnel_id)
                    del self._clients[client_id]
                    self._logger.info(f"Client [{client_id}] on socket [{socket_id}] disconnected!")
                    if is_tunnel_controller:
                        await self._on_tunnel_controller_disconnected(client_id)
                    else:
                        await self._on_client_disconnected(client_id)

        self._logger.info(f"Socket [{socket_id}] disconnected")

    async def run_server(self):
        await self._on_run_websocket_server()
        async with websockets.serve(self._handler, self._host, int(self._port)):
            self._logger.info(f"Started on port: {self._port}")
            await asyncio.Future()

    def destroy(self):
        self._on_destroy()
        for _, wsref in self._wsrefs.items():
            wsref.socket.close()
        self._wsrefs.clear()
        self._clients.clear()

