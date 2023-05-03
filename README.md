# Python Saga Orchestration

OrchestrationBuilder is a class for building Saga-style transactions using a sequence of steps, where each step consists of an operation and a compensation function. Transactions are executed sequentially, and step-by-step compensation is supported.

This code is for reference only and was inspired by my work experience in 2022.

## Usage

```python
builder = OrchestrationBuilder()
builder.add_step(action_1, compensation_1)
builder.add_step(action_2, compensation_2)
...
builder.add_step(action_n, compensation_n)
saga = await builder.execute()
```

## Example

### Simple Example

In this simple example, we use OrchestrationBuilder to execute a Saga-style transaction that consists of two actions, with no compensation functions. The result of each action is not used in subsequent actions.

```python
import asyncio

async def action_1():
    print('action_1()')
    return "result_1"

async def action_2():
    print('action_2()')
    return "result_2"

builder = OrchestrationBuilder()
builder.add_step(action_1, lambda: None)
builder.add_step(action_2, lambda: None)
asyncio.run(builder.execute())
```

Output:

```
action_1()
action_2()
```

### Complex Example

This example demonstrates how to use OrchestrationBuilder in a chain style to execute a Saga-style transaction that consists of five actions, including both synchronous and asynchronous functions, each with its own compensation function. The result of each action is passed as an argument to the next action. If an error occurs during execution, a SagaError exception will be raised.

```python
import asyncio

async def action_1():
    print('async, action_1()')
    return 'result_1'

async def compensation_1(result):
    print(f'async, compensation_1({result})')

async def action_2(result):
    print(f'async, action_2({result})')
    return 'result_2'

async def compensation_2(result):
    print(f'async, compensation_2({result})')

async def action_3(*args):
    print(f'async, action_3{args}')
    return 'result_3'

async def compensation_3():
    print(f'async, compensation_3()')

def action_4(*args):
    print(f' sync, action_4{args}')
    return 'result_4'

def compensation_4():
    print(f' sync, compensation_4()')

async def action_5(result):
    print(f'async, action_5({result})')
    raise RuntimeError

builder = (
    OrchestrationBuilder()
    .add_step(action_1, lambda curr_act_res: compensation_1(curr_act_res))
    .add_step(lambda prev_act_res: action_2(prev_act_res), lambda curr_act_res: compensation_2(curr_act_res))
    .add_step(lambda: action_3(1, 2, 3), compensation_3)
    .add_step(lambda: action_4(4, 5, 6), compensation_4)
    .add_step(lambda prev_act_res: action_5(prev_act_res), lambda: None)
)
try:
    asyncio.run(builder.execute())
except SagaError as e:
    print(e)
```

Output:

```
async, action_1()
async, action_2(result_1)
async, action_3(1, 2, 3)
 sync, action_4(4, 5, 6)
async, action_5(result_4)
 sync, compensation_4()
async, compensation_3()
async, compensation_2(result_2)
async, compensation_1(result_1)
(RuntimeError(), [])
```

## References

- https://github.com/flowpl/saga_py
- https://github.com/serramatutu/py-saga
- https://github.com/microservices-patterns/ftgo-application/blob/master/ftgo-order-service/src/main/java/net/chrisrichardson/ftgo/orderservice/sagas/createorder/CreateOrderSaga.java
