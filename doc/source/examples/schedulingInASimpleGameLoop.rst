Scheduling in a Carbon style game loop
======================================

Presented here is a simple scheduling setup which can provide task scheduling usable in a game.

The approach presented is the basic structure of how Carbon currently implements its scheduling.


Python Example
--------------

.. code-block:: python

   yielders = scheduler.channel()

   yielders.preference = 0

   def wakeUpYielders():
      print("Waking up {} yielders".format(abs(yielders.balance)))
      while(yielders.balance < 0):
         yielders.send(None)
         
   def exampleTask(x):
      while(True):
         print("Running exampleTask #{}".format(x))
         yielders.receive()
      
   # Create some game tasks
   for i in range(200):
      scheduler.tasklet(exampleTask)(i)

   # Run game loop twice
   while True:
      print("Start of Game Loop")
      wakeUpYielders()
      scheduler.run_n_tasklets(10)

      # Do other stuff such as render...

Explanation of computation:

1. A single :doc:`../pythonApi/channel` is created ``yielders`` which will be responsible for control flow.
2. Tasklets for 200 example tasks are created and bound to callable ``exampleTask`` which will print a message then call :py:func:`scheduler.channel.receive` which will then yield the :doc:`../pythonApi/tasklet` as nothing is sending. The Tasks will loop indefinitely.
3. A game loop then loops execution indefinitely.
4. The call to ``wakeUpYielders`` will loop over all Tasklets blocked on the :doc:`../pythonApi/channel` and send ``None`` in order to schedule them. As the :doc:`../pythonApi/channel` preference is prefer neither (0) they are not switched to immediately.
5. Running all Tasklets queued in the runnables queue could take a long time, therefore ``scheduler.run_n_tasklets(2)`` is used to just run 10.
6. Remaing game tasks can then be carried out before repeating.

Carbon Implementation
---------------------
This game loop is implemented in the c side in Carbon inside ``carbon-blue``.

The pattern is the same however rather than running n Tasklets, Tasklets are evaluated for a set time.