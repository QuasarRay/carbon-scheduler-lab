Initialising a Tasklet
======================

This guide illustrates all the variations that a :doc:`../pythonApi/tasklet` can be initialised ready for use.

For a more basic quick start, refer to :doc:`runningSimpleTasklet`



Before a :doc:`../pythonApi/tasklet` can be used it must first be initialised.

This is done by:

1. Binding a Python Callable to it.
2. Providing arguments for the Callable.

There a multiple ways to achieve this initialised state.


Initilising using Constructor and :py:func:`scheduler.tasklet.__call__`
-----------------------------------------------------------------------

This is the simplest method for initilising a :doc:`../pythonApi/tasklet`

The Callable is provided to the :doc:`../pythonApi/tasklet` constructor and the arguments are passed via :py:func:`scheduler.tasklet.__call__`

This method is covered in more detail in the :doc:`runningSimpleTasklet` section.

.. code-block:: python
   
   def foo(s):
      print(s)

   t = scheduler.tasklet(foo)("Example Argument Printed From Tasklet")

   scheduler.run()

   >>>"Example Argument Printed From Tasklet"

Manually initilising using :py:func:`scheduler.tasklet.bind` and :py:func:`scheduler.tasklet.setup`
---------------------------------------------------------------------------------------------------

A :doc:`../pythonApi/tasklet` can be created without passing any arguments.

.. code-block:: python

   t = scheduler.tasklet()
   
Once created, the :doc:`../pythonApi/tasklet` will be in an uninitilised state. This can be queried by inspecting the :py:func:`scheduler.tasklet.alive` attribute.

.. code-block:: python
   
   print(t.alive)

   >>>False

Python Callables can be provided to the :doc:`../pythonApi/tasklet` via the :py:func:`scheduler.tasklet.bind` method.

.. code-block:: python

   def foo(s):
      print(s)

   t.bind(foo)

Arguments can then be provided to the :doc:`../pythonApi/tasklet` via the :py:func:`scheduler.tasklet.setup` method.

.. code-block:: python

   t.setup("Example Argument Printed From Tasklet")

At this stage the :doc:`../pythonApi/tasklet` is initilised.

.. code-block:: python
   
   print(t.alive)

   >>>True

The :py:func:`scheduler.tasklet.setup` also inserts the :doc:`../pythonApi/tasklet` in the :py:func:`scheduler.schedule_manager` runnables queue.
This can be see by querying :py:func:`scheduler.tasklet.scheduled`

.. code-block:: python
   
   print(t.scheduled)

   >>>True

The :doc:`../pythonApi/tasklet` can be run by calling :py:func:`scheduler.run`

.. code-block:: python
   
   scheduler.run()

   >>>Example Argument Printed From Tasklet


Manually initilising using only :py:func:`scheduler.tasklet.bind` and :py:func:`scheduler.tasklet.insert`
---------------------------------------------------------------------------------------------------------

:py:func:`scheduler.tasklet.bind` accepts some variation. This section illustraits how a :doc:`../pythonApi/tasklet` can be initialised and
added to the runables queue without :py:func:`scheduler.tasklet.setup`

In addition to the Python Callable, :py:func:`scheduler.tasklet.bind` can also be passed the arguments.

.. code-block:: python

   def foo(s):
      print(s)

   t = scheduler.tasklet()

   t.bind(foo, ("Example Argument Printed From Tasklet", ))

At this point the :doc:`../pythonApi/tasklet` is initilised, indicated by the :py:func:`scheduler.tasklet.alive` status

.. code-block:: python
   
   print(t.alive)

   >>>True

However, unlike when the arguments are passed via :py:func:`scheduler.tasklet.setup`, the :doc:`../pythonApi/tasklet` has not been inserted into the runnables queue.

.. code-block:: python
   
   print(t.scheduled)

   >>>False

An alive :doc:`../pythonApi/tasklet` can be inserted into the runnables queue manually by calling :py:func:`scheduler.tasklet.insert`

.. code-block:: python
   
   t.insert()

   print(t.scheduled)

   >>>False

For further information regarding manual insertion of Tasklets, see :doc:`manualControlScheduling`.


Uninitising a :doc:`../pythonApi/tasklet`
-----------------------------------------

An unscheduled :doc:`../pythonApi/tasklet` can also be uninitilised via :py:func:`scheduler.tasklet.bind` by passing `None` as the Callable.

.. code-block:: python

   t.bind(None)

If the :doc:`../pythonApi/tasklet` is already present in the runnables queue, this call will result in a `RuntimeError`.
A :doc:`../pythonApi/tasklet` can be removed from the runnables queue via :py:func:`scheduler.tasklet.remove`


Suggested Further Reading
-------------------------

:doc:`understandingTaskletScheduleOrder`