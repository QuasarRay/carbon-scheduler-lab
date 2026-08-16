C-API
=====

Carbon-scheduler provides the following C functions.

To access the functions include ``<scheduler.h>``

Refer to :doc:`guides/usingSchedulerFromC` section for more infomration

Tasklet Functions
-----------------

.. doxygenfunction:: PyTasklet_New

.. doxygenfunction:: PyTasklet_Setup

.. doxygenfunction:: PyTasklet_Insert

.. doxygenfunction:: PyTasklet_GetBlockTrap

.. doxygenfunction:: PyTasklet_SetBlockTrap

.. doxygenfunction:: PyTasklet_IsMain

.. doxygenfunction:: PyTasklet_Check

.. doxygenfunction:: PyTasklet_Alive

.. doxygenfunction:: PyTasklet_Kill



Channel Functions
-----------------

.. doxygenfunction:: PyChannel_New

.. doxygenfunction:: PyChannel_Send

.. doxygenfunction:: PyChannel_Receive

.. doxygenfunction:: PyChannel_SendException

.. doxygenfunction:: PyChannel_GetQueue

.. doxygenfunction:: PyChannel_GetPreference

.. doxygenfunction:: PyChannel_SetPreference

.. doxygenfunction:: PyChannel_GetBalance

.. doxygenfunction:: PyChannel_Check

.. doxygenfunction:: PyChannel_SendThrow



Scheduler Module Functions
--------------------------

.. doxygenfunction:: PyScheduler_GetScheduler

.. doxygenfunction:: PyScheduler_Schedule

.. doxygenfunction:: PyScheduler_GetRunCount

.. doxygenfunction:: PyScheduler_GetCurrent

.. doxygenfunction:: PyScheduler_RunWithTimeout

.. doxygenfunction:: PyScheduler_RunNTasklets

.. doxygenfunction:: PyScheduler_SetChannelCallback

.. doxygenfunction:: PyScheduler_GetChannelCallback

.. doxygenfunction:: PyScheduler_SetScheduleCallback

.. doxygenfunction:: PyScheduler_SetScheduleFastCallback

.. doxygenfunction:: PyScheduler_GetNumberOfActiveScheduleManagers

.. doxygenfunction:: PyScheduler_GetNumberOfActiveChannels

.. doxygenfunction:: PyScheduler_GetAllTimeTaskletCount

.. doxygenfunction:: PyScheduler_GetActiveTaskletCount

.. doxygenfunction:: PyScheduler_GetTaskletsCompletedLastRunWithTimeout

.. doxygenfunction:: PyScheduler_GetTaskletsSwitchedLastRunWithTimeout