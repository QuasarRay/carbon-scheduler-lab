/* 
	*************************************************************************

	Scheduler.h

	Author:    James Hawk
	Created:   Feb. 2024
	Project:   Scheduler

	Description:   

 		Provides channels and a scheduler for Greenlet coroutines.

 		SchedulerAPI() is the entrypoint for any external code (e.g. blue)
		that wants to call into any of scheduler's Python Capsule's functions.

	(c) CCP 2024

	*************************************************************************
*/

#ifndef Py_SCHEDULER_H
#define Py_SCHEDULER_H

#include <type_traits>

/* Header file for scheduler */

/* C API functions */
struct PyTaskletObject;
struct PyChannelObject;

typedef int( schedule_hook_func )( struct PyTaskletObject* from, struct PyTaskletObject* to );

struct SchedulerCAPI
{
    // =============== function pointer types ===============
    //tasklet functions
    using PyTasklet_New_Routine           		                        = std::add_pointer_t<struct PyTaskletObject*(PyTypeObject*, PyObject*)>;
    using PyTasklet_Setup_Routine                                       = std::add_pointer_t<int(struct PyTaskletObject*, PyObject * args, PyObject * kwds)>;
    using PyTasklet_Insert_Routine                                      = std::add_pointer_t<int(struct PyTaskletObject*)>;
    using PyTasklet_GetBlockTrap_Routine                                = std::add_pointer_t<int(struct PyTaskletObject*)>;
    using PyTasklet_SetBlockTrap_Routine                                = std::add_pointer_t<void(struct PyTaskletObject*, int)>;
    using PyTasklet_IsMain_Routine                                      = std::add_pointer_t<int(struct PyTaskletObject*)>;
    using PyTasklet_Check_Routine                                       = std::add_pointer_t<int(PyObject*)>;
    using PyTasklet_Alive_Routine                                       = std::add_pointer_t<int(struct PyTaskletObject*)>;
    using PyTasklet_Kill_Routine                                        = std::add_pointer_t<int(struct PyTaskletObject*)>;
    using PyTasklet_GetTimesSwitchedTo_Routine                          = std::add_pointer_t<long(struct PyTaskletObject*)>;
    using PyTasklet_GetContext_Routine                                  = std::add_pointer_t<const char*(struct PyTaskletObject*)>;

    //channel functions
	using PyChannel_New_Routine           		                        = std::add_pointer_t<struct PyChannelObject*(PyTypeObject*)>;
	using PyChannel_Send_Routine          		                        = std::add_pointer_t<int(struct PyChannelObject*, PyObject*)>;
	using PyChannel_Receive_Routine       		                        = std::add_pointer_t<PyObject*(struct PyChannelObject*)>;
    using PyChannel_SendException_Routine 		                        = std::add_pointer_t<int(struct PyChannelObject*, PyObject*, PyObject*)>;
    using PyChannel_GetQueue_Routine      		                        = std::add_pointer_t<PyObject*(struct PyChannelObject*)>;
    using PyChannel_GetPreference_Routine 		                        = std::add_pointer_t<int(struct PyChannelObject*)>;
    using PyChannel_SetPreference_Routine 		                        = std::add_pointer_t<void(struct PyChannelObject*, int)>;
    using PyChannel_GetBalance_Routine    		                        = std::add_pointer_t<int(struct PyChannelObject*)>;
    using PyChannel_Check_Routine                                       = std::add_pointer_t<int(PyObject*)>;
    using PyChannel_SendThrow_Routine                                   = std::add_pointer_t<int(struct PyChannelObject*, PyObject*, PyObject*, PyObject*)>;

    //scheduler functions
    using PyScheduler_GetScheduler_Routine                              = std::add_pointer_t<PyObject*(void)>;
    using PyScheduler_Schedule_Routine                                  = std::add_pointer_t<PyObject*(PyObject*, int)>;
    using PyScheduler_GetRunCount_Routine                               = std::add_pointer_t<int(void)>;
    using PyScheduler_GetCurrent_Routine                                = std::add_pointer_t<PyObject*(void)>;
    using PyScheduler_RunWithTimeout_Routine                            = std::add_pointer_t<PyObject*(long long)>;
    using PyScheduler_RunNTasklets_Routine                              = std::add_pointer_t<PyObject*(int)>;
    using PyScheduler_SetChannelCallback_Routine                        = std::add_pointer_t<int(PyObject*)>;
    using PyScheduler_GetChannelCallback_Routine                        = std::add_pointer_t<PyObject*(void)>;
    using PyScheduler_SetScheduleCallback_Routine                       = std::add_pointer_t<int(PyObject*)>;
    using PyScheduler_SetScheduleFastCallback_Routine                   = std::add_pointer_t<void(schedule_hook_func func)>;
    using PyScheduler_GetNumberOfActiveScheduleManagers_Routine         = std::add_pointer_t<int(void)>;
    using PyScheduler_GetNumberOfActiveChannels_Routine                 = std::add_pointer_t<int(void)>;
    using PyScheduler_GetAllTimeTaskletCount_Routine                    = std::add_pointer_t<int(void)>;
    using PyScheduler_GetActiveTaskletCount_Routine                     = std::add_pointer_t<int(void)>;
    using PyScheduler_GetTaskletsCompletedLastRunWithTimeout_Routine    = std::add_pointer_t<int(void)>;
    using PyScheduler_GetTaskletsSwitchedLastRunWithTimeout_Routine     = std::add_pointer_t<int(void)>;

    // =============== member function pointers ===============

    //tasklet functions
	PyTasklet_New_Routine PyTasklet_New;
	PyTasklet_Setup_Routine PyTasklet_Setup;
	PyTasklet_Insert_Routine PyTasklet_Insert;
	PyTasklet_GetBlockTrap_Routine PyTasklet_GetBlockTrap;
	PyTasklet_SetBlockTrap_Routine PyTasklet_SetBlockTrap;
	PyTasklet_IsMain_Routine PyTasklet_IsMain;
	PyTasklet_Check_Routine PyTasklet_Check;
	PyTasklet_Alive_Routine PyTasklet_Alive;
	PyTasklet_Kill_Routine PyTasklet_Kill;

    //channel functions
	PyChannel_New_Routine PyChannel_New;
	PyChannel_Send_Routine PyChannel_Send;
	PyChannel_Receive_Routine PyChannel_Receive;
	PyChannel_SendException_Routine PyChannel_SendException;
	PyChannel_GetQueue_Routine PyChannel_GetQueue;
	PyChannel_GetPreference_Routine PyChannel_GetPreference;
	PyChannel_SetPreference_Routine PyChannel_SetPreference;
	PyChannel_GetBalance_Routine PyChannel_GetBalance;
	PyChannel_Check_Routine PyChannel_Check;
	PyChannel_SendThrow_Routine PyChannel_SendThrow;

    //scheduler functions
	PyScheduler_GetScheduler_Routine PyScheduler_GetScheduler;
	PyScheduler_Schedule_Routine PyScheduler_Schedule;
	PyScheduler_GetRunCount_Routine PyScheduler_GetRunCount;
	PyScheduler_GetCurrent_Routine PyScheduler_GetCurrent;
	PyScheduler_RunWithTimeout_Routine PyScheduler_RunWithTimeout;
	PyScheduler_RunNTasklets_Routine PyScheduler_RunNTasklets;
	PyScheduler_SetChannelCallback_Routine PyScheduler_SetChannelCallback;
	PyScheduler_GetChannelCallback_Routine PyScheduler_GetChannelCallback;
	PyScheduler_SetScheduleCallback_Routine PyScheduler_SetScheduleCallback;
	PyScheduler_SetScheduleFastCallback_Routine PyScheduler_SetScheduleFastCallback;
	PyScheduler_GetNumberOfActiveScheduleManagers_Routine PyScheduler_GetNumberOfActiveScheduleManagers;
	PyScheduler_GetNumberOfActiveChannels_Routine PyScheduler_GetNumberOfActiveChannels;
	PyScheduler_GetAllTimeTaskletCount_Routine PyScheduler_GetAllTimeTaskletCount;
	PyScheduler_GetActiveTaskletCount_Routine PyScheduler_GetActiveTaskletCount;
	PyScheduler_GetTaskletsCompletedLastRunWithTimeout_Routine PyScheduler_GetTaskletsCompletedLastRunWithTimeout;
	PyScheduler_GetTaskletsSwitchedLastRunWithTimeout_Routine PyScheduler_GetTaskletsSwitchedLastRunWithTimeout;

    // types
    PyTypeObject* PyTaskletType;
	PyTypeObject* PyChannelType;

    // exceptions
	PyObject** TaskletExit;

    PyTasklet_GetTimesSwitchedTo_Routine PyTasklet_GetTimesSwitchedTo;
	PyTasklet_GetContext_Routine PyTasklet_GetContext;
};


#ifndef SCHEDULER_MODULE
/**
 * Only implement SchedulerAPI() as long as it's being used outside of Scheduler itself.
 * PyCapsule_Import will set an exception if there's an error.
 *
 * NOTE:
 * - The "static SchedulerCAPI* api" variable is only static within each compilation unit.
 * - That's because the "static" keyword in front of the function definition means the
 * - function will become "internally linked".
 * - That means each translation unit, that includes the Scheduler.h header, will
 * - have its own separate instance of the function. We're OK with that.
 *
 * @return SchedulerCAPI * or nullptr on error
 */
static SchedulerCAPI* SchedulerAPI()
{
	static SchedulerCAPI* api;
	if( api == nullptr )
	{
		api = reinterpret_cast<SchedulerCAPI*>( PyCapsule_Import( "scheduler._C_API", 0 ) );
	}
	return api;
}
#endif /* !defined(SCHEDULER_MODULE) */

#endif /* !defined(Py_SCHEDULER_H) */