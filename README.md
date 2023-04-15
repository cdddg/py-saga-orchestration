# Python Saga Orchestration

OrchestrationBuilder is a utility class for building Saga-style transactions using a sequence of steps, where each step consists of an operation and a compensation function. Transactions will be executed sequentially, and step-by-step compensation is supported.

This code is for reference only, inspired by my work experience in 2022

#### Usage

```python
builder = OrchestrationBuilder()
builder.add_step(action_1, compensation_1)
builder.add_step(action_2, compensation_2)
...
builder.add_step(action_n, compensation_n)
saga = await builder.execute()
```

#### References

- https://github.com/flowpl/saga_py
- https://github.com/serramatutu/py-saga
- https://github.com/microservices-patterns/ftgo-application/blob/master/ftgo-order-service/src/main/java/net/chrisrichardson/ftgo/orderservice/sagas/createorder/CreateOrderSaga.java