How to manually control scheduling
==================================

Sometimes it can be useful to have more control over the scheduling.

:py:func:`scheduler.tasklet.switch` can be used to switch directly to another :doc:`../pythonApi/tasklet` rather than running through the :doc:`../pythonApi/scheduleManager` runnables logic.

Circumventing the default :doc:`../pythonApi/scheduleManager` run queue order
-----------------------------------------------------------------------------

Below illustrates running tasklets manually, completely circumventing the schedule logic in :doc:`../pythonApi/scheduleManager`.

.. code-block:: python

   def log(s):
      print(s)

   t1 = scheduler.tasklet()
   t2 = scheduler.tasklet()
   t3 = scheduler.tasklet()

   t1.bind(foo,("First",))
   t2.bind(foo,("Second",))
   t3.bind(foo,("Third",))

   manualScheduler = list()

   manualScheduler.append(t1)
   manualScheduler.append(t2)
   manualScheduler.append(t3)

   for t in manualScheduler:
      t.switch()

   >>>First
   >>>Second
   >>>Third

Execution explanation:
1. Three :doc:`../pythonApi/tasklet` objects are created and initilised but not inserted into the runnables queue.
2. The tasklets are added to a Python List collection in the order they will be executed.
3. The list is iterated calling :py:func:`scheduler.tasklet.switch` which causes the :doc:`../pythonApi/tasklet` in question to be evaluated immediately.


Mixing :py:func:`scheduler.tasklet.switch` with default :doc:`../pythonApi/scheduleManager` run queue
-----------------------------------------------------------------------------------------------------

Below illustrates what to expect when mixing the two scheduling approaches.

.. code-block:: python

   def log(s):
      print(s)

   t1 = scheduler.tasklet(log)("First")
   t2 = scheduler.tasklet(log)("Second").switch()

   >>>Second
   >>>First

Execution explanation:

1. Two :doc:`../pythonApi/tasklet` objects are created `t1` and `t2`.
2. :py:func:`scheduler.tasklet.switch` is called causing `t2` to start which prints `second`.
3. The remaining tasklet queue is evaluated running `t1` which prints `first`.


.. _schedule-remove-guide:

Yielding from a Tasklet circumventing the Schedule Manager's run queue
----------------------------------------------------------------------

The standard way of yielding from a :doc:`../pythonApi/tasklet` is to call :py:func:`scheduler.schedule` from inside the running :doc:`../pythonApi/tasklet`.

However, :py:func:`scheduler.schedule` will also insert the :doc:`../pythonApi/tasklet` into the :doc:`../pythonApi/scheduleManager` run queue which may be undesirable if circumventing standard run queue.

The solution illustrated below is to use :py:func:`scheduler.schedule_remove` which will not re-insert the :doc:`../pythonApi/tasklet`.

.. code-block:: python

   def foo(x):
      print(x)
      scheduler.schedule_remove()
      print(x)

   t1 = scheduler.tasklet()

   t1.bind(foo,("Example Argument",))

   t1.switch()

   >>>Example Argument

   t1.switch()

   >>>Example Argument

Execution explanation:

1. A :doc:`../pythonApi/tasklet` object is created and not added to the :doc:`../pythonApi/scheduleManager` runnables queue.
2. :py:func:`scheduler.tasklet.switch` causes the :doc:`../pythonApi/tasklet` to be evaulated immediately.
3. :py:func:`scheduler.schedule_remove` yields execution of :doc:`../pythonApi/tasklet` and doesn't insert it into the runnables queue.
4. A second call to :py:func:`scheduler.tasklet.switch` finishes the execution of the :doc:`../pythonApi/tasklet`.

Suggested Further Reading
-------------------------

:doc:`restrictingTaskletControlFlow`

