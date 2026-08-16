/* 
	*************************************************************************

	PyChannel.h

	Author:    James Hawk
	Created:   April. 2024
	Project:   Scheduler

	Description:   

	  PyChannelObject python type definition

	(c) CCP 2024

	*************************************************************************
*/
#pragma once
#ifndef PyChannel_H
#define PyChannel_H

class Channel;

typedef struct PyChannelObject
{
	PyObject_HEAD

	Channel* m_implementation;

    PyObject* m_weakrefList; // TODO: This is apparently the old style, new style crashes unless GC is turned on for type

} _PyChannelObject;

#endif // PyChannel_H