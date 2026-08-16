#include "Channel.h"

#include <new>

#include "Tasklet.h"
#include "PyChannel.h"

static PyObject*
	ChannelNew( PyTypeObject* type, PyObject* args, PyObject* kwds )
{
	PyChannelObject* self;

	self = (PyChannelObject*)type->tp_alloc( type, 0 );

	if( self != nullptr )
	{
		self->m_implementation = nullptr;

		self->m_weakrefList = nullptr;
	}

	return (PyObject*)self;
}

static int
	ChannelInit( PyChannelObject* self, PyObject* Py_UNUSED( args ), PyObject* Py_UNUSED( kwds ) )
{

	// Allocate the memory for the implementation member
	self->m_implementation = (Channel*)PyObject_Malloc( sizeof( Channel ) );

	if( !self->m_implementation )
	{
		PyErr_SetString( PyExc_RuntimeError, "Failed to allocate memory for implementation object." );

		return -1;
	}

    // Call constructor
	try
	{
		new( self->m_implementation ) Channel( reinterpret_cast<PyObject*>( self ) );
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
	ChannelDealloc( PyChannelObject* self )
{
	if( self->m_implementation )
    {
		// Call destructor
		self->m_implementation->~Channel();

		PyObject_Free( self->m_implementation );
    }

    // Handle weakrefs
    if (self->m_weakrefList != nullptr)
    {
		PyObject_ClearWeakRefs( (PyObject*)self );
    }

    Py_TYPE( self )->tp_free( (PyObject*)self );
}

static bool PyChannelObjectIsValid( PyChannelObject* channel )
{
	if( !channel->m_implementation )
	{
		PyErr_SetString( PyExc_RuntimeError, "Channel object is not valid. Most likely cause being __init__ not called on base type." );

		return false;
	}

	return true;
}

static PyObject*
	ChannelPreferenceGet( PyChannelObject* self, void* closure )
{
	// Ensure PyChannelObject is in a valid state
	if( !PyChannelObjectIsValid( self ) )
	{
		return nullptr;
	}

	return PyLong_FromLong( self->m_implementation->PreferenceAsInt() );
}

static int
	ChannelPreferenceSet( PyChannelObject* self, PyObject* value, void* closure )
{
	// Ensure PyChannelObject is in a valid state
	if( !PyChannelObjectIsValid( self ) )
	{
		return -1;
	}

	if( value == NULL )
	{
		PyErr_SetString( PyExc_TypeError, "Cannot delete the first attribute" );
		return -1;
	}
	if( !PyLong_Check( value ) )
	{
		PyErr_SetString( PyExc_TypeError,
						 "The first attribute value must be a number" );
		return -1;
	}

    long newPreference = PyLong_AsLong( value );

    // Only accept valid values
    // -1   - Prefer receive
    // 0    - Prefer neither
    // 1    - Prefer sender
    if( ( newPreference > -2 ) && ( newPreference < 2 ) )
	{
		self->m_implementation->SetPreferenceFromInt( newPreference );
    }

	return 0;
}

static PyObject*
	ChannelBalanceGet( PyChannelObject* self, void* closure )
{
	// Ensure PyChannelObject is in a valid state
	if( !PyChannelObjectIsValid( self ) )
	{
		return nullptr;
	}

	return PyLong_FromLong( self->m_implementation->Balance() );
}

static PyObject*
	ChannelQueueGet( PyChannelObject* self, void* closure )
{
	// Ensure PyChannelObject is in a valid state
	if( !PyChannelObjectIsValid( self ) )
	{
		return nullptr;
	}

	Tasklet* front = self->m_implementation->BlockedQueueFront();

    if (!front)
    {
		Py_IncRef(Py_None);

		return Py_None;
    }
    else
    {
		PyObject* frontOfQueue = front->PythonObject();

        Py_IncRef( frontOfQueue );

		return frontOfQueue;
    }
}

static PyObject*
	ChannelClosedGet( PyChannelObject* self, void* closure )
{
	// Ensure PyChannelObject is in a valid state
	if( !PyChannelObjectIsValid( self ) )
	{
		return nullptr;
	}

	return self->m_implementation->IsClosed() ? Py_True : Py_False;
}

static PyObject*
	ChannelClosingGet( PyChannelObject* self, void* closure )
{
	// Ensure PyChannelObject is in a valid state
	if( !PyChannelObjectIsValid( self ) )
	{
		return nullptr;
	}

	return self->m_implementation->IsClosing() ? Py_True : Py_False;
}

static PyGetSetDef Channel_getsetters[] = {
	{ "preference",
        (getter)ChannelPreferenceGet,
        (setter)ChannelPreferenceSet,
        "allows for customisation of how the channel actions.",
        NULL },

	{ "balance",
        (getter)ChannelBalanceGet,
        NULL,
        "number of tasklets waiting to send (>0) or receive (<0).",
        NULL },

	{ "queue",
        (getter)ChannelQueueGet,
        NULL,
        "the first tasklet in the chain of tasklets that are blocked on the channel.",
        NULL },

	{ "closed",
        (getter)ChannelClosedGet,
        NULL,
        "The value of this attribute is True when close() has been called and the channel is empty.",
        NULL },

	{ "closing",
        (getter)ChannelClosingGet,
        NULL,
        "The value of this attribute is True when close() has been called.",
        NULL },

	{ NULL } /* Sentinel */
};

static PyObject*
	ChannelSend( PyChannelObject* self, PyObject* args, PyObject* Py_UNUSED( kwds ) )
{
	// Ensure PyChannelObject is in a valid state
	if( !PyChannelObjectIsValid( self ) )
	{
		return nullptr;
	}

	PyObject* value;

	if( !PyArg_ParseTuple( args, "O:Channel.send", &value ) )
	{
		return nullptr;
	}

	if( !self->m_implementation->Send( value ) )
	{
		return nullptr;
	}

    Py_IncRef( Py_None );

	return Py_None;
}

static PyObject*
	ChannelReceive( PyChannelObject* self, PyObject* Py_UNUSED( ignored ) )
{
	// Ensure PyChannelObject is in a valid state
	if( !PyChannelObjectIsValid( self ) )
	{
		return nullptr;
	}

	return self->m_implementation->Receive();
}

static PyObject*
	ChannelSendException( PyChannelObject* self, PyObject* args, PyObject* Py_UNUSED( kwds ) )
{
	// Ensure PyChannelObject is in a valid state
	if( !PyChannelObjectIsValid( self ) )
	{
		return nullptr;
	}

    if (PyTuple_Size(args) < 1)
    {
		PyErr_SetString( PyExc_RuntimeError, "Exception type required" );
		return nullptr;
    }

    PyObject* exception = PyTuple_GetItem(args,0);

    if( !PyExceptionClass_Check( exception ) && !PyObject_IsInstance( exception, PyExc_Exception ) )
    {
		PyErr_SetString( PyExc_RuntimeError, "Exception type or instance required" );
		return nullptr;
    }

    Py_IncRef( exception );

    PyObject* exceptionArguments = nullptr;

    if (PyTuple_Size(args) > 1)
    {
		exceptionArguments = PyTuple_GetSlice( args, 1, PyTuple_Size( args ) );

        // if only one argument was passed, then we want to extract it, and pass it along as is
        if( PyTuple_Size( exceptionArguments ) == 1 )
        {
			auto argument = PyTuple_GetItem( exceptionArguments, 0 );
			Py_IncRef( argument );
			Py_DecRef( exceptionArguments );
			exceptionArguments = argument;
        }
    }
    else
    {
		Py_IncRef( Py_None );
		exceptionArguments = Py_None;
    }

	if( !self->m_implementation->Send( exceptionArguments, exception ) )
	{
		Py_DecRef( exceptionArguments );

		return NULL;
    }

    Py_DecRef( exceptionArguments );

    Py_IncRef( Py_None );

	return Py_None;
}

static PyObject*
	ChannelSendThrow( PyChannelObject* self, PyObject* args, PyObject* kwds )
{
	// Ensure PyChannelObject is in a valid state
	if( !PyChannelObjectIsValid( self ) )
	{
		return nullptr;
	}

	const char* kwlist[] = { "exc", "val", "tb", NULL };

	PyObject* exception = nullptr;
	PyObject* value = Py_None;
	PyObject* tb = Py_None;

	if( !PyArg_ParseTupleAndKeywords( args, kwds, "O|OO:Channel.send_throw", (char**)kwlist, &exception, &value, &tb ) )
	{
		return nullptr;
	}

    /*
    * We are keeping this check around only to adhere to the previous stackless implementation
    * We only rely on the value here, not exception or the tb (traceback) object
    */
	if( !PyExceptionClass_Check( exception ) && !PyObject_IsInstance( exception, PyExc_Exception ) )
	{
		PyErr_SetString( PyExc_TypeError, "Channel.send_throw() argument 'exc' (pos 1) must be an Exception type or instance" );
		return nullptr;
	}

	Py_IncRef( value );
	Py_IncRef( tb );
	Py_IncRef( exception );

    Py_INCREF( Py_None );

    auto exceptionDataTuple = PyTuple_New( 3 );
	PyTuple_SetItem( exceptionDataTuple, 0, exception );
	PyTuple_SetItem( exceptionDataTuple, 1, value );
	PyTuple_SetItem( exceptionDataTuple, 2, tb );

	if( !self->m_implementation->Send( Py_None, exceptionDataTuple, true ) )
	{
		Py_DecRef( exceptionDataTuple );
		return NULL;
	}
    
    Py_IncRef( Py_None );

	return Py_None;
}


static PyObject*
	ChannelIter( PyChannelObject* self )
{
	Py_INCREF( self ); 

	return reinterpret_cast<PyObject*>(self);
}

static PyObject*
	ChannelNext( PyChannelObject* self )
{
    // Run receive until unblocked
    // It is possible that this will raise a nullptr in case of deadlock
    // Doesn't raise a StopIteration error as iteration never really stops
    if (self->m_implementation->IsClosed())
    {
		PyErr_SetString( PyExc_StopIteration, "Channel is closed" );

		return nullptr;
    }

	PyObject* ret = ChannelReceive( self, nullptr );

    if (!ret)
    {
        return nullptr;
    }
    else
    {
		return ret;
    }
}

static PyObject*
	ChannelClearTasklets( PyChannelObject* self, PyObject* Py_UNUSED( ignored ) )
{
	// Ensure PyChannelObject is in a valid state
	if( !PyChannelObjectIsValid( self ) )
	{
		return nullptr;
	}

	self->m_implementation->ClearBlocked( false );

	Py_IncRef( Py_None );

    return Py_None;
}

static PyObject*
	ChannelClose( PyChannelObject* self, PyObject* Py_UNUSED( ignored ) )
{
	// Ensure PyChannelObject is in a valid state
	if( !PyChannelObjectIsValid( self ) )
	{
		return nullptr;
	}

	self->m_implementation->Close();

	Py_IncRef( Py_None );

	return Py_None;
}

static PyObject*
	ChannelOpen( PyChannelObject* self, PyObject* Py_UNUSED( ignored ) )
{
	// Ensure PyChannelObject is in a valid state
	if( !PyChannelObjectIsValid( self ) )
	{
		return nullptr;
	}

	self->m_implementation->Open();

	Py_IncRef( Py_None );

	return Py_None;
}

static PyMethodDef Channel_methods[] = {
	{ "send",
        (PyCFunction)ChannelSend,
        METH_VARARGS,
        "Send an object over the channel. \n\n\
            :param value: Value to send \n\
            :type value: Object" },

	{ "receive",
        (PyCFunction)ChannelReceive,
        METH_NOARGS,
        "Receive an object over the channel. \n\n\
            :return received value" },

	{ "send_exception",
        (PyCFunction)ChannelSendException,
        METH_VARARGS,
        "Send an exception over the channel. \n\n\
            :param exc: Python exception \n\
            :type exc: sub-class of Python exception \n\
            :param args: Arguments to apply to exception \n\
            :type args: Tuple" },

	{ "send_throw",
        (PyCFunction)ChannelSendThrow,
        METH_VARARGS | METH_KEYWORDS,
        "Send an exception over the channel. This function is deprecated! Please use send_exception instead. \n\n\
            :param exc: Python exception \n\
            :type exc: sub-class of Python exception \n\
            :param val: Value to apply to exception \n\
            :type val: Tuple \n\
            :param tb: Traceback \n\
            :type tb: Python Traceback object" },

	{ "clear",
        (PyCFunction)ChannelClearTasklets,
        METH_NOARGS,
        "Clear channel, all blocked tasklets will be killed rasing TaskletExit exception." },

	{ "close",
        (PyCFunction)ChannelClose,
        METH_NOARGS,
        "Prevents the channel queue from growing. If the channel is not empty, the flag closing becomes True. If the channel is empty, the flag closed becomes True." },

	{ "open",
        (PyCFunction)ChannelOpen,
        METH_NOARGS,
        "Reopen a channel." },

	{ NULL } /* Sentinel */
};

static PyTypeObject ChannelType = {
	/* The ob_type field must be initialized in the module init function
     * to be portable to Windows without using C++. */
	PyVarObject_HEAD_INIT( NULL, 0 ) "scheduler.Channel", /*tp_name*/
	sizeof( PyChannelObject ), /*tp_basicsize*/
	0, /*tp_itemsize*/
	/* methods */
	(destructor)ChannelDealloc, /*tp_dealloc*/
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
	PyDoc_STR( "Channel objects" ), /*tp_doc*/
	0, /*tp_traverse*/
	0, /*tp_clear*/
	0, /*tp_richcompare*/
	offsetof( PyChannelObject, m_weakrefList ), /*tp_weaklistoffset*/
	(getiterfunc)ChannelIter, /*tp_iter*/
	(iternextfunc)ChannelNext, /*tp_iternext*/
	Channel_methods, /*tp_methods*/
	0, /*tp_members*/
	Channel_getsetters, /*tp_getset*/
	0,
	/* see PyInit_xx */ /*tp_base*/
	0, /*tp_dict*/
	0, /*tp_descr_get*/
	0, /*tp_descr_set*/
	0, /*tp_dictoffset*/
	(initproc)ChannelInit, /*tp_init*/
	0, /*tp_alloc*/
	ChannelNew, /*tp_new*/
	0, /*tp_free*/
	0, /*tp_is_gc*/
};