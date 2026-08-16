Killing Tasklets
================

It is possible to exit :doc:`../pythonApi/tasklet` execution before it's callable has completed. This is referred to as 'killing' a :doc:`../pythonApi/tasklet`.

:py:func:`scheduler.tasklet.kill` can be used to 'kill' a :doc:`../pythonApi/tasklet`.


Killing a new :doc:`../pythonApi/tasklet`
-----------------------------------------
When a new :doc:`../pythonApi/tasklet` is 'killed', that is, a :doc:`../pythonApi/tasklet` that has been created and added to the :doc:`../pythonApi/scheduleManager` runnables queue.
The :doc:`../pythonApi/tasklet` is removed before running as illustrated below (see :doc:`queryingScheduleManagerState` for further information regarding querying :doc:`../pythonApi/scheduleManager`).

.. code-block:: python

   t = scheduler.tasklet(lambda:None)()

   t.kill()

   scheduler.getruncount()

   >>>1

Explanation of computation:

1. :doc:`../pythonApi/tasklet` ``t`` is created and added to :doc:`../pythonApi/scheduleManager` runnables queue via :py:func:`scheduler.tasklet.__call__`.
2. ``t`` is killed using :py:func:`scheduler.tasklet.kill`
3. :py:func:`scheduler.getruncount` returns ``1`` which is the main :doc:`../pythonApi/tasklet`.


.. _killing-immediately:

Killing a running :doc:`../pythonApi/tasklet` Immediately
---------------------------------------------------------
When a running :doc:`../pythonApi/tasklet` is 'killed' the :doc:`../pythonApi/tasklet` execution is reentered but with a raised :py:func:`scheduler.TaskletExit` exception. (Refer to :doc:`howExceptionsAreManaged` for further details related to exception management)
This allows the user to handle the :py:func:`scheduler.tasklet.kill` possible ramifications.

.. code-block:: python

   c = scheduler.channel()

   def pausingCallable():
      try:
         c.receive()
      except scheduler.TaskletExit:
         print("Killed")

   t = scheduler.tasklet(pausingCallable)()

   t.run()

   t.kill()

   >>>Killed

Explanation of computation:

1. :doc:`../pythonApi/tasklet` ``t`` is created and bound to a callable ``pausingCallable``.
2. :py:func:`scheduler.tasklet.run` is called which starts execution of ``t``.
3. :py:func:`scheduler.channel.receive` call blocks as there is nothing receiving causing ``t`` to yield before completion.
4. :py:func:`scheduler.tasklet.kill` continues ``t`` execution with a raised :py:func:`scheduler.TaskletExit`.
5. ``except scheduler.TaskletExit:`` path is then evaluated which prints ``Killed``.



Killing a running :doc:`../pythonApi/tasklet` non-immediately
-------------------------------------------------------------
:py:func:`scheduler.tasklet.kill` also excepts an option for ``Pending`` which when set ``True`` will perform a non-immediate 'kill' of the :doc:`../pythonApi/tasklet`.
This will raise a :py:func:`scheduler.TaskletExit` on the :doc:`../pythonApi/tasklet` as before, but instead of instantly evaluating the :doc:`../pythonApi/tasklet` it is added to the :doc:`../pythonApi/scheduleManager` runnables queue.


.. code-block:: python

   c = scheduler.channel()

   def pausingCallable():
      try:
         c.receive()
      except scheduler.TaskletExit:
         print("Killed")

   
   t = scheduler.tasklet(pausingCallable)()

   t.run()

   t.kill(pending=True)

   scheduler.run()

   >>>Killed


Explanation of computation:

Very similar to previous example :ref:`killing-immediately` however an extra call to :py:func:`scheduler.run` is required as the :doc:`../pythonApi/tasklet` was added to the :doc:`../pythonApi/scheduleManager` runnables queue rather than executing immediately after :py:func:`scheduler.tasklet.kill`.


Suggested Further Reading
-------------------------

:doc:`howExceptionsAreManaged`