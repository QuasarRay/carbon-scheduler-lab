#include "ScheduleManager.h"

#include <new>

#include "PyScheduleManager.h"

static PyObject*
	ScheduleManagerNew( PyTypeObject* type, PyObject* args, PyObject* kwds )
{
	PyScheduleManagerObject* self;

	self = (PyScheduleManagerObject*)type->tp_alloc( type, 0 );

	if( self != nullptr )
	{
		self->m_implementation = nullptr;

		self->m_weakrefList = nullptr;
	}

	return (PyObject*)self;
}

static int
	ScheduleManagerInit( PyScheduleManagerObject* self, PyObject* args, PyObject* kwds )
{

	// Allocate the memory for the implementation member
	self->m_implementation = (ScheduleManager*)PyObject_Malloc( sizeof( ScheduleManager ) );

	if( !self->m_implementation )
	{
		PyErr_SetString( PyExc_RuntimeError, "Failed to allocate memory for implementation object." );

		return -1;
	}

    // Call constructor
	try
	{
		new( self->m_implementation ) ScheduleManager( reinterpret_cast<PyObject*>( self ) );
	}
	catch( const std::exception& ex )
	{
		PyObject_Free( self->m_implementation );

		PyErr_SetString( PyExc_RuntimeError, ex.what() );

		return -1;
	}
	catch( ... )
	{
		PyObject_Free( self->m_implementation );

		PyErr_SetString( PyExc_RuntimeError, "Failed to construct implementation object." );

		return -1;
	}

	return 0;
}

static void
	ScheduleManager_dealloc( PyScheduleManagerObject* self )
{
	if( self->m_implementation )
	{
		// Call destructor
		self->m_implementation->~ScheduleManager();

		PyObject_Free( self->m_implementation );
	}
    
    // Handle weakrefs
	if( self->m_weakrefList != nullptr )
	{
		PyObject_ClearWeakRefs( (PyObject*)self );
	}

    Py_TYPE( self )->tp_free( (PyObject*)self );
}

static PyMethodDef ScheduleManager_methods[] = {
	{ NULL } /* Sentinel */
};

static PyTypeObject ScheduleManagerType = {
	/* The ob_type field must be initialized in the module init function
     * to be portable to Windows without using C++. */
	PyVarObject_HEAD_INIT( NULL, 0 ) "scheduler.ScheduleManager", /*tp_name*/
	sizeof( PyScheduleManagerObject ), /*tp_basicsize*/
	0, /*tp_itemsize*/
	/* methods */
	(destructor)ScheduleManager_dealloc, /*tp_dealloc*/
	0, /*tp_vectorcall_offset*/
	0, /*tp_getattr*/
	0, /*tp_setattr*/
	0, /*tp_as_async*/
	0, /*tp_repr*/
	0, /*tp_as_number*/
	0, /*tp_as_sequence*/
	0, /*tp_as_mapping*/
	0, /*tp_hash*/
	0, /*tp_call*/
	0, /*tp_str*/
	0, /*tp_getattro*/
	0, /*tp_setattro*/
	0, /*tp_as_buffer*/
	Py_TPFLAGS_DEFAULT | Py_TPFLAGS_BASETYPE, /*tp_flags*/
	PyDoc_STR( "Schedule Manager objects" ), /*tp_doc*/
	0, /*tp_traverse*/
	0, /*tp_clear*/
	0, /*tp_richcompare*/
	offsetof( PyScheduleManagerObject, m_weakrefList ), /*tp_weaklistoffset*/
	0, /*tp_iter*/
	0, /*tp_iternext*/
	ScheduleManager_methods, /*tp_methods*/
	0, /*tp_members*/
	0, /*tp_getset*/
	0,
	/* see PyInit_xx */ /*tp_base*/
	0, /*tp_dict*/
	0, /*tp_descr_get*/
	0, /*tp_descr_set*/
	0, /*tp_dictoffset*/
	(initproc)ScheduleManagerInit, /*tp_init*/
	0, /*tp_alloc*/
	ScheduleManagerNew, /*tp_new*/
	0, /*tp_free*/
	0, /*tp_is_gc*/
};