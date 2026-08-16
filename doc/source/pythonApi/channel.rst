Channel
=======

Python Api for custom Channel type.

Refer to guide section :ref:`channel-guides` for further usage information.

Methods
-------
.. autofunction:: scheduler.channel.send

    :seealso: :py:func:`scheduler.channel.preference`
    :seealso: :py:func:`scheduler.channel.receive`
    

.. autofunction:: scheduler.channel.send_exception

    :seealso: :py:func:`scheduler.TaskletExit`

    For further information see :doc:`../guides/howExceptionsAreManaged`.

.. autofunction:: scheduler.channel.send_throw

    :seealso: :py:func:`scheduler.TaskletExit`

    For further information see :doc:`../guides/howExceptionsAreManaged`.

.. autofunction:: scheduler.channel.receive

    :seealso: :py:func:`scheduler.channel.preference`
    :seealso: :py:func:`scheduler.channel.send`

.. autofunction:: scheduler.channel.clear

.. autofunction:: scheduler.channel.close

    :seealso: :py:func:`scheduler.channel.open`

.. autofunction:: scheduler.channel.open

    :seealso: :py:func:`scheduler.channel.close`

.. autofunction:: scheduler.channel.__iter__

.. autofunction:: scheduler.channel.__next__

    Performs a :py:func:`scheduler.channel.receive` until no more Tasklets remains blocked on Channel, at which point it will then block on receive until unblocked with a send. Close channel to receive a StopIteration at balance 0.

Attributes
----------

.. autoattribute:: scheduler.channel.preference

    For further information see :doc:`../guides/alteringChannelBehaviour`.

.. autoattribute:: scheduler.channel.balance

    For further information see :doc:`../guides/queryingChannelState`.

.. autoattribute:: scheduler.channel.queue

.. autoattribute:: scheduler.channel.closed

    :seealso: :py:func:`scheduler.channel.closing`

.. autoattribute:: scheduler.channel.closing

    :seealso: :py:func:`scheduler.channel.closed`
