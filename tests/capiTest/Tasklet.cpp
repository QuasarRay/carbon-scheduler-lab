
#include "StdAfx.h"

#include <Python.h>
#include <Scheduler.h>

#include "InterpreterWithSchedulerModule.h"

struct TaskletCapi : public InterpreterWithSchedulerModule{};


TEST_F( TaskletCapi, PyTasklet_New )
{
	// Create callable
	EXPECT_EQ( PyRun_SimpleString( "def foo():\n"
								   "   print(\"bar\")\n" ),
			   0 );
	PyObject* fooCallable = PyObject_GetAttrString( m_mainModule, "foo" );
	EXPECT_NE( fooCallable, nullptr );
	EXPECT_TRUE( PyCallable_Check( fooCallable ) );

    // Create tasklet
    PyObject* taskletArgs = PyTuple_New( 1 );
	EXPECT_NE( taskletArgs, nullptr );
	EXPECT_EQ(PyTuple_SetItem( taskletArgs, 0, fooCallable ),0);
	PyTaskletObject* tasklet = m_api->PyTasklet_New( m_api->PyTaskletType, taskletArgs );
	EXPECT_NE( tasklet, nullptr );

    // Check type
    EXPECT_TRUE( m_api->PyTasklet_Check( reinterpret_cast<PyObject*>( tasklet ) ) );

    // Clean
	Py_XDECREF( tasklet );
    Py_XDECREF( taskletArgs );
	Py_XDECREF( fooCallable );

}

TEST_F( TaskletCapi, PyTasklet_Setup )
{
	long testValue = 101;

    // Create test value container
	EXPECT_EQ( PyRun_SimpleString( "testValue = [0]\n" ), 0 );

	// Create callable
	EXPECT_EQ( PyRun_SimpleString( "def foo(x):\n"
								   "   testValue[0] = x\n" ),
			   0 );
	PyObject* fooCallable = PyObject_GetAttrString( m_mainModule, "foo" );
	EXPECT_NE( fooCallable, nullptr );
	EXPECT_TRUE( PyCallable_Check( fooCallable ) );

	// Create tasklet
	PyObject* taskletArgs = PyTuple_New( 1 );
	EXPECT_NE( taskletArgs, nullptr );
	EXPECT_EQ( PyTuple_SetItem( taskletArgs, 0, fooCallable ), 0 );
	PyTaskletObject* tasklet = m_api->PyTasklet_New( m_api->PyTaskletType, taskletArgs );
	EXPECT_NE( tasklet, nullptr );

	// Check type
	EXPECT_TRUE( m_api->PyTasklet_Check( reinterpret_cast<PyObject*>( tasklet ) ) );

    // Should not be added to queue yet
    EXPECT_EQ( m_api->PyScheduler_GetRunCount(), 1 );

    // Setup tasklet
	PyObject* callableArgs = PyTuple_New( 1 );
	EXPECT_NE( callableArgs, nullptr );
	EXPECT_EQ( PyTuple_SetItem( callableArgs, 0, PyLong_FromLong( testValue ) ), 0 );
	EXPECT_EQ( m_api->PyTasklet_Setup( tasklet, callableArgs, nullptr ), 0 );
	Py_XDECREF( callableArgs );

    // Should be added to queue
    EXPECT_EQ( m_api->PyScheduler_GetRunCount(), 2 );

    // Run scheduler to run tasklet
	EXPECT_EQ( m_api->PyScheduler_RunNTasklets( 1 ), Py_None);

    // Should only be main tasklet remaining
    EXPECT_EQ( m_api->PyScheduler_GetRunCount(), 1 );

    // Retreive test value to check argument was setup correctly
	PyObject* pythonTestValueList = PyObject_GetAttrString( m_mainModule, "testValue" );
	EXPECT_NE( pythonTestValueList, nullptr );
	EXPECT_TRUE( PyList_Check( pythonTestValueList ) );
	PyObject* pythonTestValue = PyList_GetItem( pythonTestValueList, 0 );
	EXPECT_NE( pythonTestValue, nullptr );
	EXPECT_TRUE( PyLong_Check( pythonTestValue ) );
	EXPECT_EQ( PyLong_AsLong( pythonTestValue ), testValue );
	Py_XDECREF( pythonTestValueList );
    
	// Clean
	Py_XDECREF( tasklet );
	Py_XDECREF( taskletArgs );
	Py_XDECREF( fooCallable );
}

TEST_F( TaskletCapi, PyTasklet_Setup_ReferenceCount )
{
	// Create callable
	EXPECT_EQ( PyRun_SimpleString( "def foo():\n"
								   "   pass\n" ),
			   0 );
	PyObject* fooCallable = PyObject_GetAttrString( m_mainModule, "foo" );
	EXPECT_NE( fooCallable, nullptr );
	EXPECT_TRUE( PyCallable_Check( fooCallable ) );
	
	// Create tasklet
	PyObject* taskletArgs = PyTuple_New( 1 );
	EXPECT_NE( taskletArgs, nullptr );
	EXPECT_EQ( PyTuple_SetItem( taskletArgs, 0, fooCallable ), 0 );
	PyTaskletObject* tasklet = m_api->PyTasklet_New( m_api->PyTaskletType, taskletArgs );
	EXPECT_NE( tasklet, nullptr );

	// Setup tasklet twice. Check refcounts.
	PyObject* callableArgs = PyTuple_New( 0 );
	EXPECT_NE( callableArgs, nullptr );
	EXPECT_EQ( Py_REFCNT(tasklet), 1);
	EXPECT_EQ( m_api->PyTasklet_Setup( tasklet, callableArgs, nullptr ), 0 );
	EXPECT_EQ( Py_REFCNT(tasklet), 2); // We got rescheduled, so reference count should increase by 1.

    // we expect PyTasklet_Setup to fail with an exception if called twice in a row
    EXPECT_EQ( m_api->PyTasklet_Setup( tasklet, callableArgs, nullptr ), -1 );
	EXPECT_EQ( Py_REFCNT( tasklet ), 2 ); // Reference count should not have increased.
    EXPECT_NE( PyErr_Occurred(), nullptr);
	PyErr_Clear();

	// Kill the tasklet. The tasklet is no longer scheduled, so reference count should have decreased.
	EXPECT_EQ(m_api->PyTasklet_Kill(tasklet), 0);
	EXPECT_EQ( Py_REFCNT(tasklet), 1);

	// Clean
	Py_DECREF(fooCallable);
	Py_DECREF(taskletArgs);
	Py_DECREF(tasklet);
	Py_DECREF(callableArgs);
}

TEST_F( TaskletCapi, PyTasklet_Insert )
{
    // Create a test value
	EXPECT_EQ( PyRun_SimpleString( "testValue = [0]\n" ), 0 );

	// Create callable which schedule removes a tasklet
	EXPECT_EQ( PyRun_SimpleString( "def foo():\n"
								   "   scheduler.schedule_remove()\n"
								   "   testValue[0] = 1\n" ),
			   0 );

    // Create tasklets and run tasklet
	EXPECT_EQ( PyRun_SimpleString( "tasklet = scheduler.tasklet(foo)()\n"
								   "scheduler.run()\n" ),
			   0 );

    // test value should be unchanged
	PyObject* pythonTestValueList = PyObject_GetAttrString( m_mainModule, "testValue" );
	EXPECT_NE( pythonTestValueList, nullptr );
	EXPECT_TRUE( PyList_Check( pythonTestValueList ) );
	PyObject* pythonTestValue = PyList_GetItem( pythonTestValueList, 0 );
	EXPECT_NE( pythonTestValue, nullptr );
	EXPECT_TRUE( PyLong_Check( pythonTestValue ) );
	EXPECT_EQ( PyLong_AsLong( pythonTestValue ), 0 );
	Py_XDECREF( pythonTestValueList );

    // Tasklet is now alive and removed from queue
	PyObject* tasklet = PyObject_GetAttrString( m_mainModule, "tasklet" );
	EXPECT_NE( tasklet, nullptr );
	EXPECT_TRUE( m_api->PyTasklet_Check( tasklet ) );

    // Now insert the tasklet back into the queue
	EXPECT_EQ( m_api->PyTasklet_Insert( reinterpret_cast<PyTaskletObject*>( tasklet ) ), 0);

    // Queue should now show tasklet has been added
	EXPECT_EQ( m_api->PyScheduler_GetRunCount(), 2 );

    // Run the queue
	EXPECT_EQ( PyRun_SimpleString( "scheduler.run()\n" ), 0 );

    // All tasklets should have run
    EXPECT_EQ( m_api->PyScheduler_GetRunCount(), 1 );

    // Test value should now be set to 1
	pythonTestValueList = PyObject_GetAttrString( m_mainModule, "testValue" );
	EXPECT_NE( pythonTestValueList, nullptr );
	EXPECT_TRUE( PyList_Check( pythonTestValueList ) );
	pythonTestValue = PyList_GetItem( pythonTestValueList, 0 );
	EXPECT_NE( pythonTestValue, nullptr );
	EXPECT_TRUE( PyLong_Check( pythonTestValue ) );
	EXPECT_EQ( PyLong_AsLong( pythonTestValue ), 1 );
	Py_XDECREF( pythonTestValueList );

    // Test adding in dead tasklet
	EXPECT_EQ( m_api->PyTasklet_Alive( reinterpret_cast<PyTaskletObject*>( tasklet ) ), 0 );

    EXPECT_EQ( m_api->PyTasklet_Insert( reinterpret_cast<PyTaskletObject*>( tasklet ) ), -1 );

    // Clean
	Py_XDECREF( tasklet );
}

TEST_F( TaskletCapi, PyTasklet_Check )
{
    // Create a callable
	EXPECT_EQ( PyRun_SimpleString( "def foo(x):\n"
								   "   testValue[0] = x\n" ),
			   0 );
	PyObject* fooCallable = PyObject_GetAttrString( m_mainModule, "foo" );
	EXPECT_NE( fooCallable, nullptr );
	EXPECT_TRUE( PyCallable_Check( fooCallable ) );

    PyObject* taskletArgs = PyTuple_New( 1 );
	EXPECT_NE( taskletArgs, nullptr );
	EXPECT_EQ( PyTuple_SetItem( taskletArgs, 0, fooCallable ), 0 );
	PyTaskletObject* tasklet = m_api->PyTasklet_New( m_api->PyTaskletType, taskletArgs );
	EXPECT_NE( tasklet, nullptr );
	Py_XDECREF( taskletArgs );

	EXPECT_TRUE( m_api->PyTasklet_Check( reinterpret_cast<PyObject*>( tasklet ) ) );

	EXPECT_FALSE( m_api->PyTasklet_Check( nullptr ) );

	EXPECT_FALSE( m_api->PyTasklet_Check( m_schedulerModule ) );

    Py_XDECREF( tasklet );
	Py_XDECREF( fooCallable );
}

TEST_F( TaskletCapi, PyTasklet_GetBlockTrap )
{
    // Create a tasklet
	EXPECT_EQ( PyRun_SimpleString( "tasklet = scheduler.tasklet(lambda: None)\n" ), 0 );
	PyObject* tasklet = PyObject_GetAttrString( m_mainModule, "tasklet" );
	EXPECT_NE( tasklet, nullptr );
	EXPECT_TRUE( m_api->PyTasklet_Check( tasklet ) );
	
    // Check default blocktrap
	EXPECT_EQ( m_api->PyTasklet_GetBlockTrap( reinterpret_cast<PyTaskletObject*>(tasklet) ), 0 );

    EXPECT_EQ( PyRun_SimpleString( "tasklet.block_trap = True\n" ), 0 );

    // Check default blocktrap
	EXPECT_EQ( m_api->PyTasklet_GetBlockTrap( reinterpret_cast<PyTaskletObject*>( tasklet ) ), 1 );

    Py_XDECREF( tasklet );

}

TEST_F( TaskletCapi, PyTasklet_IsMain )
{
	PyObject* mainTasklet = m_api->PyScheduler_GetCurrent();

    EXPECT_NE( mainTasklet, nullptr );

    EXPECT_TRUE( m_api->PyTasklet_Check( mainTasklet ) );

    EXPECT_TRUE( m_api->PyTasklet_IsMain( reinterpret_cast<PyTaskletObject*>(mainTasklet) ) );

    Py_DecRef( mainTasklet );
	
    // Create tasklet
	EXPECT_EQ( PyRun_SimpleString( "tasklet = scheduler.tasklet(lambda: None)\n" ), 0 );
	PyObject* tasklet = PyObject_GetAttrString( m_mainModule, "tasklet" );
	EXPECT_NE( tasklet, nullptr );
	EXPECT_TRUE( m_api->PyTasklet_Check( tasklet ) );
    EXPECT_FALSE( m_api->PyTasklet_IsMain( reinterpret_cast<PyTaskletObject*>( tasklet ) ) );
    
    EXPECT_EQ( PyRun_SimpleString( "tasklet = None\n" ), 0 );
	Py_XDECREF( tasklet );
    
}

TEST_F( TaskletCapi, PyTasklet_Alive )
{

	EXPECT_EQ( PyRun_SimpleString( "tasklet = scheduler.tasklet(lambda: None)()\n" ), 0 );
	PyObject* tasklet = PyObject_GetAttrString( m_mainModule, "tasklet" );
	EXPECT_NE( tasklet, nullptr );
	EXPECT_TRUE( m_api->PyTasklet_Check( tasklet ) );

    // Tasklet should be alive as it hasn't been run yet
    EXPECT_EQ( m_api->PyTasklet_Alive( reinterpret_cast<PyTaskletObject*>( tasklet ) ), 1 );

    // Run Queue
	EXPECT_EQ( PyRun_SimpleString( "scheduler.run()\n" ), 0 );

    // Tasklet should be dead
    EXPECT_EQ( m_api->PyTasklet_Alive( reinterpret_cast<PyTaskletObject*>( tasklet ) ), 0 );

    // Clean
	Py_XDECREF( tasklet );

}

TEST_F( TaskletCapi, PyTasklet_Kill )
{
	EXPECT_EQ( PyRun_SimpleString( "tasklet = scheduler.tasklet(lambda: None)()\n" ), 0 );
	PyObject* tasklet = PyObject_GetAttrString( m_mainModule, "tasklet" );
	EXPECT_NE( tasklet, nullptr );
	EXPECT_TRUE( m_api->PyTasklet_Check( tasklet ) );

    // Check tasklet was added to run queue
	EXPECT_EQ( m_api->PyScheduler_GetRunCount(), 2 );

    // Kill Tasklet
    EXPECT_EQ( m_api->PyTasklet_Kill( reinterpret_cast<PyTaskletObject*>( tasklet ) ), 0);

    // Check tasklet was removed from queue
	EXPECT_EQ( m_api->PyScheduler_GetRunCount(), 1 );

    // Clean
	Py_XDECREF( tasklet );
}