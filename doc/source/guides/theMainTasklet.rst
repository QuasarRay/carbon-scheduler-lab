The Main Tasklet
================

Every Python thread is assigned its own :doc:`../pythonApi/scheduleManager` on demand.

Each :doc:`../pythonApi/scheduleManager` will construct its own base :doc:`../pythonApi/tasklet`, this :doc:`../pythonApi/tasklet` is referred to as the 'main' :doc:`../pythonApi/tasklet`

All initial commands will be run on the 'main' :doc:`../pythonApi/tasklet` and for the most part the 'main' :doc:`../pythonApi/tasklet` can be treated just like any other, however care must be taken to ensure it is never blocked indefinitely.


.. code-block:: python

   # All commands here are executed on the main tasklet
   main_tasklet = scheduler.get_current()


Explanation of computation:

:py:func:`scheduler.get_current` returns the active main :doc:`../pythonApi/tasklet` that is currently executing.



Blocking The Main Tasklet
-------------------------
If the 'main' :doc:`../pythonApi/tasklet` is blocked indefinitely a ``RuntimeError`` will be raised.

.. code-block:: python

   # we are on the main tasklet
   channel = scheduler.channel()

   # call receive with nothing sending
   channel.receive()

   >>>RuntimeError: Deadlock: the last runnable tasklet cannot be blocked.

Explanation of computation:

The call to :py:func:`scheduler.channel.receive` attempts to 'block' the running :doc:`../pythonApi/tasklet` (in this case 'main') as there are no :doc:`../pythonApi/tasklet` objects sending.
This would cause the 'main' :doc:`../pythonApi/tasklet` to hang indefinitely so a ``RuntimeError`` is raised.

Note: It is sometimes permitted to 'block' the 'main' :doc:`../pythonApi/tasklet` on data transfer. Refer to :ref:`channel-blocking-main-tasklet` for more information.


Main Tasklets and Python Threads
--------------------------------
The rules surrounding 'blocking' on the 'main' :doc:`../pythonApi/tasklet` apply per thread, as each thread is assigned its own 'main' :doc:`../pythonApi/tasklet`.

This is illustrated below. Refer to :doc:`schedulingAcrossMultiplePythonThreads` for more further information regarding scheduling across Python threads.

.. code-block:: python

   def otherThreadMainTasklet():
      # we are on the main tasklet
      channel = scheduler.channel()

      # call receive with nothing sending
      channel.receive()

   other_thread = threading.Thread(target=otherThreadMainTasklet, args=())
   other_thread.start()

   >>>Exception in thread Thread-1 (otherThreadMainTasklet): . . .
   >>>RuntimeError: Deadlock: the last runnable tasklet cannot be blocked.


Suggested Further Reading
-------------------------

:doc:`schedulingAcrossMultiplePythonThreads`