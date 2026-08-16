Stackless Divergence
====================

Lists occurances where ``carbon-scheduler`` diverges from `Stackless Python <https://stackless.readthedocs.io/en/3.8-slp/stackless-python.html>`_ behaviour.

The original aim was to match `Stackless Python <https://stackless.readthedocs.io/en/3.8-slp/stackless-python.html>`_ functionality, however some deviation is expected due to the nature of `Stackless Python <https://stackless.readthedocs.io/en/3.8-slp/stackless-python.html>`_ being built into the interpreter.

Over time it is expected that divergence will increase.


Overview of differences
-----------------------
* :ref:`divergence-scheduler-current-scheduler-main`
* :ref:`divergence-scheduler-tasklet-execution-order` 
* :ref:`divergence-scheduler-cross-thread-Tasklet-operations` 



.. _divergence-scheduler-current-scheduler-main:

scheduler.current and scheduler.main are not implemented
--------------------------------------------------------
These attributes for current and main are not provided due to innability to keep them correct when used with threading.


**The Alternative**

use :py:func:`scheduler.getcurrent` and :py:func:`scheduler.getmain`. These will return the correct value for the Python thread which they were called.



.. _divergence-scheduler-tasklet-execution-order:

Tasklet execution order when using :py:func:`tasklet.run` can be altered
------------------------------------------------------------------------
When :py:func:`tasklet.run` is called it creates a nested non linear tasklet execution order.

carbon-scheduler allows the user to turn this behaviour off and flatten the queue using :py:func:`scheduler.set_use_nested_tasklets`.

See :doc:`nestedTaskletsVsFlatSchedulingQueue` for further details.


.. _divergence-scheduler-cross-thread-Tasklet-operations:

Cross thread Tasklet operations
-------------------------------
Many cross thread Tasklet operations have not been supported. Differences are due to:

1. Greenlet doesn't allow rebinding Greenlets to other threads.
2. Lack of need based on code survey

Differences
^^^^^^^^^^^
* :py:func:`tasklet.throw` will throw an error if performed on a thread other than the Tasklet's thread.

    Stackless had the following behaviour:

    * Pending Throws - Would add the pending operation to the correct thread associated with the Tasklet.

    * Non-pending throws - Only gets evaluated when the schedule manager of the Tasklet's thread is run again. It is sort of pending but placed at the start of the runnables queue.

* :py:func:`tasklet.raise_exception` will throw an error if performed on a thread other than the Tasklet's thread. Stackless behaviour was similar to above description for :py:func:`tasklet.throw`

* :py:func:`tasklet.kill` will throw an error if performed on a thread other than the Tasklet's thread. Stackless behaviour was similar to above description for :py:func:`tasklet.throw`

* :py:func:`tasklet.bind` will throw an error if performed on a thread other than the Tasklet's thread. Stackless would correctly bind on the Tasklet's original thread.

* :py:func:`tasklet.setup` will throw an error if performed on a thread other than the Tasklet's thread. Stackless would perform Tasklet setup on the Tasklet's original thread.

.. _divergence-scheduler-tasklet-thread-finish:

Thread finish, Tasklet cleanup
------------------------------
When a thread finishes, all Tasklets associated with the Thread will be cleaned up.

1. Tasklets that have not run before will slightly be killed.

2. Tasklets that have started will get :py:func:`scheduler.TaskletExit` raised on them. It is important to not have this become an infinate loop as this will lead to a leak.

3. Tasklets blocked on a :doc:`../pythonApi/channel` will be killed and removed from the blocked list.

Stackless behaviour would not kill Tasklets when their thread finished. They would require a rebinding of thread, this is not available in Greenlet.