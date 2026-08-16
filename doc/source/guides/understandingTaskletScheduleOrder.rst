Understanding Tasklet Schedule Order
====================================

A :doc:`../pythonApi/scheduleManager` contains a flat queue which is referred to as the runnables queue.

However, there are considerations to keep in mind to fully understand :doc:`../pythonApi/tasklet` execution order.


Simple Situation
----------------
Sequentially adding :doc:`../pythonApi/tasklet` objects to the runnables queue.

When a :doc:`../pythonApi/tasklet` is added to the runnables queue, it is appended to the back.

When :py:func:`scheduler.run` is called the runnables queue is interated and each :doc:`../pythonApi/tasklet` is run until none remain.

.. code-block:: python

   def log(s):
      print(s)

   scheduler.tasklet(log)("first")

   scheduler.tasklet(log)("second")

   scheduler.tasklet(log)("third")

At this point the internal run queue will have 3 :doc:`../pythonApi/tasklet` objects queued. This can be seen by querying :py:func:`scheduler.getruncount`

.. code-block:: python

   scheduler.getruncount()

   >>>4

The ``4`` represents the 3 queued :doc:`../pythonApi/tasklet` objects plus the main tasklet. See :doc:`theMainTasklet` for more information.

The runnable queue can be evaluated with a call to :py:func:`scheduler.run`.

.. code-block:: python

   scheduler.run()

   >>>first
   >>>second
   >>>third


Running via :py:func:`scheduler.tasklet.run`
--------------------------------------------

Instead of running the runnables queue via :py:func:`scheduler.run`, it is also possible to run via :py:func:`scheduler.tasklet.run`.

Both approaches evaluate the same runnables queue, however :py:func:`scheduler.tasklet.run` will start running at the :doc:`../pythonApi/tasklet` that :py:func:`scheduler.tasklet.run` was called.

All :doc:`../pythonApi/tasklet` objects following the calling :doc:`../pythonApi/tasklet` will also be run.

All :doc:`../pythonApi/tasklet` objects preceding the calling :doc:`../pythonApi/tasklet` will remain on the runnables queue.

.. code-block:: python

   def log(s):
      print(s)

   t1 = scheduler.tasklet(log)("first")

   t2 = scheduler.tasklet(log)("second")

   t3 = scheduler.tasklet(log)("third")

   t2.run()

   >>>second
   >>>third

.. _run-order-nesting:

Run order when nesting :doc:`../pythonApi/tasklet` objects
----------------------------------------------------------

A :doc:`../pythonApi/tasklet` can create :doc:`../pythonApi/tasklet` objects. These :doc:`../pythonApi/tasklet` objects will be added to the runnables queue and evaluated as part of a :py:func:`scheduler.tasklet.run`.

.. code-block:: python

   def log(s):
      print(s)

   def bar():
      print("fourth")
      t5 = scheduler.tasklet(log)("fifth")

   def foo():
      print("second")
      t4 = scheduler.tasklet(bar)()

   t1 = scheduler.tasklet(log)("first")

   t2 = scheduler.tasklet(foo)()

   t3 = scheduler.tasklet(log)("third")

   scheduler.run()

   >>>first
   >>>second
   >>>third
   >>>fourth
   >>>fifth

Explanation of computation:

1. First :doc:`../pythonApi/tasklet` objects ``t1``, ``t2`` and ``t3`` are initilised and added to the runnables queue in order of their creation.
2. The runnables queue is iterated with the call to :py:func:`scheduler.tasklet.run`.
3. ``t1`` is run, prints ``first``.
4. ``t2`` is run, prints ``second`` and creates a new :doc:`../pythonApi/tasklet` (`t4`) which is added to the back of the runnables queue.
5. ``t3`` is run, prints ``third``
6. ``t4`` is run, prints ``fourth`` and creates a new :doc:`../pythonApi/tasklet` (`t5`) which is added to the back of the runnables queue.
7. ``t5`` is run, prints ``fifth``


Run order when nesting :py:func:`scheduler.run` vs :py:func:`scheduler.tasklet.run`
-----------------------------------------------------------------------------------

Run order behaviour differs when run using :py:func:`scheduler.tasklet.run`.

Whereas :py:func:`scheduler.run` runs all :doc:`../pythonApi/tasklet` objects created inside each :doc:`../pythonApi/tasklet`, :py:func:`scheduler.tasklet.run` doesn't and instead leaves them on the runnables queue.

To illustrate, the code below shows the same example as :ref:`run-order-nesting` but running using :py:func:`scheduler.tasklet.run` instead of :py:func:`scheduler.run`

.. code-block:: python

   def log(s):
      print(s)

   def bar():
      print("fourth")
      t5 = scheduler.tasklet(log)("fifth")

   def foo():
      print("second")
      t4 = scheduler.tasklet(bar)()

   t1 = scheduler.tasklet(log)("first")

   t2 = scheduler.tasklet(foo)()

   t3 = scheduler.tasklet(log)("third")

   t1.run()

   >>>first
   >>>second
   >>>third

Explanation of computation:

1. First :doc:`../pythonApi/tasklet` objects ``t1``, ``t2`` and ``t3`` are initilised and added to the runnables queue in order of their creation.
2. The runnables queue is iterated with the call to :py:func:`scheduler.tasklet.run`.
3. ``t1`` is run, prints ``first``.
4. ``t2`` is run, prints ``second`` and creates a new :doc:`../pythonApi/tasklet` (``t4``) which is added to the back of the runnables queue.
5. ``t3`` is run, prints ``third``

The :doc:`../pythonApi/tasklet` object created inside the called :doc:`../pythonApi/tasklet` objects are not run and remain on the runnables queue.

.. code-block:: python

   scheduler.run()

   >>>fourth
   >>>fifth

Another more subtle example difference between using :py:func:`scheduler.run` and :py:func:`scheduler.tasklet.run` is shown below.

When using :py:func:`scheduler.run`
.. code-block:: python

   def yieldingTasklet():
      scheduler.schedule()
      print("Finished")

   t = scheduler.tasklet(yieldingTasklet)()

   scheduler.run()

   >>>Finished

When using :py:func:`scheduler.tasklet.run`
.. code-block:: python

   def yieldingTasklet():
      scheduler.schedule()
      print("Finished")

   t = scheduler.tasklet(yieldingTasklet)()

   t.run()

Explanation of computation:

The first example using :py:func:`scheduler.run` does yield but continues right away after as it was added back to the runnables queue, hence ``Finished`` is printed.

The second example using :py:func:`scheduler.tasklet.run` yields and inserts the ``t`` back onto the runnables queue, as :py:func:`scheduler.tasklet.run` won't run a :doc:`../pythonApi/tasklet` added during execution, iteration of the runnables queue finishes before it is reached resulting in ``Finished`` not outputted. A subsequent call to :py:func:`scheduler.tasklet.run` will produces the output.

Suggested Further Reading
-------------------------

:doc:`manualControlScheduling`

:doc:`restrictingTaskletControlFlow`