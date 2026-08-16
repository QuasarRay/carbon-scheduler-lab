/* 
	*************************************************************************

	PyTasklet.h

	Author:    James Hawk
	Created:   April. 2024
	Project:   Scheduler

	Description:   

	  PyTaskletObject python type definition

	(c) CCP 2024

	*************************************************************************
*/
#pragma once
#ifndef PyTasklet_H
#define PyTasklet_H

class Tasklet;

typedef struct PyTaskletObject
{
	PyObject_HEAD

	Tasklet* m_implementation;

    PyObject* m_weakrefList;   // TODO: This is apparently the old style, new style crashes

} _PyTaskletObject;

#endif // PyTasklet_H
