import asyncio
import typing
import os
from strawberry.asgi import GraphQL
from starlette.applications import Starlette
import strawberry
import logging

os.environ["PYTHONASYNCIODEBUG"] = "1"

logging.basicConfig(
    format='%(asctime)s %(levelname)-8s %(message)s',
    level=logging.INFO,
    datefmt='%Y-%m-%d %H:%M:%S')

@strawberry.type
class Query:
    @strawberry.field
    def hello(self) -> str:
        return "World"

@strawberry.type
class Subscription:
    @strawberry.subscription
    async def test(self) -> float:
        q = asyncio.Queue()
        [q.put_nowait(x) for x in range(2)]

        try:
            while True:
                logging.info("1. Waiting for the queue")
                val = await q.get()
                logging.info("2. Got value from queue")
                yield val
                await asyncio.sleep(1)
        except GeneratorExit:
            logging.info("2. Generator Quit")
        except BaseException as e:
            logging.error(f"2. Generator Error: {type(e)} {str(e)}")


schema = strawberry.Schema(Query, subscription=Subscription)

graphql = GraphQL(schema)

app = Starlette()
app.mount("/graphql", graphql)
