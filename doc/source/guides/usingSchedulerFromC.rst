Using Scheduler From C
======================

A :doc:`../cApi` is provided exposing much of the functionality to c.

Functions are provided via a Python Capsule which requires importing prior to use.

.. code-block:: c++

    #import <scheduler.h>

    // Importing the capsule
    m_scheduler_api = SchedulerAPI();

    // Get runnables queue size - example api usage
    int runcount = m_api->PyScheduler_GetRunCount();


For more examples refer to the project gtests in the target ``SchedulerCapiTest``.
