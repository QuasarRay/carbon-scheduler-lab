Guides
======

Guides containing usage examples for all functionality.

.. _tasklet-guides:

Getting started
---------------

.. toctree::
   :maxdepth: 1

   guides/whatIsATasklet

   guides/runningSimpleTasklet

   guides/initialisingATasklet

   guides/queryingScheduleManagerState

   guides/theMainTasklet


.. _schedule-guides:

Control Flow
------------
.. toctree::
   :maxdepth: 1

   guides/understandingTaskletScheduleOrder

   guides/yieldingFromATasklet

   guides/killingTasklets

   guides/restrictingTaskletControlFlow

   guides/manualControlScheduling

   guides/schedulingAcrossMultiplePythonThreads


.. _channel-guides:

Data Transfer beween Tasklets
-----------------------------

.. toctree::
   :maxdepth: 1

   guides/sendingDataBetweenTaskletsUsingChannels

   guides/queryingChannelState

   guides/alteringChannelBehaviour


.. _exception-guides:

Exception handling
------------------
.. toctree::
   :maxdepth: 1
   
   guides/howExceptionsAreManaged

Tasklet Context Managers
---------------------------
.. toctree::
   :maxdepth: 1

   guides/settingContextManagers

.. _capi-guides:

C-API Usage
------------------
.. toctree::
   :maxdepth: 1
   
   guides/usingSchedulerFromC