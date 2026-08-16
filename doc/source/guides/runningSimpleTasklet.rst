Running a simple Tasklet
========================

This guide illustrates basic setup and execution of a :doc:`../pythonApi/tasklet`.
For more in depth information related to :doc:`../pythonApi/tasklet` initialisation, refer to :doc:`initialisingATasklet`.


To run a Tasklet it must first be initialised.

This is done by:

1. Binding a Python Callable to it.
2. Providing arguments for the Callable.

Below is a very simple Callable to run.

.. code-block:: python

   def foo(x):
      print(x)

The simplest way to create a fully initialised :doc:`../pythonApi/tasklet` is to provide
both requirements during construction.

.. code-block:: python

   import _scheduler

   # schedule a tasklet to be run
   scheduler.tasklet(foo)("hello")
   scheduler.tasklet(foo)("world")

Here, a Callable is passed to the :doc:`../pythonApi/tasklet` constructor and arguments are provided
via :py:func:`scheduler.tasklet.__call__`

At this point the tasklet has been created and is added to the internal :doc:`../pythonApi/scheduleManager` ready to run.
Refer to :doc:`understandingTaskletScheduleOrder` for further details on scheduling.

The :doc:`../pythonApi/tasklet` will be executed when :py:func:`scheduler.schedule_manager` queue is run.
This can be done with the :py:func:`scheduler.run` command.

.. code-block:: python

   # run all scheduled tasklets
   >>>hello
   >>>world

Suggested Further Reading
-------------------------

:doc:`initialisingATasklet`