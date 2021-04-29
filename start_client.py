import asyncio

import websockets
import json
from strawberry.asgi.constants import *
import argparse

async def send_json(ws, obj):
    return await ws.send(json.dumps(obj))


async def receive_json(ws):
    return json.loads(await ws.recv())


async def connect_to_server(disconnect_after):
    uri = "ws://127.0.0.1:8000/graphql/"

    async with websockets.connect(uri, subprotocols="graphql-ws") as ws:
        await send_json(ws, {"type": GQL_CONNECTION_INIT})
        await send_json(ws, {
            "type": GQL_START,
            "id": "demo",
            "payload": {"query": "subscription { test }"},
        })

        _ = await receive_json(ws)  # ACK

        # wait after the queue is depleted (infinite wait)
        await asyncio.sleep(disconnect_after)

async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-s", action="store_true", help="Expect to success (stop before queue waiting)")
    args = parser.parse_args()

    if args.s:
        await connect_to_server(0.5)
    else:
        await connect_to_server(3.0)

asyncio.run(main())