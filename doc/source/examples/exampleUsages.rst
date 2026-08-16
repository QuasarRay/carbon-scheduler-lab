Example usages
==============
Series of examples which show scheduler functionality

Simple Tasklet
--------------

.. code-block:: python

   # Creating a tasklet and running

   import scheduler

   def exampleCallable(n):
      print("Running example callable {}".format(n))

   t1 = scheduler.tasklet(exampleCallable)(1)

   print("Run Count: {}".format(scheduler.getruncount()))

   scheduler.run()

Output

.. code-block::

   >>>Run Count: 2
   >>>Running example callable 1


Scheduling Tasklets
-------------------

.. code-block:: python

   # The schedule manager holds an internal store of scheduled tasklets
   # New ones are added to the end of a flat list.
   # Running the scheduler runs them in order.

   import scheduler

   def exampleCallable(n):
      print("Running example callable {}".format(n))

   scheduler.tasklet(exampleCallable)(1)
   scheduler.tasklet(exampleCallable)(2)
   scheduler.tasklet(exampleCallable)(3)

   print("Run Count: {}".format(scheduler.getruncount()))

   scheduler.run()

Output

.. code-block::

   >>>Run Count: 4
   >>>Running example callable 1
   >>>Running example callable 2
   >>>Running example callable 3

Callbacks can be installed on tasklet switch
--------------------------------------------

.. code-block:: python

   # Callbacks can be set to be called when tasklets are switched
   import scheduler

   def callback(previousTasklet, nextTasklet):
      print("previousTasklet {} nextTasklet {}".format(previousTasklet,
                                                      nextTasklet))

   def exampleCallable(n):
      print("Running example callable {}".format(n))

   m = scheduler.get_schedule_manager() # So schedule manager stays around
   scheduler.set_schedule_callback(callback)

   main = scheduler.getmain()
   t1 = scheduler.tasklet(exampleCallable)(1)
   t2 = scheduler.tasklet(exampleCallable)(2)
   t3 = scheduler.tasklet(exampleCallable)(3)

   print("MAIN: {}, t1: {}, t2: {}, t3: {}".format(main,t1,t2,t3))

   scheduler.run()

Output

.. code-block::

   >>>MAIN: <scheduler.Tasklet object at 0x0000025171A3CD30>, t1: <scheduler.Tasklet object at 0x0000025171A3DFC0>, t2: <scheduler.Tasklet object at 0x0000025171A3DFF0>, t3: <scheduler.Tasklet object at 0x0000025171A3E260>
   >>>previousTasklet <scheduler.Tasklet object at 0x0000025171A3CD30> nextTasklet <scheduler.Tasklet object at 0x0000025171A3DFC0>
   >>>Running example callable 1
   >>>previousTasklet <scheduler.Tasklet object at 0x0000025171A3DFC0> nextTasklet <scheduler.Tasklet object at 0x0000025171A3CD30>
   >>>previousTasklet <scheduler.Tasklet object at 0x0000025171A3CD30> nextTasklet <scheduler.Tasklet object at 0x0000025171A3DFF0>
   >>>Running example callable 2
   >>>previousTasklet <scheduler.Tasklet object at 0x0000025171A3DFF0> nextTasklet <scheduler.Tasklet object at 0x0000025171A3CD30>
   >>>previousTasklet <scheduler.Tasklet object at 0x0000025171A3CD30> nextTasklet <scheduler.Tasklet object at 0x0000025171A3E260>
   >>>Running example callable 3
   >>>previousTasklet <scheduler.Tasklet object at 0x0000025171A3E260> nextTasklet <scheduler.Tasklet object at 0x0000025171A3CD30>

Running Tasklets Directly
-------------------------

.. code-block:: python

   # Tasklets can also be run directly by calling their run method

   import scheduler

   def exampleCallable(n):
      print("Running example callable {}".format(n))

   t1 = scheduler.tasklet(exampleCallable)(1)

   t1.run()

Output

.. code-block::

   >>>Running example callable 1

.. code-block:: python

   # Tasklets run directly still use the scheduled internal queue
   # The queue is evaluated at the start of the tasklet which called tasklet.run
   # Tasklets queued in a higher position remain on the scheduled queue.
   # Tasklets following the run Tasklet will also be run

   import scheduler

   def exampleCallable(n):
      print("Running example callable {}".format(n))

   t1 = scheduler.tasklet(exampleCallable)(1)
   t2 = scheduler.tasklet(exampleCallable)(2)
   t3 = scheduler.tasklet(exampleCallable)(3)

   t2.run()

   print("Run Count: {}".format(scheduler.getruncount()))

Output

.. code-block::

   >>>Running example callable 2
   >>>Running example callable 3
   >>>Run Count: 2

Creating Tasklets Inside Tasklets
---------------------------------

.. code-block:: python

   # Tasklets can be created inside a running tasklet

   import scheduler

   def exampleCallable(n):
      print("Running example callable {}".format(n))

   def exampleCallableWithNestedTasklet(n):
      print("Running example callable {}".format(n))
      t4 = scheduler.tasklet(exampleCallable)(4)


   t1 = scheduler.tasklet(exampleCallable)(1)
   t2 = scheduler.tasklet(exampleCallableWithNestedTasklet)(2)
   t3 = scheduler.tasklet(exampleCallable)(3)

   scheduler.run()

Output

.. code-block::

   >>>Running example callable 1
   >>>Running example callable 2
   >>>Running example callable 3
   >>>Running example callable 4

Scheduler Run and Tasklet Run With Nested Tasklets
--------------------------------------------------

.. code-block:: python

   # scheduler.run != tasklet.run when nesting tasklets
   # Tasklet.run will only evaluate tasklets that were already created when tasklet.run was called.

   import scheduler

   def exampleCallable(n):
      print("Running example callable {}".format(n))

   def exampleCallableWithNestedTasklet(n):
      print("Running example callable {}".format(n))
      t4 = scheduler.tasklet(exampleCallable)(4)


   t1 = scheduler.tasklet(exampleCallable)(1)
   t2 = scheduler.tasklet(exampleCallableWithNestedTasklet)(2)
   t3 = scheduler.tasklet(exampleCallable)(3)

   t1.run()
   
Output

.. code-block::

   >>>Running example callable 1
   >>>Running example callable 2
   >>>Running example callable 3

Tasklet Switching Of Scheduled Tasklets
-----------------------------------------

.. code-block:: python

   # Tasklets can also be Run by switching to them.
   # Tasklets that are scheduled and switched to will give the same behaviour as Tasklet.run
   # Switch behaviour is different when the Tasklet is not scheduled

   import scheduler

   def exampleCallable(n):
      print("Running example callable {}".format(n))

   def exampleCallableWithNestedTasklet(n):
      print("Running example callable {}".format(n))
      t4 = scheduler.tasklet(exampleCallable)(4)


   t1 = scheduler.tasklet(exampleCallable)(1)
   t2 = scheduler.tasklet(exampleCallableWithNestedTasklet)(2)
   t3 = scheduler.tasklet(exampleCallable)(3)

   t1.switch()

Output

.. code-block::

   >>>Running example callable 1
   >>>Running example callable 2
   >>>Running example callable 3
   >>>Running example callable 4

Running Tasklets With Limit
---------------------------

.. code-block:: python

   # The schedule queue can also be run with PyScheduler_RunWithTimeout
   # PyScheduler_RunWithTimeout is a C-API function which runs tasklets for a set time
   # carbon-scheduler exposes a new function run_n_tasklets which similiarly runs only a portion of the queue at a time.
   # Good for determinism when testing partial queue runs.

   import scheduler

   def exampleCallable(n):
      print("Running example callable {}".format(n))

   scheduler.tasklet(exampleCallable)(1)
   scheduler.tasklet(exampleCallable)(2)
   scheduler.tasklet(exampleCallable)(3)

   while(scheduler.getruncount() > 1):
      scheduler.run_n_tasklets(1)

Output

.. code-block::

   >>>Running example callable 1
   >>>Running example callable 2
   >>>Running example callable 3

Creating Tasklets Outside Schedule manager
------------------------------------------

.. code-block:: python

   # Tasklets can be created and managed completely outside the schedule manager internal queue
   # Switch here will now act differently than when the Tasklet was scheduled
   # In reality it still utilises the scheduler queue but for practical purposes it can be thought of as external

   import scheduler

   def exampleCallable(n):
      print("Running example callable {}".format(n))

   t1 = scheduler.tasklet(exampleCallable)
   t1.bind(exampleCallable, (1,))

   print("Is Tasklet scheduled in internal queue?: {}".format(t1.scheduled))

   t1.switch()

Output

.. code-block::

   >>>Is Tasklet scheduled in internal queue?: False
   >>>Running example callable 1

Tasklet Yielding
-----------------

.. code-block:: python

   # Tasklets can be set to yield at any point
   # scheduler.schedule will yield the current callable and add the Tasklet to the end of the runnables queue

   import scheduler

   def exampleCallable(n):
      print("Start Running example callable {}".format(n))
      scheduler.schedule()
      print("End Running example callable {}".format(n))


   t1 = scheduler.tasklet(exampleCallable)(1)

   t1.run()

Output

.. code-block::

   >>>Start Running example callable 1
   >>>End Running example callable 1

Tasklet Yielding behaviour with Scheduler Run
---------------------------------------------

.. code-block:: python

   # Tasklet yielding with scheduler.run gives very different results here. 

   import scheduler

   def exampleCallable(n):
      print("Start Running example callable {}".format(n))
      scheduler.schedule()
      print("End Running example callable {}".format(n))


   t1 = scheduler.tasklet(exampleCallable)(1)

   scheduler.run()

Output

.. code-block::

   >>>Start Running example callable 1
   >>>End Running example callable 1

How external tasklets can accidently end up on queue
----------------------------------------------------

.. code-block:: python

   # Tasklets that are external to the schedule manager queue can easily get added to the queue accidently

   import scheduler

   def exampleCallable(n):
      print("Start example callable {}".format(n))
      scheduler.schedule()
      print("End example callable {}".format(n))

   t1 = scheduler.tasklet(exampleCallable)
   t1.bind(exampleCallable, (1,))

   print("Is Tasklet on scheduled queue?: {}".format(t1.scheduled))

   t1.switch()

   print("Is Tasklet on scheduled queue?: {}".format(t1.scheduled))

Output

.. code-block::

   >>>Is Tasklet on scheduled queue?: False
   >>>Start example callable 1
   >>>Is Tasklet on scheduled queue?: True

This can be avoided

.. code-block:: python

   # A special schedule exists which doesn't add the Tasklet to the end of the schedule queue

   import scheduler

   def exampleCallable(n):
      print("Start example callable {}".format(n))
      scheduler.schedule_remove()
      print("End example callable {}".format(n))

   t1 = scheduler.tasklet(exampleCallable)
   t1.bind(exampleCallable, (1,))

   print("Is Tasklet on scheduled queue?: {}".format(t1.scheduled))

   t1.switch()

   print("Is Tasklet on scheduled queue?: {}".format(t1.scheduled))

Output

.. code-block::

   >>>Is Tasklet on scheduled queue?: False
   >>>Start example callable 1
   >>>Is Tasklet on scheduled queue?: False

Removing partially complete tasklets from queue
-----------------------------------------------

.. code-block:: python

   # This can also remove Tasklets from the queue in a partially complete state
   # At the end of execution t1 is entirely managed by the user.
   # It can be reinserted or run directly.
   # It is not finished.

   import scheduler

   def exampleCallable(n):
      print("Start example callable {}".format(n))
      scheduler.schedule_remove()
      print("End example callable {}".format(n))

   t1 = scheduler.tasklet(exampleCallable)(1)

   print("Is Tasklet on scheduled queue?: {}".format(t1.scheduled))

   t1.run()

   print("Is Tasklet on scheduled queue?: {}".format(t1.scheduled))

Output

.. code-block::

   >>>Is Tasklet on scheduled queue?: True
   >>>Start example callable 1
   >>>Is Tasklet on scheduled queue?: False

Destroying Tasklets
-------------------

.. code-block:: python

   # Tasklets can be destroyed

   import scheduler

   def exampleCallable(n):
      print("example callable {}".format(n))

   t1 = scheduler.tasklet(exampleCallable)(1)

   print("Run Count: {}".format(scheduler.getruncount()))

   t1.kill()

   print("Run Count: {}".format(scheduler.getruncount()))

Output

.. code-block::

   >>>Run Count: 2
   >>>Run Count: 1

Killing runs schedule manager
-----------------------------

.. code-block:: python

   # Killing a Tasklet does more than just removing them from the queue
   # Tasklets added to run queue that appear after the killed Tasklet will be run

   import scheduler

   def exampleCallable(n):
      print("example callable {}".format(n))

   t1 = scheduler.tasklet(exampleCallable)(1)
   t2 = scheduler.tasklet(exampleCallable)(1)
   t3 = scheduler.tasklet(exampleCallable)(1)

   t1.kill()

   print("Run Count: {}".format(scheduler.getruncount()))

Output

.. code-block::

   >>>example callable 1
   >>>example callable 1
   >>>Run Count: 1

Passing data between tasklets using channels
--------------------------------------------

.. code-block:: python

   # For a channel transfer to complete there first needs to be a matching send/receive pair
   # When the first command is encountered the Tasklet where the command was executed will yield and be added to an internal blocked list on the channel

   import scheduler

   channel = scheduler.channel()

   def send(testChannel):
      testChannel.send(None)

   # Get the tasklet blocked on the channel.
   tasklet = scheduler.tasklet(send)(channel)
   tasklet.run()

   print("Tasklets Blocked on channel: {}".format(channel.balance))

Output

.. code-block::

 >>>Tasklets Blocked on channel: 1

Channel blocking on receive example
-----------------------------------

.. code-block:: python

   # Channels can also block on recieve

   import scheduler

   channel = scheduler.channel()

   def receive(testChannel):
      testChannel.receive()

   # Get the tasklet blocked on the channel.
   tasklet = scheduler.tasklet(receive)(channel)
   tasklet.run()

   print("Tasklets Blocked on channel: {}".format(channel.balance))

Output

.. code-block::

   >>>Tasklets Blocked on channel: -1

Completing channel transfer
---------------------------

.. code-block:: python

   # When a matching pair of send and receives are executed a data transfer will complete

   import scheduler

   def sender(chan, x):
      print("channel sending")
      chan.send(x)
      print("sender finished")

   def receiver(chan):
      print("receiver receiving ...")
      r = chan.receive()
      print("received ", r)


   channel = scheduler.channel()
   scheduler.tasklet(receiver)(channel)
   scheduler.tasklet(sender)(channel, "Data sent over channel")

   scheduler.run()

Output

.. code-block::

   >>>receiver receiving ...
   >>>channel sending
   >>>received  Data sent over channel
   >>>sender finished

Channels can have many blocked tasklets at a time
-------------------------------------------------

.. code-block:: python

   # Channels can have many Tasklets blocked at once

   import scheduler

   channel = scheduler.channel()

   def send(testChannel,x):
      testChannel.send(x)

   # Get the tasklet blocked on the channel.
   for i in range(10):
      scheduler.tasklet(send)(channel,i)
   scheduler.run()

   print("Tasklets Blocked on channel: {}".format(channel.balance))

Output

.. code-block::

   >>>Tasklets Blocked on channel: 10

Channel transfers complete on first blocked
-------------------------------------------

.. code-block:: python

   # Data transfers will be matching simply with the first blocked Tasklet

   import scheduler

   channel = scheduler.channel()

   def send(testChannel,x):
      testChannel.send(x)

   # Get the tasklet blocked on the channel.
   for i in range(10):
      scheduler.tasklet(send)(channel,i)
   scheduler.run()

   print(channel.receive())

Output

.. code-block::

   >>>0

Channels blocking main tasklet can deadlock
--------------------------------------------

.. code-block:: python

   # Blocking the main thread can cause a Deadlock

   import scheduler


   channel = scheduler.channel()
   channel.receive()

Output

.. code-block::

   >>>RuntimeError: Deadlock: the last runnable tasklet cannot be blocked.

Channels blocking main tasklet with scheduled tasklets
-------------------------------------------------------

.. code-block:: python

   # If a future scheduled tasklet exists to complete the channel transfer Deadlock is avoided

   import scheduler


   channel = scheduler.channel()

   def send():
      channel.send("Value from scheduled tasklet")

   scheduler.tasklet(send)()

   print(channel.receive())

Output

.. code-block::

   >>>Value from scheduled tasklet

Channel preference Receive
---------------------------

.. code-block:: python

   # Tasklet Schedule order during a Channel transfer can be altered by altering a the channel's preference tag

   # By default a channel is set to 'prefer receiver'

   import scheduler

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

Output

.. code-block::

   >>>sendingTasklet Started
   >>>receivingTasklet Started
   >>>receivingTasklet Received Value
   >>>receivingTasklet Finished
   >>>sendingTasklet Finished

With switched tasklet order

.. code-block:: python

   # If the tasklet order is switched the same transfer resolution is acheived

   import scheduler

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

Output

.. code-block::

   >>>receivingTasklet Started
   >>>sendingTasklet Started
   >>>receivingTasklet Received Value
   >>>receivingTasklet Finished
   >>>sendingTasklet Finished


Channel preference Send
-----------------------

.. code-block:: python

   # Changing this to 'prefer sender' will have the following effect
   # and again switching t1 and t2 will lead to the same transfer resolution order

   import scheduler

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

Output

.. code-block::

   >>>sendingTasklet Started
   >>>receivingTasklet Started
   >>>sendingTasklet Finished
   >>>receivingTasklet Received Value
   >>>receivingTasklet Finished

With switched tasklet order

.. code-block:: python

   # Changing this to 'prefer sender' will have the following effect
   # and again switching t1 and t2 will lead to the same transfer resolution order

   import scheduler

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

Output

.. code-block::

   >>>receivingTasklet Started
   >>>sendingTasklet Started
   >>>sendingTasklet Finished
   >>>receivingTasklet Received Value
   >>>receivingTasklet Finished

Channel preference Neither
--------------------------

.. code-block:: python

   # Changing this to 'prefer sender' will have the following effect
   # and again switching t1 and t2 will lead to the same transfer resolution order

   import scheduler

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

Output

.. code-block::

   >>>sendingTasklet Started
   >>>receivingTasklet Started
   >>>receivingTasklet Received Value
   >>>receivingTasklet Finished
   >>>sendingTasklet Finished

With switched tasklet order

.. code-block:: python

   # Switching the Tasklet creation order will give different results
   # The channel is now matching resolution order of prefer.sender
   # Hence Prefer neither doesn't prefer any.
   # However it is probably better summed up as prefer either.

   import scheduler

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

Output

.. code-block::

   >>>receivingTasklet Started
   >>>sendingTasklet Started
   >>>sendingTasklet Finished
   >>>receivingTasklet Received Value
   >>>receivingTasklet Finished

Unblocking channels with iterators
----------------------------------

.. code-block:: python

   # Channels offer an iterator to unblock Tasklets blocked on send

   import scheduler

   channel = scheduler.channel()

   def send(testChannel,x):
      testChannel.send(x)

   # Get the tasklet blocked on the channel.
   for i in range(10):
      scheduler.tasklet(send)(channel,i)
   scheduler.run()


   iter = iter(channel)
   while(channel.balance > 0):
      print(next(iter))

Output

.. code-block::

   >>>0
   >>>1
   >>>2
   >>>3
   >>>4
   >>>5
   >>>6
   >>>7
   >>>8
   >>>9

Closing channels
----------------

.. code-block:: python

   # Channels can be 'closed'

   import scheduler

   channel = scheduler.channel()

   def send(testChannel,x):
      testChannel.send(x)

   t1 = scheduler.tasklet(send)(channel,1)

   t1.run()

   channel.close()

   t2 = scheduler.tasklet(send)(channel,1)

   t2.run()

Output

.. code-block::

   >>>ValueError: Send/receive operation on a closed channel

Channels only fully close when block list is empty

.. code-block:: python

   # Channels are only marked as fully closed when they contain no more blocked tasklets
   # which follows that, closed channels can still complete transfer operations
   # Watch out for closing as it may not be obvious

   import scheduler

   channel = scheduler.channel()

   def send(testChannel,x):
      testChannel.send(x)

   # Get the tasklet blocked on the channel.
   t1 = scheduler.tasklet(send)(channel,1)

   t1.run()

   channel.close()

   print("Is Channel closed?: {}".format(channel.closed))

   print("Is Channel closing?: {}".format(channel.closing))

   print("Received {}" .format(channel.receive()))

   print("Is Channel closed?: {}".format(channel.closed))

   print("Is Channel closing? Really... ¯_ (ツ)_/¯ : {}".format(channel.closing))

Output

.. code-block::

   >>>Is Channel closed?: False
   >>>Is Channel closing?: True
   >>>Received 1
   >>>Is Channel closed?: True
   >>>Is Channel closing? Really... ¯_ (ツ)_/¯ : True

Channels can call callbacks called on operation
-----------------------------------------------

.. code-block:: python

   # Channel callbacks can be installed
   # Channel callbacks are global to the scheduler and so shared by all channels


   import scheduler

   def callback(channel, tasklet, is_sending, will_block):
      print("Channel {} Tasklet {} is_sending {} will_block {}".format(channel,
                                                                     tasklet,
                                                                     is_sending,
                                                                     will_block))


   def sender(chan, x):
      print("channel sending")
      chan.send(x)
      print("sender finished")

   def receiver(chan):
      print("receiver receiving ...")
      r = chan.receive()
      print("received ", r)

   scheduler.set_channel_callback(callback)

   channel = scheduler.channel()
   t1 = scheduler.tasklet(receiver)(channel)
   t2 = scheduler.tasklet(sender)(channel, "Data sent over channel")

   print("Channel {} t1 {} t2 {}".format(channel,t1,t2))

   scheduler.run()

Output

.. code-block::

   >>>Channel <scheduler.Channel object at 0x000002455CC6AB90> t1 <scheduler.Tasklet object at 0x000002455CC9E200> t2 <scheduler.Tasklet object at 0x000002455CC9E230>
   >>>receiver receiving ...
   >>>Channel <scheduler.Channel object at 0x000002455CC6AB90> Tasklet <scheduler.Tasklet object at 0x000002455CC9E200> is_sending False will_block True
   >>>channel sending
   >>>Channel <scheduler.Channel object at 0x000002455CC6AB90> Tasklet <scheduler.Tasklet object at 0x000002455CC9E230> is_sending True will_block False
   >>>received  Data sent over channel
   >>>sender finished

Raising exceptions on tasklets
------------------------------

.. code-block:: python

   # Exceptions can be raised on Tasklets

   import scheduler

   def yieldingTasklet():
      scheduler.schedule()

   t = scheduler.tasklet(yieldingTasklet)()

   t.run()

   t.raise_exception(RuntimeError)

Output

.. code-block::

   >>>RuntimeError

Raising TaskletExit exceptions
------------------------------

.. code-block:: python

   # A special exception is provided scheduler.TaskletExit
   # scheduler.TaskletExit exceptions will be contained in the Tasklet

   import scheduler

   def yieldingTasklet():
      scheduler.schedule()

   t = scheduler.tasklet(yieldingTasklet)()

   t.run()

   t.raise_exception(scheduler.TaskletExit)

Output

.. code-block::

   >>>

Catching TaskletExit exceptions
-------------------------------

.. code-block:: python

   # scheduler.TaskletExit can be caught to deal with cleanup inside the Tasklet

   import scheduler

   def yieldingTasklet():
      try:
         scheduler.schedule()
      except scheduler.TaskletExit:
         print("Caught the scheduler.TaskletExit error")

   t = scheduler.tasklet(yieldingTasklet)()

   t.run()

   t.raise_exception(scheduler.TaskletExit)

Output

.. code-block::

   >>>Caught the scheduler.TaskletExit error

Raising TaskletExit on a new tasklet
------------------------------------

.. code-block:: python

   # Tasklet exit on a new Tasklet will cause it never to even start

   import scheduler

   def yieldingTasklet():
      try:
         scheduler.schedule()
      except scheduler.TaskletExit:
         print("Causght the scheduler.TaskletExit error")

   t = scheduler.tasklet(yieldingTasklet)()

   t.raise_exception(scheduler.TaskletExit)

   t.run()

Output

.. code-block::

   >>>Cannot run tasklet that is not alive (dead)

Sending exceptions over channels
--------------------------------

.. code-block:: python

   # Exceptions can be sent over channels

   import scheduler

   channel = scheduler.channel()

   def send(testChannel):
      testChannel.receive()

   # Get the tasklet blocked on the channel.
   t = scheduler.tasklet(send)(channel)
   t.run()

   channel.send_exception(RuntimeError)

Output

.. code-block::

   >>>RuntimeError

Running tasklets are still marked as scheduled
----------------------------------------------

.. code-block:: python

   # Running Tasklets are marked as 'scheduled'

   import scheduler

   def exampleCallable(n):
      print("Running example callable {}".format(n))
      print("Is current scheduled? {}".format(scheduler.getcurrent().scheduled))

   t1 = scheduler.tasklet(exampleCallable)(1)

   scheduler.run()

Output

.. code-block::

   >>>Running example callable 1
   >>>Is current scheduled? True

Complex tasklet order example
-----------------------------

.. code-block:: python

   # Schedule order can get complex to follow
   # Even though the scheduler run queue is a flat list it is often not evaluated in a linear way.

   import scheduler

   def taskletCallable(x):
      print("t{}".format(x))

   def schedule(x):
      scheduler.schedule()
      taskletCallable(x)

   def createNestedTaskletRun2():
      t8 = scheduler.tasklet(taskletCallable)(3)
      t9 = scheduler.tasklet(schedule)(8)
      t10 = scheduler.tasklet(taskletCallable)(4)
      t8.run()

   def createNestedTaskletRun():
      t4 = scheduler.tasklet(taskletCallable)(2)
      t5 = scheduler.tasklet(schedule)(7)
      t6 = scheduler.tasklet(createNestedTaskletRun2)()
      t7 = scheduler.tasklet(taskletCallable)(5)
      t4.run()

   t1 = scheduler.tasklet(taskletCallable)(1)
   t2 = scheduler.tasklet(createNestedTaskletRun)()
   t3 = scheduler.tasklet(taskletCallable)(6)

   scheduler.run()

Output

.. code-block::

   >>>t1
   >>>t2
   >>>t3
   >>>t4
   >>>t5
   >>>t6
   >>>t7
   >>>t8

Runs with limit retain tasklet nesting
--------------------------------------

.. code-block:: python

   # Runs with limits will retain Nesting order of execution to retain Tasklet order during runs

   import scheduler

   def taskletCallable(x):
      print("t{}".format(x))

   def schedule():
      scheduler.schedule()

   def createNestedTaskletRun2():
      t2 = scheduler.tasklet(taskletCallable)(3)
      scheduler.tasklet(schedule)()
      scheduler.tasklet(taskletCallable)(4)
      t2.run()

   def createNestedTaskletRun():
      t2 = scheduler.tasklet(taskletCallable)(2)
      scheduler.tasklet(schedule)()
      scheduler.tasklet(createNestedTaskletRun2)()
      scheduler.tasklet(taskletCallable)(5)
      t2.run()

   scheduler.tasklet(taskletCallable)(1)
   scheduler.tasklet(createNestedTaskletRun)()
   scheduler.tasklet(taskletCallable)(6)

   while scheduler.getruncount() > 1:
      scheduler.run_n_tasklets(1)

Output

.. code-block::

   >>>t1
   >>>t2
   >>>t3
   >>>t4
   >>>t5
   >>>t6

Python threads and schedule manager
-----------------------------------

.. code-block:: python

   # Threads
   # Scheduler works with threading
   # The way it works is that each Python thread gets its own schedule manager
   # These are set up for you as needed and destroyed when no longer required.

   import scheduler
   import threading

   def log(argument):
      t = scheduler.getcurrent()
      print("log: {} from thread_id: {}".format(argument, t.thread_id))

   def createTasklets():
      for i in range(2):
         scheduler.tasklet(log)(i)
      scheduler.run()

   thread = threading.Thread(target=createTasklets, args=())

   thread.start()

   createTasklets()

Output

.. code-block::

   >>>log: 0 from thread_id: 33956
   >>>log: 0 from thread_id: 28260
   >>>log: 1 from thread_id: 33956
   >>>log: 1 from thread_id: 28260

Channels are threadsafe
-----------------------

.. code-block:: python

   # Channels are thread safe, data can be transferred between Python threads.

   import scheduler
   import threading

   channel = scheduler.channel()

   def receiver(chan):
      r = chan.receive()
      print("received '{}' from different thread".format(r))

   def otherThreadMainTasklet(chan):
      t = scheduler.tasklet(receiver)(chan)
      while(t.alive):
         scheduler.run()

   recever_thread = threading.Thread(target=otherThreadMainTasklet, args=(channel,))
   recever_thread.start()

   channel.send("Hello from another thread!")

Output

.. code-block::

   >>>received 'Hello from another thread!' from different thread

Supressing tasklet switching
----------------------------

.. code-block:: python

   # Tasklets can be set to be non blocking using their block_trap property

   import scheduler

   def receiver(chan):
      print("about to call receive ...")
      chan.receive()

   channel = scheduler.channel()

   unblockableTasklet = scheduler.tasklet(receiver)(channel)

   unblockableTasklet.block_trap = True

   scheduler.run()

Output

.. code-block::

   >>>RuntimeError: Channel cannot block on main tasklet with block_trap set true

Blocktrap does not stop transers Completing
-------------------------------------------

.. code-block:: python

   # Blocktrap will not stop switching for a completing transfer

   import scheduler

   def sender(chan, x):
      print("channel sending")
      chan.send(x)
      print("sender finished")

   def receiver(chan):
      print("receiver receiving ...")
      r = chan.receive()
      print("received ", r)


   channel = scheduler.channel()
   t1 = scheduler.tasklet(receiver)(channel)

   t1.run()

   t2 = scheduler.tasklet(sender)(channel, "Data sent over channel")

   t2.block_trap = True

   t2.run()

Output

.. code-block::

   >>>receiver receiving ...
   >>>channel sending
   >>>received  Data sent over channel
