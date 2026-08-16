import unittest
import contextlib
import test_utils
import scheduler

@contextlib.contextmanager
def switch_trapped():
    scheduler.switch_trap(1)
    try:
        yield
    finally:
        scheduler.switch_trap(-1)


class TestCAPIExposure(unittest.TestCase):
    def test_has_capi_attribute(self):
        self.assertTrue(hasattr(scheduler, "_C_API"))

class TestTaskletRunOrderBase(object):
    
    def test_tasklet_run_order(self):
        completedSendTasklets = [""]

        def tasklet_callable(x):
            completedSendTasklets[0] += "t" + str(x)

        t1 = scheduler.tasklet(tasklet_callable)(1)
        scheduler.tasklet(tasklet_callable)(2)
        scheduler.tasklet(tasklet_callable)(3)

        self.assertEqual(self.getruncount(), 4)

        t1.run()

        self.assertEqual(self.getruncount(), 1)

        self.assertEqual(completedSendTasklets[0],"t1t2t3")

    def test_tasklet_run_order_2(self):
        completedSendTasklets = [""]

        def tasklet_callable(x):
            completedSendTasklets[0] += "t" + str(x)

        t1 = scheduler.tasklet(tasklet_callable)(1)
        t2 = scheduler.tasklet(tasklet_callable)(2)
        scheduler.tasklet(tasklet_callable)(3)

        self.assertEqual(self.getruncount(), 4)

        t2.run()

        # This will be different without nested tasklets
        # T2 will be rescheduled to the front then the queue will run
        # This will include then t1.
        if scheduler.get_use_nested_tasklets() == True:
            self.assertEqual(self.getruncount(), 2)

            t1.run()

            self.assertEqual(self.getruncount(), 1)

        if scheduler.get_use_nested_tasklets() == True:
            self.assertEqual(completedSendTasklets[0],"t2t3t1")
        else:
            self.assertEqual(completedSendTasklets[0],"t2t1t3")

class TestTaskletRunOrderBaseWithNestedTasklets(test_utils.SchedulerTestCaseBase, 
                                                TestTaskletRunOrderBase):
    pass

class TestTaskletRunOrderBaseWithoutNestedTasklets(test_utils.SchedulerTestCaseBase, 
                                                   TestTaskletRunOrderBase, 
                                                   test_utils.TestNoNestedTasklets):
    pass

class TestScheduleOrderBase(object):

    def test_scheduler_run_order(self):
        completedSendTasklets = [""]

        def tasklet_callable(x):
            completedSendTasklets[0] += "t" + str(x)

        scheduler.tasklet(tasklet_callable)(1)
        scheduler.tasklet(tasklet_callable)(2)
        scheduler.tasklet(tasklet_callable)(3)

        self.assertEqual(self.getruncount(), 4)

        scheduler.run()

        self.assertEqual(self.getruncount(), 1)

        self.assertEqual(completedSendTasklets[0],"t1t2t3")

    def test_nested_tasklet_run_order(self):
        completedSendTasklets = [""]

        def tasklet_callable(x):
            completedSendTasklets[0] += "t" + str(x)

        def create_nested_tasklet_run():
            t2 = scheduler.tasklet(tasklet_callable)(2)
            scheduler.tasklet(tasklet_callable)(3)
            scheduler.tasklet(tasklet_callable)(4)
            t2.run()

        scheduler.tasklet(tasklet_callable)(1)
        scheduler.tasklet(create_nested_tasklet_run)()
        scheduler.tasklet(tasklet_callable)(5)

        self.assertEqual(self.getruncount(), 4)

        self.run_scheduler()

        self.assertEqual(self.getruncount(), 1)
        if scheduler.get_use_nested_tasklets() == True:
            self.assertEqual(completedSendTasklets[0],"t1t2t3t4t5")
        else:
            self.assertEqual(completedSendTasklets[0],"t1t2t5t3t4")


    def test_nested_tasklet_run_order_with_schedule(self):
        completedSendTasklets = [""]

        def tasklet_callable(x):
            completedSendTasklets[0] += "t" + str(x)

        def schedule():
            scheduler.schedule()

        def create_nested_tasklet_run():
            t2 = scheduler.tasklet(tasklet_callable)(2)
            scheduler.tasklet(schedule)()
            scheduler.tasklet(tasklet_callable)(3)
            t2.run()

        scheduler.tasklet(tasklet_callable)(1)
        scheduler.tasklet(create_nested_tasklet_run)()
        scheduler.tasklet(tasklet_callable)(4)

        self.assertEqual(self.getruncount(), 4)

        self.run_scheduler()

        self.assertEqual(self.getruncount(), 1)

        if scheduler.get_use_nested_tasklets() == True:
            self.assertEqual(completedSendTasklets[0],"t1t2t3t4")
        else:
            self.assertEqual(completedSendTasklets[0],"t1t2t4t3")


    def test_multi_level_nested_tasklet_run_order_with_schedule(self):
        completedSendTasklets = [""]

        def tasklet_callable(x):
            completedSendTasklets[0] += "t" + str(x)

        def schedule():
            scheduler.schedule()

        def create_nested_tasklet_run_2():
            t2 = scheduler.tasklet(tasklet_callable)(3)
            scheduler.tasklet(schedule)()
            scheduler.tasklet(tasklet_callable)(4)
            t2.run()

        def create_nested_tasklet_run():
            t2 = scheduler.tasklet(tasklet_callable)(2)
            scheduler.tasklet(schedule)()
            scheduler.tasklet(create_nested_tasklet_run_2)()
            scheduler.tasklet(tasklet_callable)(5)
            t2.run()

        scheduler.tasklet(tasklet_callable)(1)
        scheduler.tasklet(create_nested_tasklet_run)()
        scheduler.tasklet(tasklet_callable)(6)

        self.assertEqual(self.getruncount(), 4)

        self.run_scheduler()

        self.assertEqual(self.getruncount(), 1)

        if scheduler.get_use_nested_tasklets() == True:
            self.assertEqual(completedSendTasklets[0],"t1t2t3t4t5t6")
        else:
            self.assertEqual(completedSendTasklets[0],"t1t2t6t3t5t4")

    def test_channel_usage_schedule_order_preference_receiver(self):

        completedTasklets = []
        testValue = "TEST_VALUE"

        c = scheduler.channel()

        c.preference = -1

        def sending_tasklet_callable(valueToSend):
            c.send(valueToSend)

        def receiving_tasklet_callable(expectedValue):
            self.assertEqual(expectedValue, c.receive())

        main = scheduler.getmain()
        sendingTasklet = scheduler.tasklet(sending_tasklet_callable)(testValue)
        receivingTasklet = scheduler.tasklet(receiving_tasklet_callable)(testValue)

        def callback(previousTasklet, nextTasklet):
            completedTasklets.append(previousTasklet)
            completedTasklets.append(nextTasklet)

        scheduler.set_schedule_callback(callback)

        self.run_scheduler()

        self.assertEqual(completedTasklets[0],main)
        self.assertEqual(completedTasklets[1],sendingTasklet)

        self.assertEqual(completedTasklets[2],sendingTasklet)
        self.assertEqual(completedTasklets[3],main)

        self.assertEqual(completedTasklets[4],main)
        self.assertEqual(completedTasklets[5],receivingTasklet)

        self.assertEqual(completedTasklets[6],receivingTasklet)
        self.assertEqual(completedTasklets[7],main)

        self.assertEqual(completedTasklets[8],main)
        self.assertEqual(completedTasklets[9],sendingTasklet)

        self.assertEqual(completedTasklets[10],sendingTasklet)
        self.assertEqual(completedTasklets[11],main)

        self.assertEqual(len(completedTasklets), 12)

        scheduler.set_schedule_callback(None)

    def test_schedule_callback_with_multiple_threads(self):
        
        import threading

        callbackCalls = [0]

        def callback(previousTasklet, nextTasklet):
            callbackCalls[0]+=1
        

        scheduler.set_schedule_callback(callback)

        def createTasklets():
            for i in range(2):
                scheduler.tasklet(lambda: None)()
            scheduler.run()
        
        thread = threading.Thread(target=createTasklets, args=())

        thread.start()

        createTasklets()

        thread.join()

        self.assertEqual(callbackCalls[0],8)

        scheduler.set_schedule_callback(None)

    def test_multi_level_nested_tasklet_run_order_with_yield_to_blocked(self):
        completedSendTasklets = [""]
        
        c = scheduler.channel()

        def tasklet_callable(x):
            completedSendTasklets[0] += "t" + str(x)

        def nest_2():
            c.receive() 
            t2 = scheduler.tasklet(tasklet_callable)(2)
            scheduler.tasklet(tasklet_callable)(3)
            t2.run()

        def nest_1():
            t1 = scheduler.tasklet(tasklet_callable)(1)
            scheduler.tasklet(nest_2)()
            t1.run()
            c.receive()
            
        def sender():
            c.send(None)

        scheduler.tasklet(tasklet_callable)(0)
        scheduler.tasklet(nest_1)()
        scheduler.tasklet(sender)()

        self.run_scheduler()

        self.assertEqual(self.getruncount(), 1)

        if scheduler.get_use_nested_tasklets() == True:
            self.assertEqual(completedSendTasklets[0],"t0t1t2t3")

        c.send(None)

        if scheduler.get_use_nested_tasklets() == False:
            self.assertEqual(completedSendTasklets[0],"t0t1t2t3")

        self.assertEqual(c.balance, 0)
class TestScheduleOrderNoLimitWithNestedTasklets(test_utils.SchedulerTestCaseBase, 
                                                    TestScheduleOrderBase, 
                                                    test_utils.TestWithoutLimit):
    pass

class TestScheduleOrderWithLimitWithNestedTasklets(test_utils.SchedulerTestCaseBase, 
                                                      TestScheduleOrderBase, 
                                                      test_utils.TestWithLimit):
    pass

class TestScheduleOrderWithLimitWithoutNestedTasklets(test_utils.SchedulerTestCaseBase, 
                                                         TestScheduleOrderBase, 
                                                         test_utils.TestNoNestedTasklets, 
                                                         test_utils.TestWithLimit):
    pass

class TestScheduleOrderWithoutLimitWithoutNestedTasklets(test_utils.SchedulerTestCaseBase, 
                                                            TestScheduleOrderBase, 
                                                            test_utils.TestNoNestedTasklets, 
                                                            test_utils.TestWithoutLimit):
    pass


class TestSchedule(test_utils.SchedulerTestCaseBase):

    def setUp(self):
        super().setUp()
        self.events = []

    def test_schedule(self):
        def foo(previous):
            self.events.append("foo")
            self.assertTrue(previous.scheduled)
        t = scheduler.tasklet(foo)(scheduler.getcurrent())
        self.assertEqual(self.getruncount(), 2)
        self.assertTrue(t.scheduled)
        scheduler.schedule()
        self.assertEqual(self.getruncount(), 1)
        self.assertEqual(self.events, ["foo"])

    def test_schedule_remove_fail(self):

        def nested_tasklet():
            def foo(previous):
                self.events.append("foo")
                self.assertFalse(previous.scheduled)
                previous.insert()
                self.assertTrue(previous.scheduled)

            t = scheduler.tasklet(foo)(scheduler.getcurrent())
            self.assertEqual(self.getruncount(), 3)
            scheduler.schedule_remove()
            self.assertEqual(self.getruncount(), 2)
            self.assertEqual(self.events, ["foo"])
        t = scheduler.tasklet(nested_tasklet)()
        t.run()

    def test_set_schedule_callback(self):

        def callback1(previousTasklet,nextTasklet):
            pass

        def callback2(previousTasklet,nextTasklet):
            pass

        self.assertEqual(scheduler.get_schedule_callback(),None)
        self.assertEqual(None, scheduler.set_schedule_callback(callback1))
        self.assertEqual(scheduler.get_schedule_callback(),callback1)
        self.assertEqual(callback1, scheduler.set_schedule_callback(callback2))
        self.assertEqual(scheduler.get_schedule_callback(),callback2)
        self.assertEqual(callback2, scheduler.set_schedule_callback(None))
        self.assertEqual(scheduler.get_schedule_callback(),None)


    def test_schedule_callback_basic(self):
        callbackOutput = []

        def schedule_callback(previousTasklet, nextTasklet):
            callbackOutput.append(previousTasklet)
            callbackOutput.append(nextTasklet)

        scheduler.set_schedule_callback(schedule_callback)

        main = scheduler.getmain()
        t1 = scheduler.tasklet(lambda: None)()
        t2 = scheduler.tasklet(lambda: None)()
        t3 = scheduler.tasklet(lambda: None)()

        scheduler.run()

        self.assertEqual(self.getruncount(), 1)
        self.assertEqual(len(callbackOutput), 12)

        self.assertEqual(callbackOutput[0],main)
        self.assertEqual(callbackOutput[1],t1)
        self.assertEqual(callbackOutput[2],t1)
        self.assertEqual(callbackOutput[3],main)

        self.assertEqual(callbackOutput[4],main)
        self.assertEqual(callbackOutput[5],t2)
        self.assertEqual(callbackOutput[6],t2)
        self.assertEqual(callbackOutput[7],main)

        self.assertEqual(callbackOutput[8],main)
        self.assertEqual(callbackOutput[9],t3)
        self.assertEqual(callbackOutput[10],t3)
        self.assertEqual(callbackOutput[11],main)

        scheduler.set_schedule_callback(None)   # TODO Though this should be here to clean up after this test, if it isn't it blocks the schedule manager from cleaning up which needs looking at


class TestRun(test_utils.SchedulerTestCaseBase):
    def test_calling_run_from_non_main_tasklet(self):

        values = []
        def foo(x):
            values.append(x)

        def bar(chan):
            t = scheduler.tasklet(foo)("a")
            scheduler.tasklet(foo)("b")
            scheduler.tasklet(foo)("c")
            scheduler.tasklet(foo)("d")
            chan.send(1)
            scheduler.tasklet(foo)("e")
            scheduler.tasklet(foo)("f")
            scheduler.tasklet(foo)("g")
            scheduler.run()

        channel = scheduler.channel()
        t = scheduler.tasklet(bar)(channel)
        t.run()
        channel.receive()
        scheduler.run()
        self.assertEqual(values, ["a", "b", "c", "d", "e", "f", "g"])

class TestSwitch(test_utils.SchedulerTestCaseBase):
    """Test the new tasklet.switch() method, which allows
    explicit switching
    """
    def setUp(self):
        super().setUp()

        self.source = scheduler.getcurrent()
        self.finished = False
        self.c = scheduler.channel()

    def tearDown(self):
        self.source = None
        self.c = None
        super().tearDown()

    def target(self):
        self.assertTrue(self.source.paused)
        self.source.insert()
        self.finished = True

    def blocked_target(self):
        self.c.receive()
        self.finished = True

    def test_switch(self):
        """Simple switch"""
        t = scheduler.tasklet(self.target)()
        self.assertEqual(self.getruncount(), 2)
        t.switch()
        self.assertEqual(self.getruncount(), 1)
        self.assertTrue(self.finished)

    @unittest.skip('TODO - This test looks broken, Stackless giving the same result')
    def test_switch_self(self):
        t = scheduler.getcurrent()
        t.switch()

    def test_switch_blocked(self):
        t = scheduler.tasklet(self.blocked_target)()
        self.assertEqual(self.getruncount(), 2)
        t.run()
        self.assertEqual(self.getruncount(), 1)
        self.assertTrue(t.blocked)
        self.assertRaisesRegex(RuntimeError, "blocked", t.switch)
        self.c.send(None)
        self.assertTrue(self.finished)

    def test_switch_paused(self):
        t = scheduler.tasklet(self.target)
        self.assertEqual(self.getruncount(), 1)
        t.bind(args=())
        self.assertEqual(self.getruncount(), 1)
        self.assertTrue(t.paused)
        t.switch()
        self.assertTrue(self.finished)
        self.assertEqual(self.getruncount(), 1)

    def test_switch_trapped(self):
        t = scheduler.tasklet(self.target)()
        self.assertEqual(self.getruncount(), 2)
        self.assertFalse(t.paused)
        with switch_trapped():
            self.assertRaisesRegex(RuntimeError, "switch_trap", t.switch)
        self.assertFalse(t.paused)
        t.switch()
        self.assertTrue(self.finished)
        self.assertEqual(self.getruncount(), 1)

    @unittest.skip('TODO - This test looks broken, Stackless giving the same result')
    def test_switch_self_trapped(self):
        t = scheduler.getcurrent()
        with switch_trapped():
            t.switch()  # ok, switching to ourselves!

    def test_switch_blocked_trapped(self):
        t = scheduler.tasklet(self.blocked_target)()
        self.assertEqual(self.getruncount(), 2)
        t.run()
        self.assertEqual(self.getruncount(), 1)
        self.assertTrue(t.blocked)
        with switch_trapped():
            self.assertRaisesRegex(RuntimeError, "blocked", t.switch)
        self.assertTrue(t.blocked)
        self.c.send(None)
        self.assertTrue(self.finished)

    def test_switch_paused_trapped(self):
        t = scheduler.tasklet(self.target)
        self.assertEqual(self.getruncount(), 1)
        t.bind(args=())
        self.assertEqual(self.getruncount(), 1)
        self.assertTrue(t.paused)
        with switch_trapped():
            self.assertRaisesRegex(RuntimeError, "switch_trap", t.switch)
        self.assertTrue(t.paused)
        t.switch()
        self.assertTrue(self.finished)
        self.assertEqual(self.getruncount(), 1)

class TestSwitchTrap(test_utils.SchedulerTestCaseBase):

    class SwitchTrap(object):

        def __enter__(self):
            scheduler.switch_trap(1)

        def __exit__(self, exc, val, tb):
            scheduler.switch_trap(-1)
    switch_trap = SwitchTrap()

    def test_schedule(self):
        s = scheduler.tasklet(lambda: None)()
        self.assertEqual(self.getruncount(), 2)
        with self.switch_trap:
            self.assertRaisesRegex(RuntimeError, "switch_trap", scheduler.schedule)
        scheduler.run()
        self.assertEqual(self.getruncount(), 1)
    
    def test_schedule_remove(self):
        main = []
        s = scheduler.tasklet(lambda: main[0].insert())()
        self.assertEqual(self.getruncount(), 2)
        with self.switch_trap:
            self.assertRaisesRegex(RuntimeError, "switch_trap", scheduler.schedule_remove)
        main.append(scheduler.getcurrent())
        scheduler.schedule_remove()
        self.assertEqual(self.getruncount(), 1)
    
    def test_run(self):
        s = scheduler.tasklet(lambda: None)()
        self.assertEqual(self.getruncount(), 2)
        with self.switch_trap:
            self.assertRaisesRegex(RuntimeError, "switch_trap", scheduler.run)
        scheduler.run()
        self.assertEqual(self.getruncount(), 1)
    
    def test_run_specific(self):
        s = scheduler.tasklet(lambda: None)()
        self.assertEqual(self.getruncount(), 2)
        with self.switch_trap:
            self.assertRaisesRegex(RuntimeError, "switch_trap", s.run)
        s.run()
        self.assertEqual(self.getruncount(), 1)
    
    def test_run_paused(self):
        s = scheduler.tasklet(lambda: None)
        self.assertEqual(self.getruncount(), 1)
        s.bind(args=())
        self.assertEqual(self.getruncount(), 1)
        self.assertTrue(s.paused)
        with self.switch_trap:
            self.assertRaisesRegex(RuntimeError, "switch_trap", s.run)
        self.assertTrue(s.paused)
        scheduler.run()
        self.assertEqual(self.getruncount(), 1)
    
    def test_send(self):
        c = scheduler.channel()
        s = scheduler.tasklet(lambda: c.receive())()
        self.assertEqual(self.getruncount(), 2)
        with self.switch_trap:
            self.assertRaisesRegex(RuntimeError, "switch_trap", c.send, None)
        c.send(None)
        self.assertEqual(self.getruncount(), 1)
    
    @unittest.skip('Not currently part of required stub, send_exception is implemented')
    def test_send_throw(self):
        c = scheduler.channel()
        def f():
            self.assertRaises(NotImplementedError, c.receive)
        s = scheduler.tasklet(f)()
        self.assertEqual(self.getruncount(), 2)
        with self.switch_trap:
            self.assertRaisesRegex(RuntimeError, "switch_trap", c.send_throw, NotImplementedError)
        c.send_throw(NotImplementedError)
        self.assertEqual(self.getruncount(), 1)

    def test_send_exception(self):
        c = scheduler.channel()
        def f():
            self.assertRaises(NotImplementedError, c.receive)
        s = scheduler.tasklet(f)()
        self.assertEqual(self.getruncount(), 2)
        with self.switch_trap:
            self.assertRaisesRegex(RuntimeError, "switch_trap", c.send_exception, NotImplementedError)
        c.send_exception(NotImplementedError)
        self.assertEqual(self.getruncount(), 1)
    
    def test_receive(self):
        c = scheduler.channel()
        s = scheduler.tasklet(lambda: c.send(1))()
        self.assertEqual(self.getruncount(), 2)
        with self.switch_trap:
            self.assertRaisesRegex(RuntimeError, "switch_trap", c.receive)
        self.assertEqual(c.receive(), 1)
        self.assertEqual(self.getruncount(), 2)
    
    @unittest.skip('TODO - send_throw not in required stub so not implemented')
    def test_receive_throw(self):
        c = scheduler.channel()
        s = scheduler.tasklet(lambda: c.send_throw(NotImplementedError))()
        self.assertEqual(self.getruncount(), 2)
        with self.switch_trap:
            self.assertRaisesRegex(RuntimeError, "switch_trap", c.receive)
        self.assertRaises(NotImplementedError, c.receive)
        self.assertEqual(self.getruncount(), 1)
    
    def test_raise_exception(self):
        c = scheduler.channel()
        def foo():
            self.assertRaises(IndexError, c.receive)
        s = scheduler.tasklet(foo)()
        self.assertEqual(self.getruncount(), 2)
        s.run()  # necessary, since raise_exception won't automatically run it
        self.assertEqual(self.getruncount(), 1)
        with self.switch_trap:
            self.assertRaisesRegex(RuntimeError, "switch_trap", s.raise_exception, RuntimeError)
        s.raise_exception(IndexError)
        self.assertEqual(self.getruncount(), 1)
    
    def test_kill(self):
        c = scheduler.channel()
        def foo():
            self.assertRaises(scheduler.TaskletExit, c.receive)
        s = scheduler.tasklet(foo)()
        self.assertEqual(self.getruncount(), 2)
        s.run()  # necessary, since raise_exception won't automatically run it
        with self.switch_trap:
            self.assertRaisesRegex(RuntimeError, "switch_trap", s.kill)
        s.kill()
        self.assertEqual(self.getruncount(), 1)
    
    def test_run2(self):
        c = scheduler.channel()
        def foo():
            pass
        s = scheduler.tasklet(foo)()
        self.assertEqual(self.getruncount(), 2)
        with self.switch_trap:
            self.assertRaisesRegex(RuntimeError, "switch_trap", s.run)
        s.run()
        self.assertEqual(self.getruncount(), 1)

    def test_run_raising_function(self):
        def foo():
            raise RuntimeError("boom!")

        scheduler.tasklet(foo)()
        with self.assertRaises(RuntimeError):
            scheduler.run()

