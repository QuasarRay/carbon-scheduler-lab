Setting Context Managers for Tasklets
=====================================

It's common to have cross-cutting concerns that require some code to always run at the beggining and end of any a Tasklet's bound method. The common way to accomplish this in python would be to wrap a tasklet's callable in another function that executes the start & end code.

.. code-block:: python

    class ContextManager:
        def __enter__(self):
        print("__enter__")

        def __exit__(self, *args):
            print("__exit__")

    def foo(x):
        print(x)

    def wrapper(x):
        with ContextManager():
            return foo(x)

    scheduler.tasklet(wrapper)("middle")
    scheduler.run()

    >>> __enter__
        middle
        __exit__
    >>>

While there is nothing wrong with the way this code is written, wrapping a tasklet's method in another wrapper method causes issues with tasklet tracing.

Scheduler tasklets automatically keep track of their callable's filename :py:attr:`scheduler.tasklet.file_name`, method name :py:attr:`scheduler.tasklet.method_name`, module name :py:attr:`scheduler.tasklet.module_name` & line number :py:attr:`scheduler.tasklet.line_number`. If a callable is wrapped like it is above, these attributes will all point to the wrapper code, not the original callable.

In order to not have to wrap the callable and loose tracing tasklet tracing information, scheduler allows you to pass in a function that returns a context manager that scheduler will use internally to wrap the callable :py:attr:`scheduler.tasklet.context_manager_getter`.

.. code-block:: python

    class ContextManager:

        def __init__(self, t):
            self.tasklet = t

        def __enter__(self):
            print(f"__enter__ {self.tasklet.method_name}")

        def __exit__(self, *args):
            print(f"__exit__ {self.tasklet.method_name}")

    def foo(x):
        print(x)

    t = scheduler.tasklet()
    t.dont_raise = True
    t.bind(foo)
    t.setup("middle")
    t.context_manager_getter = ContextManager

    >>> __enter__ foo
        middle
        __exit__ foo
    >>>

Here, we set :py:attr:`scheduler.tasklet.context_manager_getter` to the typename  `ContextManager`. Scheduler treats that name as a function that takes a tasklet and returns a contetx manger. We could just as easily had passed a function that returns an instance of context manager, but the typename is enough in this example, as calling the type name calls the type's init method and returns an instance.

Important Points
----------------

* :py:attr:`scheduler.tasklet.dont_raise` must be set to `True`, otherwise :py:attr:`scheduler.tasklet.context_manager_getter` will have **no effect**.
* As :py:attr:`scheduler.tasklet.dont_raise` must be `True`, all exceptions raised by the callable will be caught, so the `type`, `value` and `traceback` arguments to the context manager's `__exit__` method, will always be `None`.
* :py:attr:`scheduler.tasklet.context_manager_getter` can be set to None (None by default) and will have no effect.
* :py:attr:`scheduler.tasklet.context_manager_getter` is evaluated when the tasklet is first run, so if a tasklet yieds before `__exit__` is called, and  `context_manager_getter` is set to `None` before the tasklet is re-entered, the original `__exit__` function is already called.
