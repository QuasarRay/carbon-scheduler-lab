/* 
	*************************************************************************

	ScheduleManager.h

	Author:    James Hawk
	Created:   Feb. 2024
	Project:   Scheduler

	Description:   

	  Functionality related to scheduling tasklets

	(c) CCP 2024

	*************************************************************************
*/
#pragma once
#ifndef ScheduleManager_H
#define ScheduleManager_H

#include "stdafx.h"

#include "PythonCppType.h"

#include <map>
#include <chrono>
#include <unordered_set>

typedef int( schedule_hook_func )( struct PyTaskletObject* from, struct PyTaskletObject* to );  // TODO remove redef

enum class RescheduleType;

enum class RunType
{
    STANDARD,
    TIME_LIMITED,
    TASKLET_LIMITED
};

class Tasklet;

class ScheduleManager : public PythonCppType
{
public:
	ScheduleManager( PyObject* pythonObject );

	~ScheduleManager();

    static long NumberOfActiveScheduleManagers();

    static ScheduleManager* GetThreadScheduleManager();

	void SetCurrentTasklet( Tasklet* tasklet );

	Tasklet* GetCurrentTasklet();

    bool RemoveTasklet( Tasklet* tasklet );

    void InsertTaskletToRunNext( Tasklet* tasklet );

    void InsertTasklet( Tasklet* tasklet );

    int GetCachedTaskletCount();

    int GetCalculatedTaskletCount();

    bool Schedule( RescheduleType position, bool remove = false );

    bool Yield();

    bool RunNTasklets( int n );

    bool RunTaskletsForTime( long long timeout );

    bool Run( Tasklet* startTasklet = nullptr );

    Tasklet* GetMainTasklet();

    void SetSchedulerFastCallback( schedule_hook_func* func );

    static void SetSchedulerCallback( PyObject* callback );

    static PyObject* SchedulerCallback();

    bool IsSwitchTrapped();

    int SwitchTrapLevel();

    void SetSwitchTrapLevel( int level );

    static int GetNumberOfTaskletsCompletedLastRunWithTimeout();

    static int GetNumberOfTaskletsSwitchedLastRunWithTimeout();

    void RegisterTaskletToThread( Tasklet* tasklet );

	void UnregisterTaskletFromThread( Tasklet* tasklet );

	void ClearThreadTasklets();

	unsigned long ThreadId() const;


private:

    void RunSchedulerCallback( Tasklet* previous, Tasklet* next );

    void CreateSchedulerTasklet();

    void OnSwitch();

public:

    inline static PyTypeObject* s_callableWrapperType;

    inline static PyTypeObject* s_taskletType;

    inline static PyTypeObject* s_scheduleManagerType;

    inline static bool s_useNestedTasklets = true;
    
    inline static PyObject* m_scheduleManagerThreadKey = nullptr;

private:

    unsigned long m_threadId;

    Tasklet* m_schedulerTasklet;

    Tasklet* m_currentTasklet; //Weak ref

    Tasklet* m_previousTasklet; //Weak ref

    long m_switchTrapLevel;

    // This is global, not per schedule manager
	inline static PyObject* s_schedulerCallback = nullptr;

    // This is global, not per schedule manager 
    inline static schedule_hook_func* s_schedulerFastCallback = nullptr; 

    RunType m_runType;

    int m_taskletLimit;

    long long m_totalTaskletRunTimeLimit;

    bool m_firstTimeLimitTestSkipped;

    std::chrono::steady_clock::time_point m_startTime;

    bool m_stopScheduler;

    int m_numberOfTaskletsInQueue;

    static inline long s_numberOfTaskletsCompletedLastRunWithTimeout = 0;

    static inline long s_numberOfTaskletsSwitchedLastRunWithTimeout = 0;

    static inline long s_numberOfActiveScheduleManagers = 0;

    std::unordered_set<Tasklet*> m_taskletsOnSchedulerThread;

	static inline std::map<long, ScheduleManager*> s_closingScheduleManagers;
    
};

#endif // ScheduleManager_H
