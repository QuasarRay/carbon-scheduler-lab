Tasklet
=======

Python Api for custom Tasklet type.

Refer to guide section :ref:`tasklet-guides` for further usage information.

Methods
-------
.. autofunction:: scheduler.tasklet.__init__

    Sets up tasklet and calls :py:func:`scheduler.tasklet.bind`

.. autofunction:: scheduler.tasklet.insert

    .. note::

        It is possible to perform this operation from a thread other than the thread associated with the Tasklet in question.

    For further information see :doc:`../guides/understandingTaskletScheduleOrder`.

.. autofunction:: scheduler.tasklet.remove

    .. note::

        It is possible to perform this operation from a thread other than the thread associated with the Tasklet in question.

.. autofunction:: scheduler.tasklet.run

    .. note::

        It is not possible to perform this operation from a thread other than the thread associated with the Tasklet in question. If performed will silently ignore.

    For further information see:
    
        :doc:`../guides/understandingTaskletScheduleOrder`.

        :doc:`../guides/schedulingAcrossMultiplePythonThreads`.


.. autofunction:: scheduler.tasklet.switch

    .. note::

        It is not possible to perform this operation from a thread other than the thread associated with the Tasklet in question. Will raise a RuntimeError.

    For further information regarding manual switching see :doc:`../guides/manualControlScheduling`.

.. autofunction:: scheduler.tasklet.throw

    .. note::

        It is not possible to perform this operation from a thread other than the thread associated with the Tasklet in question. Will raise a RuntimeError.

    :seealso: :py:func:`scheduler.TaskletExit`

    For further information see :doc:`../guides/howExceptionsAreManaged`.

.. autofunction:: scheduler.tasklet.raise_exception

    .. note::

        It is not possible to perform this operation from a thread other than the thread associated with the Tasklet in question. Will raise a RuntimeError.

    :seealso: :py:func:`scheduler.TaskletExit`

    For further information see :doc:`../guides/howExceptionsAreManaged`.

.. autofunction:: scheduler.tasklet.kill

    .. note::

        It is not possible to perform this operation from a thread other than the thread associated with the Tasklet in question. Will raise a RuntimeError.

    :seealso: :py:func:`scheduler.TaskletExit`

    For further information see :doc:`../guides/howExceptionsAreManaged`.

.. autofunction:: scheduler.tasklet.set_context

.. autofunction:: scheduler.tasklet.bind

    .. note::

        It is not possible to perform this operation from a thread other than the thread associated with the Tasklet in question. Will raise a RuntimeError.

.. autofunction:: scheduler.tasklet.__call__

    Calls :py:func:`scheduler.tasklet.setup`

.. autofunction:: scheduler.tasklet.setup

    .. note::

        It is not possible to perform this operation from a thread other than the thread associated with the Tasklet in question. Will raise a RuntimeError.

Attributes
----------

.. autoattribute:: scheduler.tasklet.alive

.. autoattribute:: scheduler.tasklet.blocked

    :seealso: :py:func:`scheduler.channel`

.. autoattribute:: scheduler.tasklet.scheduled

    For further information see :doc:`../guides/understandingTaskletScheduleOrder`.

.. autoattribute:: scheduler.tasklet.block_trap

    For further information see :doc:`../guides/restrictingTaskletControlFlow`.

.. autoattribute:: scheduler.tasklet.is_current

.. autoattribute:: scheduler.tasklet.is_main

.. autoattribute:: scheduler.tasklet.thread_id

    For further information see :doc:`../guides/schedulingAcrossMultiplePythonThreads`.

.. autoattribute:: scheduler.tasklet.next

.. autoattribute:: scheduler.tasklet.prev

.. autoattribute:: scheduler.tasklet.paused

.. autoattribute:: scheduler.tasklet.method_name

.. autoattribute:: scheduler.tasklet.module_name

.. autoattribute:: scheduler.tasklet.context

.. autoattribute:: scheduler.tasklet.file_name

.. autoattribute:: scheduler.tasklet.line_number

.. autoattribute:: scheduler.tasklet.parent_callsite

.. autoattribute:: scheduler.tasklet.startTime

.. autoattribute:: scheduler.tasklet.endTime

.. autoattribute:: scheduler.tasklet.runTime

.. autoattribute:: scheduler.tasklet.highlighted

.. autoattribute:: scheduler.tasklet.dont_raise

.. autoattribute:: scheduler.tasklet.context_manager_getter

.. autoattribute:: scheduler.tasklet.times_switched_to

.. autoattribute:: scheduler.tasklet.exception_handler
