Sending data between Tasklets using Channels
============================================

Data can be passed from one :doc:`../pythonApi/tasklet` to another using a :doc:`../pythonApi/channel`.

Below illustraits how to send data using :py:func:`scheduler.channel.send` and :py:func:`scheduler.channel.receive`

.. code-block:: python

   def sender(chan, x):
      print("channel sending")
      chan.send(x)
      print("sender finished")

   def receiver(chan):
      print("receiver receiving ...")
      r = chan.receive()
      print("received ", r)


   channel = scheduler.channel()
   _tasklet_A = scheduler.tasklet(receiver)(channel)
   _tasklet_B = scheduler.tasklet(sender)(channel, "Data sent over channel")

   scheduler.run()

   >>>receiver receiving ...
   >>>channel sending
   >>>received Data sent over channel

Explanation of computation:

1. ``_tasklet_A`` calls :py:func:`scheduler.channel.receive` on the :doc:`../pythonApi/channel`
2. This causes ``_tasklet_A`` to yield it's execution, since no :doc:`../pythonApi/tasklet` is waiting to send on that :doc:`../pythonApi/channel`. ``_tasklet_A`` is now 'blocked' on the :doc:`../pythonApi/channel`.
3. ``_tasklet_B`` calls :py:func:`scheduler.channel.send` on the :doc:`../pythonApi/channel`, ``_tasklet_A`` gets 'unblocked' and continues execution, while ``_tasklet_B`` gets inserted into the runnables queue to run later.

.. _channel-blocking-main-tasklet:

'Blocking' The Main Tasklet
---------------------------

Care must be taken to ensure that the Main :doc:`../pythonApi/tasklet` doesn't get 'blocked' indefinitely.

Doing so will raise a ``RuntimeError`` as illustrated below.

.. code-block:: python

   import scheduler

   # we are on the main tasklet
   channel = scheduler.channel()

   # call receive with nothing sending
   channel.receive()

   >>>RuntimeError: Deadlock: the last runnable tasklet cannot be blocked.

The 'blocking' call to :py:func:`scheduler.channel.receive` will first attempt to run the :doc:`../pythonApi/scheduleManager` runnables queue in case their is a :py:func:`scheduler.channel.send`.

Below illustrates expected behaviour when still a matching :py:func:`scheduler.channel.send` is encountered.

.. code-block:: python

   def foo(x):
      print(x)

   import scheduler

   # we are on the main tasklet
   scheduler.tasklet(foo)("1")
   scheduler.tasklet(foo)("2")
   scheduler.tasklet(foo)("3")

   channel = scheduler.channel()
   channel.receive()

   >>>1
   >>>2
   >>>3
   >>>Traceback (most recent call last): . . .
   >>>RuntimeError: Deadlock: the last runnable tasklet cannot be blocked.

Explanation of computation:

1. The three scheduled :doc:`../pythonApi/scheduleManager` s are run.
2. No :py:func:`scheduler.channel.send` is encountered so ``RuntimeError`` is thrown.

Finally, below illustrates a matching :py:func:`scheduler.channel.send` being encountered in a later :doc:`../pythonApi/tasklet` after the :py:func:`scheduler.channel.receive`

.. code-block:: python

   def foo(x):
      print(x)

   def unblock(chan):
      chan.send(1)

   channel = scheduler.channel()

   # we are on the main tasklet
   t1 = scheduler.tasklet(foo)("1")
   t2 = scheduler.tasklet(foo)("2")
   t3 = scheduler.tasklet(unblock)(channel)
   t4 = scheduler.tasklet(foo)("3")

   r = channel.receive()

   print("received ", r)

   >>>1
   >>>2
   >>>received  1

Explanation of computation:

1. This time a matching :py:func:`scheduler.channel.send` was encountered and the send succeeds.
2. It is important to note that ``t4`` has not yet been run as the matching :py:func:`scheduler.channel.send` was reached before this :doc:`../pythonApi/tasklet`.

Suggested Further Reading
-------------------------

:doc:`queryingChannelState`
