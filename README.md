# Repo Description

Reproducing https://github.com/strawberry-graphql/strawberry/issues/889#issuecomment-829420393

# Problem Description

The strawberry subscription uses an async generator to generate real-time data to the client. It is a common pattern to
use `asyncio.Queue` to transform the stream from `RxPY` observable to async stream. In this case, the `queue.get`
will block and wait until new data arrives.

It was observed that when the queue is empty and waiting and when the (websocket) client disconnects, the server side
could not correctly stop the async generator and task. See the traceback in
the [issue](https://github.com/strawberry-graphql/strawberry/issues/889#issuecomment-829420393). 

Also, Python 3.7 seems having a different error behavior. It will cause error no matter the queue is working or 
waiting.


# Usage
1. install the dependencies
```
pip install -r requirements.txt
```

2. run the server
```
python start_server.py
```

3. run the client to reproduce the error on the server side.
```
python start_client.py
```

Or run with `-s` to reproduce the expected behavior.
```
python start_client.py -s
```

# Expected result
On the server side, if the log ends with either `2. Generator Quit` or `2. Generator Error ...`, it should be 
considered working because there is a way to clean up the generator when the client disconnects.

The following log was from the client with `-s` flag.
```
2021-04-29 16:28:58 INFO     ('127.0.0.1', 61860) - "WebSocket /graphql/" [accepted]
2021-04-29 16:28:58 INFO     1. Waiting for the queue
2021-04-29 16:28:58 INFO     2. Got value from queue
2021-04-29 16:28:59 INFO     1. Waiting for the queue
2021-04-29 16:28:59 INFO     2. Got value from queue
2021-04-29 16:28:59 INFO     2. Generator Quit
```

When there is no `-s` flag the generator is never cleaned up:
```
INFO:     ('127.0.0.1', 62218) - "WebSocket /graphql/" [accepted]
2021-04-29 16:41:28 INFO     ('127.0.0.1', 62218) - "WebSocket /graphql/" [accepted]
2021-04-29 16:41:28 INFO     1. Waiting for the queue
2021-04-29 16:41:28 INFO     2. Got value from queue
2021-04-29 16:41:29 INFO     1. Waiting for the queue
2021-04-29 16:41:29 INFO     2. Got value from queue
2021-04-29 16:41:30 INFO     1. Waiting for the queue
```

# Different behavior in GraphiQL
The error seems different when using the GraphiQL client tester.
## Procedures
1. start server
2. go to http://127.0.0.1:8000/graphql/
3. subscribe to 
```
subscription {
   test
}
```
4. wait for about 5 seconds
5. refresh the page

The error message on the server side becomes
```
INFO:     127.0.0.1:62513 - "POST /graphql/ HTTP/1.1" 200 OK
2021-04-29 16:50:28 INFO     1. Waiting for the queue
2021-04-29 16:50:30 INFO     1. Waiting for the queue
2021-04-29 16:50:30 INFO     2. Got value from queue
2021-04-29 16:50:31 INFO     1. Waiting for the queue
2021-04-29 16:50:31 INFO     2. Got value from queue
2021-04-29 16:50:32 INFO     1. Waiting for the queue
INFO:     127.0.0.1:62518 - "GET /graphql/ HTTP/1.1" 200 OK
INFO:     ('127.0.0.1', 62519) - "WebSocket /graphql/" [accepted]
2021-04-29 16:50:35 INFO     ('127.0.0.1', 62519) - "WebSocket /graphql/" [accepted]
2021-04-29 16:50:35 ERROR    Task was destroyed but it is pending!
source_traceback: Object created at (most recent call last):
(omitted)
task: <Task pending name='Task-91' coro=<<async_generator_asend without __name__>()> wait_for=<Future pending cb=[<TaskWakeupMethWrapper object at 0x000001FDD5BB9A60>()] created at C:\Users\wuyua\anaconda3\envs\patstack\lib\asyncio\base_events.py:422> created at C:\Users\wuyua\anaconda3\envs\patstack\lib\site-packages\graphql\subscription\map_async_iterator.py:44>
INFO:     127.0.0.1:62518 - "POST /graphql/ HTTP/1.1" 200 OK
2021-04-29 16:50:35 ERROR    2. Generator Error: <class 'RuntimeError'> cannot reuse already awaited coroutine

```

I did observe the double-release happening when using GraphiQL. [This block](https://github.
com/strawberry-graphql/strawberry/blob/f31e6c17238ba4372129c4f291ddf336b4e6b901/strawberry/asgi/__init__.py#L149) 
was re-entrant when GraphiQL page was refreshed. I could not confirm whether this led to the error. When 
using the `websockets` python client, this re-entrancy was not observed.


# Impact and conclusion
This bug/behavior leads to unreliable asynchronous generator finalization process. There could be two situations 
during finalization: 
1. the `queue.get` will block forever after the client is disconnected
2. the incorrect exception was thrown (other than `GeneratorExit`)

The second could be caught using some workarounds but the first one means there is no way to stop the generator and 
we may need to wrap the `queue.get` in the `wait_for` wrapper. 
