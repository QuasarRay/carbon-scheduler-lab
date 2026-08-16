Querying Schedule Manager State
================================

:doc:`../pythonApi/scheduleManager` objects manage an internal store of :doc:`../pythonApi/tasklet` objects.

These can be inserted either via :py:func:`scheduler.tasklet.setup` or :py:func:`scheduler.tasklet.insert`.

All :doc:`../pythonApi/scheduleManager` interaction is exposed on the module level. (Refer to :doc:`../pythonApi`)

Ascertaining runnables queue size
---------------------------------

:py:func:`scheduler.getruncount` can be called which to ascertain the current number of :doc:`../pythonApi/tasklet` objects in the runnables queue.

To illustrate refer to the below example.

.. code-block:: python

   t1 = scheduler.tasklet(lambda:None)()

   scheduler.getruncount()

   >>>2

Explanation of computation:

1. ``scheduler.tasklet(lambda:None)()`` creates a :doc:`../pythonApi/tasklet` ``t1`` and the :py:func:`scheduler.tasklet.__call__` will add it to the :doc:`../pythonApi/scheduleManager` runnables queue.
2. ``scheduler.getruncount()`` then returns the value ``2`` which shows there are 2 :doc:`../pythonApi/tasklet` objects. 1 is the main :doc:`../pythonApi/tasklet`, the other being ``t1``.


Python Threads
--------------
Each Python thread will get it's own distinct :doc:`../pythonApi/scheduleManager`.

Therefore, a query call on one thread will return information related to :doc:`../pythonApi/scheduleManager` of that thread. A matching query on another thread could and probably will return different values.

Refer to :doc:`schedulingAcrossMultiplePythonThreads` for further details related to threading.


See Related
-----------

:doc:`schedulingAcrossMultiplePythonThreads`
:doc:`initialisingATasklet`