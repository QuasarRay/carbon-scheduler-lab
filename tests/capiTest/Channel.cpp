
#include "StdAfx.h"

#include <Python.h>
#include <Scheduler.h>

#include "InterpreterWithSchedulerModule.h"

struct ChannelCapi : public InterpreterWithSchedulerModule{};

    TEST_F( ChannelCapi, PyChannel_New )
    {

	    PyChannelObject* channel = m_api->PyChannel_New( m_api->PyChannelType );

        ASSERT_NE( channel, nullptr );

	    EXPECT_TRUE( m_api->PyChannel_Check( reinterpret_cast<PyObject*>( channel ) ) );
    }

    TEST_F( ChannelCapi, PyChannel_Send )
    {
	    // Test Value
	    long testValue = 101;

	    // Create a channel for use in test
	    PyChannelObject* channel = m_api->PyChannel_New( m_api->PyChannelType );

        EXPECT_NE( channel, nullptr );
		Py_IncRef( reinterpret_cast<PyObject*>( channel ) );

	    // Create a callable which calls PyChannel_Send in c++
		EXPECT_EQ( PyRun_SimpleString( "def send_function(channel,value):\n"
									   "   schedulertest.channel_send(channel,value)\n" ),
				   0 );

	    PyObject* sendCallable = PyObject_GetAttrString( m_mainModule, "send_function" );
		EXPECT_NE( sendCallable, nullptr );
		EXPECT_TRUE( PyCallable_Check( sendCallable ) );

	    // Create tasklet with foo callable
	    PyObject* tasklet_args = PyTuple_New( 1 );
		EXPECT_NE( tasklet_args, nullptr );
		EXPECT_EQ( PyTuple_SetItem( tasklet_args, 0, sendCallable ), 0 );
	    PyTaskletObject* tasklet = m_api->PyTasklet_New( m_api->PyTaskletType, tasklet_args );
		EXPECT_NE( tasklet, nullptr );
	    Py_XDECREF( tasklet_args );

	    // Setup tasklet to bind arguments and add the queue
	    PyObject* callableArgs = PyTuple_New( 2 );
		EXPECT_NE( callableArgs, nullptr );
		EXPECT_EQ( PyTuple_SetItem( callableArgs, 0, reinterpret_cast<PyObject*>( channel ) ), 0 );
		EXPECT_EQ( PyTuple_SetItem( callableArgs, 1, PyLong_FromLong( testValue ) ), 0 );
	    EXPECT_EQ(m_api->PyTasklet_Setup( tasklet, callableArgs, nullptr ), 0);
	    Py_XDECREF( callableArgs );

	    // Check that tasklet was scheduled
	    EXPECT_EQ( m_api->PyScheduler_GetRunCount(), 2 );

	    // Run scheduler (once)
		EXPECT_EQ( m_api->PyScheduler_RunNTasklets( 1 ), Py_None );

	    // Check balance has one waiting to send (1)
	    EXPECT_EQ( m_api->PyChannel_GetBalance( channel ), 1 );

	    // Receive on channel to unblock
	    PyObject* received = m_api->PyChannel_Receive( channel );

        EXPECT_NE( received, nullptr );

	    // Should be a long
	    EXPECT_TRUE( PyLong_Check( received ) );

	    // Should be the same value as the one passed in
	    EXPECT_EQ( PyLong_AsLong( received ), testValue );

	    // Channel balance should reset
	    EXPECT_EQ( m_api->PyChannel_GetBalance( channel ), 0 );

	    // There should be the remaining of send left on the queue
	    EXPECT_EQ( m_api->PyScheduler_GetRunCount(), 2 );

	    // Run scheduler
		EXPECT_EQ( m_api->PyScheduler_RunNTasklets( 1 ), Py_None );

	    // There should be nothing left on the queue but main
	    EXPECT_EQ( m_api->PyScheduler_GetRunCount(), 1 );

	    // Cleanup
	    Py_XDECREF( tasklet );

	    Py_XDECREF( channel );
    }

    TEST_F( ChannelCapi, PyChannel_Send_With_Killed_Tasklet )
	{
		// Test Value
		long testValue = 101;

		// Create a channel for use in test
		PyChannelObject* channel = m_api->PyChannel_New( m_api->PyChannelType );

        EXPECT_NE( channel, nullptr );
		Py_IncRef( reinterpret_cast<PyObject*>( channel ) );

		// Create a callable which calls PyChannel_Send in c++
		EXPECT_EQ( PyRun_SimpleString( "def send_function(channel,value):\n"
									   "   schedulertest.channel_send(channel,value)\n" ),
				   0 );

		PyObject* sendCallable = PyObject_GetAttrString( m_mainModule, "send_function" );
		EXPECT_NE( sendCallable, nullptr );
		EXPECT_TRUE( PyCallable_Check( sendCallable ) );

		// Create tasklet with foo callable
		PyObject* taskletArgs = PyTuple_New( 1 );
		EXPECT_NE( taskletArgs, nullptr );
		EXPECT_EQ( PyTuple_SetItem( taskletArgs, 0, sendCallable ), 0 );
		PyTaskletObject* tasklet = m_api->PyTasklet_New( m_api->PyTaskletType, taskletArgs );
		EXPECT_NE( tasklet, nullptr );
		EXPECT_TRUE( m_api->PyTasklet_Check( reinterpret_cast<PyObject*>(tasklet) ) );
		Py_XDECREF( taskletArgs );

		// Setup tasklet to bind arguments and add the queue
		PyObject* callableArgs = PyTuple_New( 2 );
		EXPECT_NE( callableArgs, nullptr );
		EXPECT_EQ( PyTuple_SetItem( callableArgs, 0, reinterpret_cast<PyObject*>( channel ) ), 0 );
		EXPECT_EQ( PyTuple_SetItem( callableArgs, 1, PyLong_FromLong( testValue ) ), 0 );
		EXPECT_EQ( m_api->PyTasklet_Setup( tasklet, callableArgs, nullptr ), 0 );
		Py_XDECREF( callableArgs );

		// Check that tasklet was scheduled
		EXPECT_EQ( m_api->PyScheduler_GetRunCount(), 2 );

		// Run scheduler (once)
		EXPECT_EQ( m_api->PyScheduler_RunNTasklets( 1 ), Py_None );

        // Check the test value 
        EXPECT_EQ( PyRun_SimpleString( "channel_state_test_value = schedulertest.test_value()\n" ), 0 );

		PyObject* channelStateTestValue = PyObject_GetAttrString( m_mainModule, "channel_state_test_value" );
		EXPECT_NE( channelStateTestValue, nullptr );
		EXPECT_TRUE( PyLong_Check( channelStateTestValue ) );
		EXPECT_EQ( PyLong_AsLong( channelStateTestValue ), 1 ); 
        Py_XDECREF( channelStateTestValue );

        // Kill the tasklet
		EXPECT_EQ( m_api->PyTasklet_Kill( reinterpret_cast<PyTaskletObject*>( tasklet ) ), 0);

        // Check that cleanup occurred
		EXPECT_EQ( PyRun_SimpleString( "channel_state_test_value = schedulertest.test_value()\n" ), 0 );

		channelStateTestValue = PyObject_GetAttrString( m_mainModule, "channel_state_test_value" );
		EXPECT_NE( channelStateTestValue, nullptr );
		EXPECT_TRUE( PyLong_Check( channelStateTestValue ) );
		EXPECT_EQ( PyLong_AsLong( channelStateTestValue ), -1 );
		Py_XDECREF( channelStateTestValue );

		// Cleanup
		Py_DECREF( tasklet );
		Py_XDECREF( channel );
	}

    TEST_F( ChannelCapi, PyChannel_Receive )
    {
	    // Test Value
	    long testValue = 101;

	    // Create channel
	    PyChannelObject* channel = m_api->PyChannel_New( m_api->PyChannelType );

        EXPECT_NE( channel, nullptr );
		Py_IncRef( reinterpret_cast<PyObject*>( channel ) );

	    // Create callable
		EXPECT_EQ( PyRun_SimpleString( "def foo(channel, value):\n"
									   "   channel.send(value)\n" ),
				   0 );

	    PyObject* fooCallable = PyObject_GetAttrString( m_mainModule, "foo" );
		EXPECT_NE( fooCallable, nullptr );
	    EXPECT_TRUE( PyCallable_Check( fooCallable ) );

	    // Create tasklet with foo callable
	    PyObject* taskletArgs = PyTuple_New( 1 );
		EXPECT_NE( taskletArgs, nullptr );
		EXPECT_EQ( PyTuple_SetItem( taskletArgs, 0, fooCallable ), 0 );
	    PyTaskletObject* tasklet = m_api->PyTasklet_New( m_api->PyTaskletType, taskletArgs );
		EXPECT_NE( tasklet, nullptr );
		EXPECT_TRUE( m_api->PyTasklet_Check( reinterpret_cast<PyObject*>( tasklet ) ) );
	    Py_XDECREF( taskletArgs );

	    // Setup tasklet to bind arguments and add the queue
	    PyObject* callableArgs = PyTuple_New( 2 );
		EXPECT_NE( callableArgs, nullptr );
		EXPECT_EQ( PyTuple_SetItem( callableArgs, 0, reinterpret_cast<PyObject*>( channel ) ), 0 );
		EXPECT_EQ( PyTuple_SetItem( callableArgs, 1, PyLong_FromLong( testValue ) ), 0 );
	    EXPECT_EQ( m_api->PyTasklet_Setup( tasklet, callableArgs, nullptr ), 0);
	    Py_XDECREF( callableArgs );

	    // Check that tasklet was scheduled
	    EXPECT_EQ( m_api->PyScheduler_GetRunCount(), 2 );

	    // Run scheduler (once)
		EXPECT_EQ( m_api->PyScheduler_RunNTasklets( 1 ), Py_None );

	    // Check balance has one waiting to send (1)
	    EXPECT_EQ( m_api->PyChannel_GetBalance( channel ), 1 );

	    // Receive on channel to unblock
	    PyObject* received = m_api->PyChannel_Receive( channel );

        EXPECT_NE( received, nullptr );

	    // Should be a long
	    EXPECT_TRUE( PyLong_Check( received ) );

	    // Should be the same value as the one passed in
	    EXPECT_EQ( PyLong_AsLong( received ), testValue );

	    // Channel balance should reset
	    EXPECT_EQ( m_api->PyChannel_GetBalance( channel ), 0 );

	    // There should be the remaining of send left on the queue
	    EXPECT_EQ( m_api->PyScheduler_GetRunCount(), 2 );

	    // Run scheduler
		EXPECT_EQ( m_api->PyScheduler_RunNTasklets( 1 ), Py_None );

	    // There should be nothing left on the queue but main
	    EXPECT_EQ( m_api->PyScheduler_GetRunCount(), 1 );

	    // Cleanup
		Py_XDECREF( received );

	    Py_XDECREF( tasklet );

	    Py_XDECREF( channel );

    }


    TEST_F( ChannelCapi, PyChannel_Receive_With_Killed_Tasklet )
	{

		// Create channel
		PyChannelObject* channel = m_api->PyChannel_New( m_api->PyChannelType );

        EXPECT_NE( channel, nullptr );
		Py_IncRef( reinterpret_cast<PyObject*>( channel ) );

        // Set channel preference to prefer sender
		m_api->PyChannel_SetPreference( channel, 1 );

		// Create callable
		EXPECT_EQ( PyRun_SimpleString( "def foo(channel):\n"
									   "   value = schedulertest.channel_receive(channel)\n" ),
				   0 );

		PyObject* fooCallable = PyObject_GetAttrString( m_mainModule, "foo" );
		EXPECT_NE( fooCallable, nullptr );
		EXPECT_TRUE( PyCallable_Check( fooCallable ) );

		// Create tasklet with foo callable
		PyObject* taskletArgs = PyTuple_New( 1 );
		EXPECT_NE( taskletArgs, nullptr );
		EXPECT_EQ( PyTuple_SetItem( taskletArgs, 0, fooCallable ), 0 );
		PyTaskletObject* tasklet = m_api->PyTasklet_New( m_api->PyTaskletType, taskletArgs );
		EXPECT_NE( tasklet, nullptr );
		EXPECT_TRUE(m_api->PyTasklet_Check(reinterpret_cast<PyObject*>(tasklet)));
		Py_XDECREF( taskletArgs );

		// Setup tasklet to bind arguments and add the queue
		PyObject* callableArgs = PyTuple_New( 1 );
		EXPECT_NE( callableArgs, nullptr );
		EXPECT_EQ( PyTuple_SetItem( callableArgs, 0, reinterpret_cast<PyObject*>( channel ) ), 0 );
		EXPECT_EQ(m_api->PyTasklet_Setup( tasklet, callableArgs, nullptr ),0);
		Py_XDECREF( callableArgs );

		// Check that tasklet was scheduled
		EXPECT_EQ( m_api->PyScheduler_GetRunCount(), 2 );

		// Run scheduler (once)
		EXPECT_EQ( m_api->PyScheduler_RunNTasklets( 1 ), Py_None );

		// Check balance has one waiting to send (1)
		EXPECT_EQ( m_api->PyChannel_GetBalance( channel ), -1 );

        // Check the test value
		EXPECT_EQ( PyRun_SimpleString( "channel_state_test_value = schedulertest.test_value()\n" ), 0 );

		PyObject* channelStateTestValue = PyObject_GetAttrString( m_mainModule, "channel_state_test_value" );
		EXPECT_NE( channelStateTestValue, nullptr );
		EXPECT_TRUE( PyLong_Check( channelStateTestValue ) );
		EXPECT_EQ( PyLong_AsLong( channelStateTestValue ), 1 );
		Py_XDECREF( channelStateTestValue );

		// Kill the tasklet
		EXPECT_EQ( m_api->PyTasklet_Kill( reinterpret_cast<PyTaskletObject*>( tasklet ) ), 0);

		// Check that cleanup occurred
		EXPECT_EQ( PyRun_SimpleString( "channel_state_test_value = schedulertest.test_value()\n" ), 0 );

		channelStateTestValue = PyObject_GetAttrString( m_mainModule, "channel_state_test_value" );
		EXPECT_NE( channelStateTestValue, nullptr );
		EXPECT_TRUE( PyLong_Check( channelStateTestValue ) );
		EXPECT_EQ( PyLong_AsLong( channelStateTestValue ), -1 );
		Py_XDECREF( channelStateTestValue );

		// Cleanup
		Py_XDECREF( tasklet );

		Py_XDECREF( channel );
	}


    TEST_F( ChannelCapi, PyChannel_SendException )
    {
	    // Create a channel for use in test
		EXPECT_EQ( PyRun_SimpleString( "channel = scheduler.channel()\n" ), 0 );

	    // Create callable which sends an exception over a channel
		EXPECT_EQ( PyRun_SimpleString( "def foo():\n"
									   "   schedulertest.send_exception(channel, ValueError, (1,2,3))\n" ),
				   0 );

	    // Create a tasklet and run
		EXPECT_EQ( PyRun_SimpleString( "scheduler.tasklet(foo)()\n"
									   "scheduler.run()\n" ),
				   0 );

	    // Get channel
	    PyObject* channel = PyObject_GetAttrString( m_mainModule, "channel" );
		EXPECT_NE( channel, nullptr );
	    EXPECT_TRUE( m_api->PyChannel_Check( channel ) );

	    // Attempt to receive on channel
		EXPECT_EQ( m_api->PyChannel_Receive( reinterpret_cast<PyChannelObject*>( channel ) ), nullptr );

	    // Check error has been raised
	    PyObject* errorType = PyErr_Occurred();

	    // Should be of type value error
	    EXPECT_EQ( errorType, PyExc_ValueError );

	    // Clear the error
	    PyErr_Clear();

	    Py_XDECREF( channel );
    }

    //NOTE: failure due to channel queue not yet implemented
    TEST_F( ChannelCapi, PyChannel_GetQueue )
    {

	    // Create channel in python
		EXPECT_EQ( PyRun_SimpleString( "send_channel = scheduler.channel()\n" ), 0 );

	    PyObject* sendChannel = PyObject_GetAttrString( m_mainModule, "send_channel" );
		EXPECT_NE( sendChannel, nullptr );
	    EXPECT_TRUE( m_api->PyChannel_Check( sendChannel ) );

	    // Create blocking function
		EXPECT_EQ( PyRun_SimpleString( "def send_block():\n"
									   "   send_channel.send(1)\n" ),
				   0 );

	    // Create and run tasklet to block on send on channel
		EXPECT_EQ( PyRun_SimpleString( "send_tasklet = scheduler.tasklet(send_block)()\n"
									   "scheduler.run()\n" ),
				   0 );

	    PyObject* blockedTasklet = m_api->PyChannel_GetQueue( reinterpret_cast<PyChannelObject*>( sendChannel ) );
		EXPECT_NE( blockedTasklet, nullptr );
	    EXPECT_TRUE( m_api->PyTasklet_Check( blockedTasklet ) );

	    // Check the tasklet matches expected
	    PyObject* sendTasklet = PyObject_GetAttrString( m_mainModule, "send_tasklet" );
		EXPECT_NE( sendTasklet, nullptr );
	    EXPECT_EQ( blockedTasklet, sendTasklet );

	    Py_XDECREF( sendChannel );
	    Py_XDECREF( sendTasklet );
    }

    TEST_F( ChannelCapi, PyChannel_SetPreference )
    {
	    PyChannelObject* channel = m_api->PyChannel_New( m_api->PyChannelType );

        EXPECT_NE( channel, nullptr );

	    // Check default - prefer receiver -1
	    EXPECT_EQ( m_api->PyChannel_GetPreference( channel ), -1 );

	    // Set prefer neither
	    m_api->PyChannel_SetPreference( channel, 0 );

	    EXPECT_EQ( m_api->PyChannel_GetPreference( channel ), 0 );

	    // Set prefer sender
	    m_api->PyChannel_SetPreference( channel, 1 );

	    EXPECT_EQ( m_api->PyChannel_GetPreference( channel ), 1 );

	    // Check out of bounds values
	    m_api->PyChannel_SetPreference( channel, -2 );

	    EXPECT_EQ( m_api->PyChannel_GetPreference( channel ), -1 );

	    m_api->PyChannel_SetPreference( channel, 2 );

	    EXPECT_EQ( m_api->PyChannel_GetPreference( channel ), 1 );

	    Py_XDECREF( channel );
    }

    TEST_F( ChannelCapi, PyChannel_GetBalance )
    {
	    // Create channel in python
		EXPECT_EQ( PyRun_SimpleString( "send_channel = scheduler.channel()\n" ), 0 );

	    PyObject* sendChannel = PyObject_GetAttrString( m_mainModule, "send_channel" );
		EXPECT_NE( sendChannel, nullptr );

	    EXPECT_TRUE( m_api->PyChannel_Check( sendChannel ) );

	    // Check default
	    EXPECT_EQ( m_api->PyChannel_GetBalance( reinterpret_cast<PyChannelObject*>( sendChannel ) ), 0 );

	    // Create blocking function
		EXPECT_EQ( PyRun_SimpleString( "def send_block():\n"
									   "   send_channel.send(1)\n" ),
				   0 );

	    // Create and run tasklet to block on send on channel
		EXPECT_EQ( PyRun_SimpleString( "scheduler.tasklet(send_block)()\n"
									   "scheduler.run()\n" ),
				   0 );

	    // Balance with one blocking send
	    EXPECT_EQ( m_api->PyChannel_GetBalance( reinterpret_cast<PyChannelObject*>( sendChannel ) ), 1 );

	    Py_XDECREF( sendChannel );

	    // Check blocking receive
		EXPECT_EQ( PyRun_SimpleString( "receive_channel = scheduler.channel()\n"
									   "receive_channel.preference = 1\n" ),
				   0 );

	    PyObject* receiveChannel = PyObject_GetAttrString( m_mainModule, "receive_channel" );
		EXPECT_NE( receiveChannel, nullptr );

	    EXPECT_TRUE( m_api->PyChannel_Check( receiveChannel ) );

	    // Check default
	    EXPECT_EQ( m_api->PyChannel_GetBalance( reinterpret_cast<PyChannelObject*>( receiveChannel ) ), 0 );

	    // Create blocking function
		EXPECT_EQ( PyRun_SimpleString( "def receive_block():\n"
									   "   receive_channel.receive()\n" ),
				   0 );

	    // Create and run tasklet to block on send on channel
		EXPECT_EQ( PyRun_SimpleString( "scheduler.tasklet(receive_block)()\n"
									   "scheduler.run()\n" ),
				   0 );

	    // Balance with one blocking send
	    EXPECT_EQ( m_api->PyChannel_GetBalance( reinterpret_cast<PyChannelObject*>( receiveChannel ) ), -1 );

	    Py_XDECREF( receiveChannel );
    }

    TEST_F( ChannelCapi, PyChannel_Check )
    {
	    PyChannelObject* channel = m_api->PyChannel_New( m_api->PyChannelType );

        EXPECT_NE( channel, nullptr );

	    EXPECT_TRUE( m_api->PyChannel_Check( reinterpret_cast<PyObject*>( channel ) ) );

	    EXPECT_FALSE( m_api->PyChannel_Check( nullptr ) );

	    EXPECT_FALSE( m_api->PyChannel_Check( m_schedulerModule ) );

	    Py_XDECREF( channel );
    }

    TEST_F( ChannelCapi, PyChannel_SendThrow )
	{
		PyChannelObject* channel = m_api->PyChannel_New( m_api->PyChannelType );

		EXPECT_NE( channel, nullptr );
		Py_IncRef( reinterpret_cast<PyObject*>( channel ) );

        // Create test scenario to which calls send_throw through capi
		EXPECT_EQ( PyRun_SimpleString( "import sys\n"
                                       "def foo(testChannel):\n"
									   "    try:\n"
									   "        raise ValueError(1,2,3)\n"
									   "    except Exception:\n"
									   "        schedulertest.channel_send_throw(testChannel, *sys.exc_info())\n" ),
				   0 );

        // Get reference to callable
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
		EXPECT_EQ( PyTuple_SetItem( callableArgs, 0, reinterpret_cast<PyObject*>(channel) ), 0 );
		EXPECT_EQ( m_api->PyTasklet_Setup( tasklet, callableArgs, nullptr ), 0 );
		Py_XDECREF( callableArgs );
		
		// Should be added to queue
		EXPECT_EQ( m_api->PyScheduler_GetRunCount(), 2 );
		
		// Run scheduler to run tasklet
		EXPECT_EQ( m_api->PyScheduler_RunNTasklets( 1 ), Py_None );
		
        // At this point the tasklet should be blocked on send
		EXPECT_EQ( m_api->PyChannel_GetBalance( channel ), 1 );
		
        // Attempt receive which should return an error state
		EXPECT_EQ( m_api->PyChannel_Receive( channel ), nullptr );
		
        PyObject* exc = PyErr_GetRaisedException();

        // Error should exist
        EXPECT_NE( exc, nullptr );

        // Value error expected
		EXPECT_EQ( PyObject_IsInstance(exc, PyExc_ValueError), 1 );

        // Clear error
		PyErr_Clear();

        // Finish send tasklet
		EXPECT_EQ( m_api->PyScheduler_RunNTasklets( 1 ), Py_None );

        // Expect nothing in the queue
		EXPECT_EQ( m_api->PyScheduler_GetRunCount(), 1 );

        // Expect nothing blocked on the channel
		EXPECT_EQ( m_api->PyChannel_GetBalance( channel ), 0 );

		Py_DecRef( reinterpret_cast<PyObject*>( channel ) );
	}

    TEST_F( ChannelCapi, PyChannel_SendThrow_NoValueOrTb )
	{
		PyChannelObject* channel = m_api->PyChannel_New( m_api->PyChannelType );

		EXPECT_NE( channel, nullptr );
		Py_IncRef( reinterpret_cast<PyObject*>( channel ) );

		// Create test scenario to which calls send_throw through capi
		EXPECT_EQ( PyRun_SimpleString( "import sys\n"
									   "def foo(testChannel):\n"
									   "    schedulertest.channel_send_throw(testChannel, ValueError)\n" ),
				   0 );

		// Get reference to callable
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
		EXPECT_EQ( PyTuple_SetItem( callableArgs, 0, reinterpret_cast<PyObject*>( channel ) ), 0 );
		EXPECT_EQ( m_api->PyTasklet_Setup( tasklet, callableArgs, nullptr ), 0 );
		Py_XDECREF( callableArgs );

		// Should be added to queue
		EXPECT_EQ( m_api->PyScheduler_GetRunCount(), 2 );

		// Run scheduler to run tasklet
		EXPECT_EQ( m_api->PyScheduler_RunNTasklets( 1 ), Py_None );

		// At this point the tasklet should be blocked on send
		EXPECT_EQ( m_api->PyChannel_GetBalance( channel ), 1 );

		// Attempt receive which should return an error state
		EXPECT_EQ( m_api->PyChannel_Receive( channel ), nullptr );

		PyObject* exc = PyErr_GetRaisedException();

		// Error should exist
		EXPECT_NE( exc, nullptr );

		// Value error expected
		EXPECT_EQ( PyObject_IsInstance( exc, PyExc_ValueError ), 1 );

		// Clear error
		PyErr_Clear();

		// Finish send tasklet
		EXPECT_EQ( m_api->PyScheduler_RunNTasklets( 1 ), Py_None );

		// Expect nothing in the queue
		EXPECT_EQ( m_api->PyScheduler_GetRunCount(), 1 );

		// Expect nothing blocked on the channel
		EXPECT_EQ( m_api->PyChannel_GetBalance( channel ), 0 );
		Py_DecRef( reinterpret_cast<PyObject*>( channel ) );
	}
