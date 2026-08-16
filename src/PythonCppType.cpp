#include "PythonCppType.h"

PythonCppType::PythonCppType(PyObject* pythonObject):
	m_pythonObject( pythonObject )
{

}

PythonCppType ::~PythonCppType()
{

}

void PythonCppType::Incref()
{
	Py_IncRef( m_pythonObject );
}

void PythonCppType::Decref()
{
	Py_DecRef( m_pythonObject );
}

Py_ssize_t PythonCppType::ReferenceCount()
{
	return m_pythonObject->ob_refcnt;
}

PyObject* PythonCppType::PythonObject()
{
	return m_pythonObject;
}
