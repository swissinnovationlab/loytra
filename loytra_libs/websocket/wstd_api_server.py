from typing import Any, Callable, Awaitable, Optional
from loytra_libs.websocket.wstd_server_base import WSTDServerBase, WebsocketMessageTransport

# auto-response
class WebsocketMessageResponse:
    def __init__(self,
            data: Any,
            topic: Optional[str] = None,
            broadcast: bool = False,
            intent_filter: Optional[str] = None):

        self.data = data
        self.topic = topic
        self.broadcast = broadcast
        self.intent_filter = intent_filter


class WSTDApiServer(WSTDServerBase):
    def __init__(self,
            debug_mode: bool,
            port: int,
            transport: WebsocketMessageTransport = WebsocketMessageTransport.MSGPACK,
            on_client_connected: Optional[Callable[['WSTDApiServer', str], Awaitable[Any]]] = None,
            on_client_authorized: Optional[Callable[['WSTDApiServer', str, list[str], Any], Awaitable[Any]]] = None,
            on_client_disconnected: Optional[Callable[['WSTDApiServer', str], Awaitable[Any]]] = None,
            on_tunnel_controller_connected: Optional[Callable[['WSTDApiServer', str], Awaitable[Any]]] = None,
            on_tunnel_controller_disconnected: Optional[Callable[['WSTDApiServer', str], Awaitable[Any]]] = None,
            on_receive_unhandled: Optional[Callable[[str, str, Any], Awaitable[Any]]] = None):

        super().__init__(debug_mode, port, transport)

        self._on_client_connected_listener = on_client_connected
        self._on_client_authorized_listener = on_client_authorized
        self._on_client_disconnected_listener = on_client_disconnected
        self._on_tunnel_controller_connected_listener = on_tunnel_controller_connected
        self._on_tunnel_controller_disconnected_listener = on_tunnel_controller_disconnected
        self._on_receive_unhandled = on_receive_unhandled

        self._methods: dict[str, Callable[[str, str, Any], Awaitable[Any]]] = {}

    def method(self, topic_prefix: str):
        def decorator(func: Callable[[str, str, Any], Awaitable[Any]]):
            self._methods[topic_prefix] = func
            return func
        return decorator

    def set_on_client_connected_listener(self, listener: Callable[['WSTDApiServer', str], Awaitable[Any]]):
        self._on_client_connected_listener = listener

    def set_on_client_authorized_listener(self, listener: Callable[['WSTDApiServer', str, list[str], Any], Awaitable[Any]]):
        self._on_client_authorized_listener = listener

    def set_on_client_disconnected_listener(self, listener: Callable[['WSTDApiServer', str], Awaitable[Any]]):
        self._on_client_disconnected_listener = listener

    def set_on_tunnel_controller_connected_listener(self, listener: Callable[['WSTDApiServer', str], Awaitable[Any]]):
        self._on_tunnel_controller_connected_listener = listener

    def set_on_tunnel_controller_disconnected_listener(self, listener: Callable[['WSTDApiServer', str], Awaitable[Any]]):
        self._on_tunnel_controller_disconnected_listener = listener

    def set_on_receive_unhandled_listener(self, listener: Callable[[str, str, Any], Awaitable[Any]]):
        self._on_receive_unhandled = listener

    async def _on_client_connected(self, client_id: str):
        if self._on_client_connected_listener is not None:
            await self._on_client_connected_listener(self, client_id)

    async def _on_client_authorized(self, client_id: str, intent: list[str], info: Any):
        if self._on_client_authorized_listener is not None:
            await self._on_client_authorized_listener(self, client_id, intent, info)

    async def _on_client_disconnected(self, client_id: str):
        if self._on_client_disconnected_listener is not None:
            await self._on_client_disconnected_listener(self, client_id)

    async def _on_tunnel_controller_connected(self, client_id: str):
        if self._on_tunnel_controller_connected_listener is not None:
            await self._on_tunnel_controller_connected_listener(self, client_id)

    async def _on_tunnel_controller_disconnected(self, client_id: str):
        if self._on_tunnel_controller_disconnected_listener is not None:
            await self._on_tunnel_controller_disconnected_listener(self, client_id)

    async def _check_auto_response(self, sender_cid: str, sender_topic: str, response: Any):
        if response is not None and isinstance(response, WebsocketMessageResponse):
            response_topic = sender_topic if response.topic is None else response.topic
            response_cid: Optional[str] = None if response.broadcast else sender_cid
            await self.send_message(response_topic, response.data, response_cid, response.intent_filter)

    async def _on_message_received(self, client_id: str, topic: str, data: Any, message: dict[str, Any], client_is_tunnel_controller: bool):
        # call bound methods
        handled = False
        for topic_prefix, func in self._methods.items():
            if topic.startswith(topic_prefix):
                response = await func(client_id, topic, data)
                await self._check_auto_response(client_id, topic, response)
                handled = True

        # call unhandled message listener
        if not handled and self._on_receive_unhandled is not None:
            response = await self._on_receive_unhandled(client_id, topic, data)
            await self._check_auto_response(client_id, topic, response)

