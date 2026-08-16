Scheduling Across multiple Python Threads
=========================================

carbon-scheduler support Python Threads.

Each Python Thread gets assigned its own :doc:`../pythonApi/scheduleManager` on demand.

The following rules apply:

1. :doc:`../pythonApi/tasklet` are locked to the thread they were created on and **cannot** be moved between threads.

2. :doc:`../pythonApi/tasklet` also cannot **cannot** switch to :doc:`../pythonApi/tasklet` objects created on another thread and expect them to run on the same thread.

3. :doc:`../pythonApi/channel` objects are thread safe allowing data transfer between :doc:`../pythonApi/tasklet` objects on different threads.


Running two :doc:`../pythonApi/scheduleManager` queues in different Python Threads
----------------------------------------------------------------------------------

Below illustrates populating two :doc:`../pythonApi/scheduleManager` runnable queues on different Python threads.
:py:func:`scheduler.tasklet.thread_id` is used to print the thread_id of the :doc:`../pythonApi/tasklet`.

.. code-block:: python

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

   >>>log: 0 from thread_id: 8316
   >>>log: 0 from thread_id: 29412
   >>>log: 1 from thread_id: 8316
   >>>log: 1 from thread_id: 29412


Explanation of computation:

1. 2 sets of :doc:`../pythonApi/tasklet` objects were created on different threads. One on main and one on `thread`.
2. Each set were added to a :doc:`../pythonApi/scheduleManager` runnables queue, unique to the Python thread they were created on.
3. Output illustrates that both :doc:`../pythonApi/scheduleManager` queues are evaluated asynchronously until both complete.


Switching between threads
------------------------- 

:doc:`../pythonApi/tasklet` objects are bound to the thread they were created on.

A :doc:`../pythonApi/tasklet` cannot switch execution to a :doc:`../pythonApi/tasklet` bound to another thread.

Therefore, when switching to a :doc:`../pythonApi/tasklet` a check is made to ensure it's bound thread matches that of switch caller.

If this is not the case, rather than switching directly to the :doc:`../pythonApi/tasklet`, it is inserted into the :doc:`../pythonApi/scheduleManager` runnable queue on the same thread as the :doc:`../pythonApi/tasklet` to be switched to.



Transferring data between two Python threads
--------------------------------------------

As :doc:`../pythonApi/channel` objects are thread safe, data can be transferred between Python threads.

.. code-block:: python

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

   >>>received 'Hello from another thread!' from different thread

Explanation of computation:

1. The receiving :doc:`../pythonApi/tasklet` created inside ``otherThreadMainTasklet`` is executed inside a new Python thread ``recever_thread``. which means it will get its own :doc:`../pythonApi/scheduleManager` runnable queue.
2. ``recever_thread`` is a new Main :doc:`../pythonApi/tasklet` and is responsible for running its queue via :py:func:`scheduler.run`
3. The created :doc:`../pythonApi/tasklet` ``t`` is set to receive.
4. After the first execution of ``t`` it will be placed on the :doc:`../pythonApi/channel` object's blocked list so in order to keep the Python thread alive :py:func:`scheduler.run` is run inside ``while(t.alive)``.
5. ``Hello from another thread!`` is sent over the :doc:`../pythonApi/channel`, and as the :doc:`../pythonApi/tasklet` currently blocked on receive is bound to a thread other than the one of the sender, the receive tasklet is scheduled on the ``recever_thread`` :doc:`../pythonApi/scheduleManager` runnable queue.
6. The listening thread ``recever_thread`` which is still looping and executing :py:func:`scheduler.run` eventually hits the new :doc:`../pythonApi/tasklet` that was added from the other thread.
7. Execution of :doc:`../pythonApi/tasklet` `t` resumes having received the argument.
8. ``received 'Hello from another thread! from different thread`` is printed.
9. As the :doc:`../pythonApi/tasklet` completed :py:func:`scheduler.tasklet.alive` will now evaluate to ``False`` allowing ``recever_thread`` to exit the ``while`` loop and complete.


Suggested Further Reading
-------------------------

:doc:`manualControlScheduling`