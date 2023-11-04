# Python Saga Orchestration

The Saga Orchestration pattern provides a mechanism to manage data consistency across microservices without relying on distributed transactions. In this design, each saga orchestrates a series of local transactions. If a local transaction fails, compensating transactions are executed to rollback any preceding transactions, ensuring data integrity. 

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

## Examples

1. **Basic Usage**

   ```python
   async def action_1():
       print('action_1()')
       return "result_1"
   
   async def action_2():
       print('async_action_2()')
       return "result_2"
   
   builder = OrchestrationBuilder()
   builder.add_step(action_1, lambda: None)
   builder.add_step(action_2, lambda: None)
   asyncio.run(builder.execute())
   
   # >>> Output:
   # action_1()
   # async_action_2()
   ```

2. **Use Arguments or the Return Value of the Previous Action**

   To pass the result of a prior action to a subsequent one, you can use lambda functions. This design allows easy chaining of the results. The result of the previous action is always passed as the first argument to the next action using a lambda function.

   ```python
   async def action_1():
       print('async_action_1()')
       return 'result_1'
   
   async def action_2(a, b, *args):
       print(f'async_action_2(a={a}, b={b}, args={args}')
       return 'result_2'
   
   async def action_3(*args, c, d):
       print(f'async_action_3(args={args}, c={c}, d={d}')
       return 'result_3'
   
   async def action_4(a, b, *args, c, d, **kwargs):
       print(f'async_action_4(a={a}, b={b}, args={args}, c={c}, d={d}, kwargs={kwargs}')
       return 'result_4'
   
   builder = (
       OrchestrationBuilder()
       .add_step(action_1, lambda: None)
       .add_step(lambda prev_act_res, a=1, b=2: action_2(a, b, prev_act_res), lambda: None)
       .add_step(lambda prev_act_res, c=3, d=4: action_3(prev_act_res, c=c, d=d), lambda: None)
       .add_step(lambda prev_act_res, a=1, b=2, c=3, d=4, e=5, f=6: action_4(a, b, prev_act_res, c=c, d=d, e=e, f=f), lambda: None)
   )
   asyncio.run(builder.execute())
   
   # >>> Output:
   # async_action_1()
   # async_action_2(a=1, b=2, args=('result_1',)
   # async_action_3(args=('result_2',), c=3, d=4)
   # async_action_4(a=1, b=2, args=('result_3',), c=3, d=4, kwargs={'e': 5, 'f': 6}
   ```

3. **Orchestration with Compensation**

   This example demonstrates the compensation feature of the Saga Orchestration. Here, `action_2` raises a `RuntimeError` which triggers the Saga to attempt to compensate for the previously executed actions. The result of `action_1` is then passed to its corresponding compensation function `compensation_1`.

   ```python
   async def action_1():
       print('async_action_1()')
       return 'result_1'
   
   async def compensation_1(result):
       print(f'async_compensation_1({result})')
   
   async def action_2():
       print('async_action_2()')
       raise RuntimeError('test')
   
   builder = (
       OrchestrationBuilder()
       .add_step(action_1, lambda curr_act_res: compensation_1(curr_act_res))
       .add_step(action_2, lambda: None)
   )
   asyncio.run(builder.execute())
   
   # >>> Output:
   # async_action_1()
   # async_action_2()
   # async_compensation_1(result_1)
   # Traceback (most recent call last):
   #   File "<string>", in <module>
   #   File "<string>", in in execute
   #     raise SagaError(index, exc, action_traceback, compensation_exceptions)
   # SagaError: A critical error occurred during the saga execution, resulting in transaction failure and compensation attempts.
   #
   # Transaction failed at step 1 due to an unexpected RuntimeError, triggering the compensation process.
   #   ╎Traceback (most recent call last):
   #   ╎  File "<string>", in <module>
   #   ╎  File "<string>", in action_2
   #   ╎    raise RuntimeError('test')
   #   ╎RuntimeError: test
   ```

## References

- https://github.com/flowpl/saga_py
- https://github.com/serramatutu/py-saga
- https://github.com/microservices-patterns/ftgo-application/blob/master/ftgo-order-service/src/main/java/net/chrisrichardson/ftgo/orderservice/sagas/createorder/CreateOrderSaga.java
