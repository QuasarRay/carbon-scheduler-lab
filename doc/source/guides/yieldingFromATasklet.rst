Yielding from a Tasklet
=======================

A :doc:`../pythonApi/tasklet` can be yielded from at any time using :py:func:`scheduler.schedule`.

Below illustrates how to pause execution of a running tasklet and insert it at the back of the runnables queue.

.. code-block:: python
   
   def foo():
      print("Start")
      scheduler.schedule()
      print("End")

   t = scheduler.tasklet(foo)()

   scheduler.run()

   >>>Start

Explanation of computation:

1. A :doc:`../pythonApi/tasklet` object is created, initilised and added to the runnables queue.
2. :py:func:`scheduler.run` causes the :doc:`../pythonApi/tasklet` to run, it prints `Start` and calls :py:func:`scheduler.schedule` which yields.

At this point the :doc:`../pythonApi/tasklet` is in an incomplete state, which can be seen by querying the :py:func:`scheduler.tasklet.alive` attribute.

.. code-block:: python
   
   print(t.alive)

   >>>True

The :doc:`../pythonApi/tasklet` will also have been reinserted into the runnables queue, which can be seen by querying :py:func:`scheduler.getruncount`.

.. code-block:: python
   
   scheduler.getruncount()

   >>>2

``2`` refers to the :doc:`../pythonApi/tasklet` that was inserted as part of :py:func:`scheduler.schedule` and the Main tasklet. Refer to :doc:`theMainTasklet` for further information related to the main :doc:`../pythonApi/tasklet`.




Yielding and removing from runnables queue.
-------------------------------------------

It is possible to yield control of a :doc:`../pythonApi/tasklet` without reinserting back into the :doc:`../pythonApi/scheduleManager` runnables queue by using :py:func:`scheduler.schedule_remove`.

This will remove the :doc:`../pythonApi/tasklet` in an unfinished state which must then be handled by the user.

.. code-block:: python
   
   def foo():
      print("Start")
      scheduler.schedule_remove()
      print("End")

   t = scheduler.tasklet(foo)()

   scheduler.run()

   >>>Start

The :doc:`../pythonApi/tasklet` will not have been reinserted into the runnables queue, which can be seen by querying :py:func:`scheduler.getruncount`.

.. code-block:: python
   
   scheduler.getruncount()

   >>>1

In order to continue execution of the :doc:`../pythonApi/tasklet` it must either be:

1. Reinserted back into the runnables queue via :py:func:`scheduler.tasklet.insert`.
2. Run directly using :py:func:`scheduler.tasklet.run`.
3. Switched to directly using :py:func:`scheduler.tasklet.switch`.

See :ref:`schedule-remove-guide` for another example usage of :py:func:`scheduler.schedule_remove`


Suggested Further Reading
-------------------------

:doc:`manualControlScheduling`