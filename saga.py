import traceback
from dataclasses import dataclass, field
from inspect import isawaitable, signature
from typing import Any, Callable, NewType, Union

TracebackStr = NewType('TracebackStr', str)


class SagaError(Exception):
    def __init__(
        self,
        steps: list['Action'],
        failed_step_index: int,
        action_exception: Exception,
        action_traceback: TracebackStr,
        compensation_exception_tracebacks: dict[int, tuple[Exception, TracebackStr]],
    ):
        self.steps = steps
        self.failed_step_index = failed_step_index
        self.action_exception = action_exception
        self.action_traceback = action_traceback
        self.compensation_exception_tracebacks = compensation_exception_tracebacks

        super().__init__(self.build_header_message())

    def __str__(self):
        header_msg = (
            f'Saga execution failed at step {self.failed_step_index}: '
            f'{type(self.action_exception).__name__}: {self.action_exception}'
        )
        if self.compensation_exception_tracebacks:
            header_msg += f' (and {len(self.compensation_exception_tracebacks)} compensation step(s) failed)'


        registered_steps_msg = 'Registered Steps:\n' + '\n'.join(
            f'  [{i}] action: {step.action_call_repr}; compensation: {step.compensation_call_repr}'
            for i, step in enumerate(self.steps)
        )

        action_error_msg = (
            f'Transaction failed at step index {self.failed_step_index}: '
            f'An unexpected {type(self.action_exception).__name__} occurred, triggering the compensation process.'
            f'\n{self.format_traceback_indentation(self.action_traceback, 2)}'
        )

        compensation_error_msgs = ''
        if any(self.compensation_exception_tracebacks.values()):
            compensation_error_msgs = 'Compensations encountered errors:\n' + '\n'.join(
                [
                    f'  - (step index {step}): Compensation failed due to a {type(exc).__name__}: {exc}'
                    f'\n{self.format_traceback_indentation(traceback_str, 6)}'
                    for step, (exc, traceback_str) in self.compensation_exception_tracebacks.items()
                ]
            )

        return '\n\n'.join([header_msg, registered_steps_msg, action_error_msg, compensation_error_msgs]).strip()

    def build_header_message(self) -> str:
        msg = (
            f'Saga execution failed at step {self.failed_step_index}: '
            f'{type(self.action_exception).__name__}: {self.action_exception}'
        )
        if self.compensation_exception_tracebacks:
            msg += f' (and {len(self.compensation_exception_tracebacks)} compensation step(s) failed)'
        return msg

    def format_traceback_indentation(self, traceback_str: str, indent: int = 2) -> str:
        if '\n' in traceback_str:
            return '\n'.join([' ' * indent + '╎' + line for line in traceback_str.splitlines()])
        else:
            return traceback_str


@dataclass
class Action:
    action: Callable[..., Any]
    compensation: Callable[..., Any]

    _result: Any = field(init=False, default=None)
    _action_call_repr: str = field(init=False)
    _compensation_call_repr: str = field(init=False)
    _compensation_args: Union[tuple[Any], list[Any]] = field(init=False, default_factory=list)

    def __post_init__(self):
        self._action_call_repr = self._format_signature_preview(self.action)
        self._compensation_call_repr = self._format_signature_preview(self.compensation)

    def _format_signature_preview(self, func: Callable) -> str:
        func_name = func.__name__
        try:
            sig = signature(func)
            parts = []
            for name, param in sig.parameters.items():
                if param.default is not param.empty:
                    parts.append(f'{name}={param.default!r}')
                else:
                    parts.append(f'{name}=<?>')
            return f'{func_name}({", ".join(parts)})'
        except Exception:
            return f'{func_name}(...)'

    def _format_function_call(self, func: Callable, *args) -> str:
        func_name = func.__name__
        try:
            sig = signature(func)
            if not sig.parameters:
                return f'{func_name}()'
            if not args:
                return self._format_signature_preview(func)
            bound = sig.bind(*args)
            bound.apply_defaults()
            arg_str = ', '.join(f'{k}={v!r}' for k, v in bound.arguments.items())
            return f'{func_name}({arg_str})'
        except Exception:
            return f'{func_name}(...)'

    @property
    def action_call_repr(self) -> str:
        return str(self._action_call_repr)

    @property
    def compensation_call_repr(self) -> str:
        return str(self._compensation_call_repr)

    @property
    def result(self) -> Any:
        return self._result

    async def act(self, *args) -> Any:
        self._action_call_repr = self._format_function_call(self.action, *args)
        result = self.action(*(args if self.action.__code__.co_varnames else []))
        if isawaitable(result):
            result = await result

        return result

    async def compensate(self) -> Any:
        args = self._compensation_args if self.compensation.__code__.co_varnames else []
        self._compensation_call_repr = self._format_function_call(self.compensation, *args)
        result = self.compensation(*args)
        if isawaitable(result):
            result = await result

        return result


@dataclass
class Saga:
    steps: list[Action]

    async def execute(self) -> 'Saga':
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
                    action._compensation_args = args
                    action._result = actioned_result
                except Exception as exc:
                    action_traceback_str = TracebackStr(traceback.format_exc())
                    compensation_exceptions = await self._run_compensations(index)
                    raise SagaError(self.steps, index, exc, action_traceback_str, compensation_exceptions)

        return self

    async def _run_compensations(self, last_action_index: int) -> dict[int, tuple[Exception, TracebackStr]]:
        compensation_exceptions = {}
        for compensation_index in range(last_action_index - 1, -1, -1):
            try:
                action = self.steps[compensation_index]
                await action.compensate()
            except Exception as exc:
                _, _, traceback_str = traceback.format_exc().partition(
                    'During handling of the above exception, another exception occurred:\n\n'
                )
                compensation_exceptions[compensation_index] = (exc, TracebackStr(traceback_str))

        return compensation_exceptions


class OrchestrationBuilder:
    def __init__(self):
        self.steps: list[Action] = []

    def add_step(self, action: Callable[..., Any], compensation: Callable[..., Any]) -> 'OrchestrationBuilder':
        self.steps.append(Action(action, compensation))
        return self

    async def execute(self) -> Saga:
        return await Saga(self.steps).execute()
