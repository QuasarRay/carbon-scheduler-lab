/* 
	*************************************************************************

	PyScheduleManager.h

	Author:    James Hawk
	Created:   May. 2024
	Project:   Scheduler

	Description:   

	  PyScheduleManager python type definition

	(c) CCP 2024

	*************************************************************************
*/
#pragma once
#ifndef PyScheduleManager_H
#define PyScheduleManager_H

class ScheduleManager;

typedef struct PyScheduleManagerObject
{
	PyObject_HEAD

	ScheduleManager* m_implementation;

    PyObject* m_weakrefList; // TODO: This is apparently the old style, new style crashes

} _PyScheduleManagerObject;

#endif // PyScheduleManager_H