import os
import os.path
import asyncio
import websockets
import json
import dataclasses as dc
from typing import Any


@dc.dataclass(frozen=True, slots=True)
class ApiConn:
    host: str = dc.field()
    port: int = dc.field()
    use_ssl: bool = dc.field()
    api_key: str = dc.field()
    app_key: str = dc.field()

@dc.dataclass(frozen=True, slots=True)
class ApiMethod:
    topic: str = dc.field()
    data: Any = dc.field(default=None)


@dc.dataclass(frozen=True, slots=True)
class ApiSpec:
    api: ApiConn = dc.field()
    monitor: list[str] = dc.field(default_factory=lambda: [])
    methods: list[ApiMethod] = dc.field(default_factory=lambda: [])


async def _send(ws, topic, data):
    msg = { "topic": topic, "data": data }
    print("SEND:", msg)
    data = json.dumps(msg)
    await ws.send(data)

async def _recv(ws) -> tuple[str, Any]:
    data = await ws.recv()
    msg = json.loads(data)
    print("RECV:", msg)

    topic = ""
    data = None
    if msg is not None and isinstance(msg, dict):
        topic = msg.get('topic', "")
        data = msg.get('data')
    return (topic, data)

async def _send_app_message(socket, app_key, dev_key, svc_key, topic, data):
    await _send(socket, f"device/app/{app_key}/{dev_key}/{svc_key}/{topic}", data)

async def _handle_app_message(socket, spec: ApiSpec, app_key: str, dev_key: str, svc_key: str, topic: str, data: Any):
    for method in spec.methods:
        if method.topic == topic:
            response_data = method.data if method.data is not None else data
            await _send_app_message(socket, app_key, dev_key, svc_key, topic, response_data)

async def _handle_message(socket, spec: ApiSpec, topic: str, data: Any):
    if topic.startswith("device/app/"):
        parts = topic.removeprefix("device/app/").split("/")
        if len(parts) >= 4:
            app_key = parts[0]
            dev_key = parts[1]
            svc_key = parts[2]
            app_topic = "/".join(parts[3:])
            await _handle_app_message(socket, spec, app_key, dev_key, svc_key, app_topic, data)

async def _websocket_loop(websocket, spec: ApiSpec):
    await _send(websocket, "authorize", spec.api.api_key)
    await _recv(websocket)

    if len(spec.api.app_key) > 0:
        await _send(websocket, "self/apps/bind", [spec.api.app_key])
        await _recv(websocket)

    if len(spec.monitor) > 0:
        await _send(websocket, "device/state", { "action": "get", "devices": spec.monitor })
        await _recv(websocket)
        await _send(websocket, "device/state", { "action": "subscribe", "devices": spec.monitor })

    while True:
        recv_topic, recv_data = await _recv(websocket)
        await _handle_message(websocket, spec, recv_topic, recv_data)

def _get_url(host: str, port: int, use_ssl: bool):
    prefix = "wss" if use_ssl else "ws"
    return prefix + "://" + host + ":" + str(port) + "/api/websocket"

async def _client_loop(spec: ApiSpec):
    url = _get_url(spec.api.host, spec.api.port, spec.api.use_ssl)
    async with websockets.connect(url) as websocket:
        print("CONNECTED to: " + url)
        try:
            await _websocket_loop(websocket, spec)
        except:
            print("CONNECTION CLOSED")

def _parse_spec(data):
    api_conn_data = data.get('api')
    if api_conn_data is None or not isinstance(api_conn_data, dict):
        print(f"Invalid API connection data!")
        return None

    api_conn = ApiConn(
        host=api_conn_data.get('host', "").strip(),
        port=api_conn_data.get('port', 0),
        use_ssl=api_conn_data.get('use_ssl', True),
        api_key=api_conn_data.get('api_key', "").strip(),
        app_key=api_conn_data.get('app_key', "").strip())

    if len(api_conn.host) == 0 or api_conn.port <= 0:
        print("Invalid API host or port!")
        return None

    if len(api_conn.api_key) == 0:
        print("Invalid API key!")
        return None

    monitor = data.get('monitor')
    if monitor is None or not isinstance(monitor, list):
        monitor = []

    methods: list[ApiMethod] = []
    methods_spec = data.get('methods')
    if methods_spec is None or not isinstance(methods_spec, list):
        methods_spec = []

    for method_spec in methods_spec:
        method_topic = method_spec.get('topic')
        if method_topic is None or not isinstance(method_topic, str):
            continue

        method_data = method_spec.get('data')

        methods.append(ApiMethod(
            topic=method_topic,
            data=method_data))

    return ApiSpec(
        api=api_conn,
        monitor=monitor,
        methods=methods)


def run(definition_path):
    if os.path.exists(definition_path):
        with open(definition_path, "r") as f:
            data = json.loads(f.read())

        spec = _parse_spec(data)
        if spec is not None:
            asyncio.run(_client_loop(spec))
        else:
            print(f"API definition parse failed!")
    else:
        print(f"Invalid API definition path: {definition_path}")

