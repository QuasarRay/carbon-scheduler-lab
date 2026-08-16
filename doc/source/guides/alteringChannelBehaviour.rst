Altering Channel Behaviour
==========================

:doc:`../pythonApi/channel` operations follow switching behaviour referred to as 'preference', changeable via :py:func:`scheduler.channel.preference`.

There are three 'preference' settings:

1. ``-1``   prefer receiver (default)
2. ``1``    prefer sender
3. ``0``    prefer neither

Channel Preference receiver
---------------------------

Prefer receiver is set via setting :py:func:`scheduler.channel.preference` to ``-1`` and is the default behaviour.

On a :doc:`../pythonApi/channel` operation, Prefer receiver will continue execution on the receiver before sender.

:doc:`../pythonApi/tasklet` order in the runnable queue has no effect on the output as the :doc:`../pythonApi/tasklet` objects are switched to directly.

See example below for a simple scenario.

.. code-block:: python

   c = scheduler.channel()

   c.preference = -1

   def sendingTasklet():
      print("sendingTasklet Started")
      c.send("Value")
      print("sendingTasklet Finished")
   
   def receivingTasklet():
      print("receivingTasklet Started")
      print("receivingTasklet Received {}".format(c.receive()))
      print("receivingTasklet Finished")
   
   t1 = scheduler.tasklet(sendingTasklet)()  
   t2 = scheduler.tasklet(receivingTasklet)()  

   scheduler.run()

   >>>sendingTasklet Started
   >>>receivingTasklet Started
   >>>receivingTasklet Received value
   >>>receivingTasklet Finished
   >>>sendingTasklet Finished

Explanation of computation:

1. On :py:func:`scheduler.run` :doc:`../pythonApi/tasklet`  ``t1`` Is run First. Prints  ``sendingTasklet Started`` and blocks on :py:func:`scheduler.channel.send` at ``c.send("Value")``.
2. ``t2`` Now runs. Prints ``receivingTasklet Started`` and calls :py:func:`scheduler.channel.receive`.
3. As the :py:func:`scheduler.channel.preference` is for the receiver (``-1``) execution continues on the receiver (``t2``) which then prints ``receivingTasklet Received value`` and ``receivingTasklet Finished`` before completing.
4. ``t1`` Continues to execute the remaining instructions after ``c.send("Value")``, which prints ``sendingTasklet Finished`` before completing.

:doc:`../pythonApi/tasklet` order in the runnable queue has little effect on the output due to which :doc:`../pythonApi/tasklet` is run first. Even if creation of ``t1`` and ``t2`` are switched, the final transfer resolution order is the same.

.. code-block:: python

   c = scheduler.channel()

   c.preference = -1

   def sendingTasklet():
      print("sendingTasklet Started")
      c.send("Value")
      print("sendingTasklet Finished")
   
   def receivingTasklet():
      print("receivingTasklet Started")
      print("receivingTasklet Received {}".format(c.receive()))
      print("receivingTasklet Finished")
   
   t2 = scheduler.tasklet(receivingTasklet)()  
   t1 = scheduler.tasklet(sendingTasklet)()  

   scheduler.run()

   >>>receivingTasklet Started
   >>>sendingTasklet Started
   >>>receivingTasklet Received value
   >>>receivingTasklet Finished
   >>>sendingTasklet Finished


Channel Preference sender
--------------------------

Prefer sender is set via setting :py:func:`scheduler.channel.preference` to ``1``.

On a :doc:`../pythonApi/channel` operation, Prefer sender will continue execution on the sender before receiver.

:doc:`../pythonApi/tasklet` order in the runnable queue has only effects which :doc:`../pythonApi/tasklet` is run first, the final transfer resolution order is the same as the :doc:`../pythonApi/tasklet` objects are switched to directly.

See example below for a simple scenario.

.. code-block:: python

   c = scheduler.channel()

   c.preference = 1

   def sendingTasklet():
      print("sendingTasklet Started")
      c.send("Value")
      print("sendingTasklet Finished")
   
   def receivingTasklet():
      print("receivingTasklet Started")
      print("receivingTasklet Received {}".format(c.receive()))
      print("receivingTasklet Finished")
   
   t1 = scheduler.tasklet(sendingTasklet)()
   t2 = scheduler.tasklet(receivingTasklet)()

   scheduler.run()

   >>>sendingTasklet Started
   >>>receivingTasklet Started
   >>>sendingTasklet Finished
   >>>receivingTasklet Received value
   >>>receivingTasklet Finished
   

Explanation of computation:

1. On :py:func:`scheduler.run` :doc:`../pythonApi/tasklet`  ``t1`` Is run First. Prints  ``sendingTasklet Started`` and blocks on :py:func:`scheduler.channel.send` at ``c.send("Value")``.
2. ``t2`` Now runs. Prints ``receivingTasklet Started`` and calls :py:func:`scheduler.channel.receive`.
3. As the :py:func:`scheduler.channel.preference` is for the sender (``1``) execution continues on the sender (``t1``) which then prints ``sendingTasklet Finished`` before completing.
4. ``t2`` Continues to execute the remaining instructions at ``print("receivingTasklet Received {}".format(c.receive()))``, which prints ``receivingTasklet Received value`` and ``receivingTasklet Finished`` before completing.

Just like with prefer receiver, :doc:`../pythonApi/tasklet` order in the runnable queue has little effect on the output due to which :doc:`../pythonApi/tasklet` is run first. Even if creation of ``t1`` and ``t2`` are switched, the final transfer resolution order is the same.

.. code-block:: python

   c = scheduler.channel()

   c.preference = 1

   def sendingTasklet():
      print("sendingTasklet Started")
      c.send("Value")
      print("sendingTasklet Finished")
   
   def receivingTasklet():
      print("receivingTasklet Started")
      print("receivingTasklet Received {}".format(c.receive()))
      print("receivingTasklet Finished")
   
   t2 = scheduler.tasklet(receivingTasklet)()
   t1 = scheduler.tasklet(sendingTasklet)()

   scheduler.run()

   >>>receivingTasklet Started
   >>>sendingTasklet Started
   >>>sendingTasklet Finished
   >>>receivingTasklet Received value
   >>>receivingTasklet Finished



Channel Preference neither
--------------------------

Prefer neither is set via setting :py:func:`scheduler.channel.preference` to ``0``.

On a :doc:`../pythonApi/channel` operation, Prefer neither will continue execution on the current tasklet that called the non-blocking :doc:`../pythonApi/channel` operation (either :py:func:`scheduler.channel.send` or :py:func:`scheduler.channel.receive`).

Unlike prefer receiver and prefer sender :doc:`../pythonApi/tasklet` order in the runnable queue *DOES* have as effect on the output.

.. code-block:: python

   c = scheduler.channel()

   c.preference = 0

   def sendingTasklet():
      print("sendingTasklet Started")
      c.send("Value")
      print("sendingTasklet Finished")
   
   def receivingTasklet():
      print("receivingTasklet Started")
      print("receivingTasklet Received {}".format(c.receive()))
      print("receivingTasklet Finished")
   
   t1 = scheduler.tasklet(sendingTasklet)()
   t2 = scheduler.tasklet(receivingTasklet)()

   scheduler.run()

   >>>sendingTasklet Started
   >>>receivingTasklet Started
   >>>receivingTasklet Received value
   >>>receivingTasklet Finished
   >>>sendingTasklet Finished

Explanation of computation:

1. On :py:func:`scheduler.run` :doc:`../pythonApi/tasklet`  ``t1`` Is run First. Prints  ``sendingTasklet Started`` and blocks on :py:func:`scheduler.channel.send` at ``c.send("Value")``.
2. ``t2`` Now runs. Prints ``receivingTasklet Started`` and calls :py:func:`scheduler.channel.receive`.
3. As the :py:func:`scheduler.channel.preference` is for the receiver (``0``) execution continues on the caller of the non-blocking :doc:`../pythonApi/channel` operation, which here is the receiver (``t2``) that then prints ``receivingTasklet Received value`` and ``receivingTasklet Finished`` before completing.
4. ``t1`` Continues to execute the remaining instructions after ``c.send("Value")``, which prints ``sendingTasklet Finished`` before completing.

Due to the specific :doc:`../pythonApi/tasklet` order in the runnables queue, the behaviour matches expected behaviour from prefer receiver.

However, if the :doc:`../pythonApi/tasklet` order is changed by switching the creation of ``t1`` and ``t2`` the behaviour will instead match prefer sender.

This is because after switching which :doc:`../pythonApi/tasklet` will be executed first. The non-blocking :doc:`../pythonApi/channel` operation call would now be made from the sending :doc:`../pythonApi/tasklet` ``t1`` whereas previously this would have been from the receiving :doc:`../pythonApi/tasklet` ``t2``.

Below illustrates how the :doc:`../pythonApi/tasklet` run order *does* change the expected output.

.. code-block:: python

   c = scheduler.channel()

   c.preference = 0

   def sendingTasklet():
      print("sendingTasklet Started")
      c.send("Value")
      print("sendingTasklet Finished")
   
   def receivingTasklet():
      print("receivingTasklet Started")
      print("receivingTasklet Received {}".format(c.receive()))
      print("receivingTasklet Finished")
   
   t2 = scheduler.tasklet(receivingTasklet)()
   t1 = scheduler.tasklet(sendingTasklet)()

   scheduler.run()

   >>>sendingTasklet Started
   >>>receivingTasklet Started
   >>>sendingTasklet Finished
   >>>receivingTasklet Received value
   >>>receivingTasklet Finished


Suggested Further Reading
-------------------------

:doc:`queryingChannelState`