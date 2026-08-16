Restricting Tasklet Control Flow
================================

There are two ways that :doc:`../pythonApi/tasklet` switching can be restricted.

1. :py:func:`scheduler.switch_trap`
2. :py:func:`scheduler.tasklet.block_trap`

Restricting via :py:func:`scheduler.switch_trap`
------------------------------------------------

:doc:`../pythonApi/tasklet` switching can be prevented on the :doc:`../pythonApi/scheduleManager` level by setting :py:func:`scheduler.switch_trap` to a non-zero value.

This will prevent any switching from taking place. Any attempt will raise a `RuntimeError`.

.. code-block:: python

   def foo():
      print("Won't be called")

   scheduler.tasklet(foo)()

   scheduler.switch_trap(1)

   scheduler.run()

   >>>Traceback (most recent call last):
   >>>File "<stdin>", line 1, in <module>
   >>>RuntimeError: Cannot schedule when scheduler switch_trap level is non-zero


Restricting via :py:func:`scheduler.tasklet.block_trap`
-------------------------------------------------------

A :doc:`../pythonApi/tasklet` can be set to prevent a :doc:`../pythonApi/channel` from yielding execution to another :doc:`../pythonApi/tasklet` by setting :py:func:`scheduler.tasklet.block_trap` to `True` .

An attempt to do this will raise a `RuntimeError`.

.. code-block:: python

   def receiver(chan):
      print("about to call receive ...")
      chan.receive()


   channel = scheduler.channel()

   unblockableTasklet = scheduler.tasklet(receiver)(channel)

   unblockableTasklet.block_trap = True

   scheduler.run()

   >>>about to call receive ...
   >>>Traceback (most recent call last): ...
   >>>RuntimeError: Channel cannot block on a tasklet with block_trap set true


Suggested Further Reading
-------------------------

:doc:`sendingDataBetweenTaskletsUsingChannels`