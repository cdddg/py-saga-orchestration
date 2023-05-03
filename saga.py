from inspect import isawaitable
from typing import Any, Callable, Optional, Union
from dataclasses import dataclass


class SagaError(Exception):
    def __init__(self, action_exception, compensation_exceptions):
        self.action = action_exception
        self.compensations = compensation_exceptions


@dataclass
class Action:
    action: Callable[..., Any]
    compensation: Callable[..., Any]
    compensation_args: Optional[Union[tuple[Any], list[Any]]] = None
    result: Optional[Any] = None

    async def act(self, *args):
        result = self.action(*(args if self.action.__code__.co_varnames else []))
        if isawaitable(result):
            result = await result

        return result

    async def compensate(self):
        result = self.compensation(
            *(self.compensation_args if self.compensation.__code__.co_varnames else [])  # pyright:ignore
        )
        if isawaitable(result):
            result = await result

        return result


@dataclass
class Saga:
    """
    The Saga class provides a way to manage Saga-style transactions using a sequence of steps,
    where each step consists of an operation and a compensation function. Transactions will be
    executed sequentially, and step-by-step compensation is supported.

    Methods:
        execute(self) -> Any:
            Execute the saga, sequentially executing each action and storing the result for
            compensation use in case of failure. If any action fails, compensation functions will
            be called in reverse order for each executed action.
    """
    steps: list[Action]

    async def execute(self):
        args = []
        for index, action in enumerate(self.steps):
            if isinstance(action, Action):
                try:
                    actioned_result = await action.act(*args)
                    if actioned_result is None:
                        args = []
                    elif isinstance(actioned_result, (list, tuple)):
                        args = actioned_result
                    else:
                        args = (actioned_result,)
                    action.compensation_args = args
                    action.result = actioned_result
                except Exception as action_exception:
                    compensation_exceptions = await self._run_compensations(index)
                    raise SagaError(action_exception, compensation_exceptions)

        return self

    async def _run_compensations(self, last_action_index: int):
        compensation_exceptions = []
        for compensation_index in range(last_action_index - 1, -1, -1):
            try:
                action = self.steps[compensation_index]
                await action.compensate()
            except Exception as ex:
                compensation_exceptions.append(ex)

        return compensation_exceptions


class OrchestrationBuilder:
    """
    OrchestrationBuilder is a utility class for building a saga-style transaction using a series of
    steps, where each step consists of an action and a compensation function. The transaction will be
    executed in sequence and support compensation on a per-step basis.

    Usage:
    ```
    builder = OrchestrationBuilder()
    builder.add_step(action_1, compensation_1)
    builder.add_step(action_2, compensation_2)
    ...
    builder.add_step(action_n, compensation_n)
    saga = await builder.execute()
    ```

    Methods:
    - add_step(action: Callable[..., Any], compensation: Callable[..., Any]) -> OrchestrationBuilder:
        Adds a step to the transaction, consisting of an action and a compensation function.
        Both action and compensation functions can be synchronous or asynchronous. Returns
        the current OrchestrationBuilder instance.

    - execute() -> Saga:
        Builds and executes a Saga instance representing the transaction. When an action function
        completes successfully, its response will be passed to the next action function as a parameter.
        If an action function fails, the Saga will compensate for the previously executed actions.

        For example, if action_n fails, the compensations will be executed in the following order:
        compensation_n-1, compensation_n-2, ..., compensation_1. Finally raises a SagaError.

    OrchestrationBuilder instance methods should be chained together to build up the desired
    sequence of actions and compensations.

    When the action function completes, its response will be passed to the corresponding compensation
    function as a parameter.

    See also:
    - Saga
    """

    def __init__(self):
        self.steps: list[Action] = []

    def add_step(self, action: Callable[..., Any], compensation: Callable[..., Any]) -> 'OrchestrationBuilder':
        action_ = Action(action, compensation)
        self.steps.append(action_)

        return self

    async def execute(self) -> Saga:
        return await Saga(self.steps).execute()

