Querying Channel State
======================

:doc:`../pythonApi/channel` objects can send and receive data.

For a successful data transfer they us required to be a set of matching :py:func:`scheduler.channel.receive` and :py:func:`scheduler.channel.send` commands.

If only half of the pair is present then the :doc:`../pythonApi/tasklet` performing the operation is added to a 'blocked' list internal to the :doc:`../pythonApi/channel`.

The :py:func:`scheduler.channel.balance` of a :doc:`../pythonApi/channel` can be queried to ascertain the 'blocked' list state.

A positive :py:func:`scheduler.channel.balance` of ``n`` indicates there are ``n`` :doc:`../pythonApi/tasklet` 'blocked' on a send operation.

A negative :py:func:`scheduler.channel.balance` of ``-n`` indicates there are ``n`` :doc:`../pythonApi/tasklet` 'blocked' on a receive operation.


Below illustrates a 'blocking' on :py:func:`scheduler.channel.send`

.. code-block:: python

   def sender(chan, x):
      chan.send(x)

   channel = scheduler.channel()

   for i in range(10):
      scheduler.tasklet(sender)(channel, i)

   print(channel.balance)

   >>>10

To further illustrate the point below another :py:func:`scheduler.channel.receive` can be called showing the :py:func:`scheduler.channel.balance` is affected.

.. code-block:: python

   channel.receive()

   print(channel.balance)

   >>>9


To complete the example below illustrates a 'blocking' on :py:func:`scheduler.channel.receive`


.. code-block:: python

   def receiver(chan):
      chan.receive()

   channel = scheduler.channel()

   for i in range(10):
      scheduler.tasklet(receiver)(channel)

   print(channel.balance)

   >>>-10


.. code-block:: python

   channel.send()

   print(channel.balance)

   >>>-9

See Related
-----------

:doc:`alteringChannelBehaviour`