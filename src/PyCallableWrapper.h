/* 
	*************************************************************************

	PyCallableWrapper.h

	Author:    Joseph Frangoudes
	Created:   October. 2024
	Project:   Scheduler

	Description:   

	  PyCallableWrapper python type definition

	(c) CCP 2024

	*************************************************************************
*/
#pragma once
#ifndef PyCallableWrapper_H
#define PyCallableWrapper_H

class Tasklet;

typedef void( OnExceptionCB )( PyObject* exception, void* data );

typedef struct PyCallableWrapperObject
{
	PyObject_HEAD

	PyObject* m_callable;

	PyObject* m_weakrefList;

    void* m_ownerTasklet;

    OnExceptionCB* m_onExceptioncb;

} _PyCallableWrapperObject;

#endif // PyCallableWrapper_H
