/* 
	*************************************************************************

	Channel.h

	Author:    James Hawk
	Created:   July. 2024
	Project:   Scheduler

	Description:   

	  Base class for c++ python type implementation

	(c) CCP 2024

	*************************************************************************
*/
#pragma once
#ifndef PYTHONCPPTYPE_H
#define PYTHONCPPTYPE_H

#include "stdafx.h"

class PythonCppType
{
public:
	
	PythonCppType( PyObject* pythonObject );

    ~PythonCppType();

    void Incref();

	void Decref();

    Py_ssize_t ReferenceCount();

    PyObject* PythonObject();

private:

    PyObject* m_pythonObject;

};

#endif // PYTHONCPPTYPE_H
