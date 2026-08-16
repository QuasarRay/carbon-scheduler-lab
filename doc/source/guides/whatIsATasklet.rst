What is a Tasklet?
==================

A :doc:`../pythonApi/tasklet` is a structure which encapsulates a coroutine.

A :doc:`../pythonApi/tasklet` requires:

1. A standard Python callable to execute.
2. Arguments to pass to the callable.


Executing callable with arguments a Tasklet
-------------------------------------------

Below shows an example of a very simple :doc:`../pythonApi/tasklet` setup and execution.
(refer to :doc:`runningSimpleTasklet` for further more details.)

.. code-block:: python

    def pythonCallable(arg):
        print("Hello {}".format(arg))

   # schedule a tasklet to be run
   scheduler.tasklet(pythonCallable)("World")
   scheduler.run()

   >>>Hello World


Data transfer between Tasklets
------------------------------
:doc:`../pythonApi/tasklet` objects can send and receive data to each other cooperatively.
(refer to :doc:`sendingDataBetweenTaskletsUsingChannels` for further more details.)

Below illustrates how :doc:`../pythonApi/tasklet` objects can be used to bounce calls from one callable to another without causing a stack overflow.

This example includes complex ideas but is presented here to prove that such a scenario is possible.


.. code-block:: python

    coroutine1_channel = scheduler.channel()
    coroutine2_channel = scheduler.channel()

    def coroutine1Callable():
        while True:
            print(coroutine1_channel.receive())
            coroutine2_channel.send("from Coroutine1")
                
    def coroutine2Callable():
        while True:
            print(coroutine2_channel.receive())
            coroutine1_channel.send("from Coroutine2")
            
    scheduler.tasklet(coroutine1Callable)()
    scheduler.tasklet(coroutine2Callable)()
    scheduler.tasklet(coroutine1_channel.send)("from Main")

    scheduler.run()

    >>>from Main
    >>>from Coroutine1
    >>>from Coroutine2
    >>>from Coroutine1
    >>>from Coroutine2
    >>>from Coroutine1
    >>>from Coroutine2
    >>>from Coroutine1
    >>>from Coroutine2
    >>>from Coroutine1
    >>>from Coroutine2
    ...

Explanation of computation:

This code will run indefinitely without causing a stack overflow.
Full explanation of this code is outside the scope of :doc:`whatIsATasklet`. To fully understand this please refer to :doc:`../guides`.

How do Tasklets work?
---------------------
carbon-scheduler uses the `Greenlet <https://greenlet.readthedocs.io/en/latest/>`_ package to manage stack switching.

Each :doc:`../pythonApi/tasklet` is a wrapper for a `Greenlet <https://greenlet.readthedocs.io/en/latest/>`_ which adds additional control flow logic.

:doc:`../pythonApi/channel` and :doc:`../pythonApi/scheduleManager` objects are implemented to further extend scheduling logic.

Functionality is based on the Python 3.7 specification of `Stackless Python <https://stackless.readthedocs.io/en/3.8-slp/stackless-python.html>`_.

See :doc:`../designDocuments/originalDesignBrief` for further details related to the original project aims.

Suggested Further Reading
-------------------------
:doc:`runningSimpleTasklet`