import unittest
import sys
import traceback
import test_utils
import scheduler
    
class TestTasklets(test_utils.SchedulerTestCaseBase):
    
    def test_raise_exception(self):
        c = scheduler.channel()

        def foo():
            self.assertRaises(IndexError, c.receive)
        s = scheduler.tasklet(foo)()
        self.assertEqual(self.getruncount(), 2)
        s.run()  # necessary, since raise_exception won't automatically run it
        self.assertEqual(self.getruncount(), 1)
        s.raise_exception(IndexError)
   
    def test_run(self):
        flag = [False]

        def foo():
            flag[0] = True
        s = scheduler.tasklet(foo)()
        self.assertEqual(self.getruncount(), 2)
        s.run()
        self.assertEqual(flag[0], True)
        self.assertEqual(self.getruncount(), 1)

    def test_run_args(self):
        passed_args = [None]
        
        def foo(*args):
            passed_args[0] = args

        args = (1,2,3)

        scheduler.tasklet(foo)(*args)

        self.assertEqual(self.getruncount(), 2)

        scheduler.run()

        self.assertTupleEqual(passed_args[0], args)

        self.assertEqual(self.getruncount(), 1)

    def test_run_args_kwargs(self):
        passed_args = [None]
        passed_kwargs = [None]
        
        def foo(*args, **kwargs):
            passed_args[0] = args
            passed_kwargs[0] = kwargs

        args = (1,2,3)
        kwargs = {"a": 1, "b": 2, "c": 3}

        scheduler.tasklet(foo)(*args, **kwargs)

        self.assertEqual(self.getruncount(), 2)

        scheduler.run()

        self.assertEqual(self.getruncount(), 1)

        self.assertTupleEqual(passed_args[0], args)
        self.assertDictEqual(passed_kwargs[0], kwargs)
    
    def test_kill_tasklet(self):
        value = [0]

        def increment_value():
            value[0] = value[0] + 1

        tasklet = scheduler.tasklet(increment_value)()

        self.assertEqual(self.getruncount(), 2)

        tasklet.kill()

        self.assertEqual(self.getruncount(), 1)

        scheduler.run()

        self.assertEqual(self.getruncount(), 1)

        # Tasklet was not run so value remains zero
        self.assertEqual(value[0],0)

        tasklet1 = scheduler.tasklet(increment_value)()

        tasklet2 = scheduler.tasklet(increment_value)()

        tasklet3 = scheduler.tasklet(increment_value)()

        self.assertEqual(self.getruncount(), 4)

        tasklet1.kill()

        self.assertEqual(self.getruncount(), 1)

        # Tasklet 1 was killed, tasklets were run from this point
        # So tasklet 2 and 3 will run and value should be 2
        self.assertEqual(value[0],2)

    def test_paused(self):
        def task():
            scheduler.schedule_remove()

        t = scheduler.tasklet(task)()
        scheduler.run()
        self.assertTrue(t.paused)


    def test_invalid_tasklet_when_skipping_init(self):
        
        class Foo(scheduler.tasklet):
            def __init__(self, *args, **kwargs):
                pass 
            
        t = Foo()

        self.assertRaises(RuntimeError, t.run)

    def test_invalid_tasklet_when_skipping_new(self):
        
        class Foo(scheduler.tasklet):
            def __new__(cls, *args, **kwargs):
                pass 
            
        t = Foo()

        self.assertEqual(t, None)
        

    def test_weakref_in_tasklet_new(self):

        import weakref

        tasklets = weakref.WeakKeyDictionary()

        class Foo(scheduler.tasklet):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
            
            def __new__(cls, *args, **kwargs):
                t = scheduler.tasklet.__new__(cls, *args, **kwargs)
                tasklets[t] = True
                return t
            
        t = Foo()

        # Single check to ensure t is valid
        self.assertFalse(t.alive)

    def test_cyclical_callable_reference_cleans_up(self):
        # when wrapper is set to None the tasklet should clean up
        # The tasklet holds a reference to the scheduleManager
        # So when the tasklet is cleaned there should remain only
        # 1 ref to schedule manager
        class DummyWrapper:
            def __init__(self):
                def inner():
                    print(self)
                    
                self.tasklet = scheduler.tasklet(inner)

        wrapperInstance = DummyWrapper()
        wrapperInstance = None

        import gc
        gc.collect()

    def test_tasklets_with_cyclical_argument_cleans_up(self):
        # If Tasklet has itself in an argument ensure that 
        # cyclic dep is handled

        def test(x):
            print("world")

        t = scheduler.tasklet(test)
        t.bind(test,(t,))

        t = None

        import gc
        gc.collect()

    def test_remove_and_switch(self):
        valueOut = [-1]
        valueIn = [1]

        def foo(x):
            valueOut[0] = x
        
        t = scheduler.tasklet(foo)(valueIn[0])

        self.assertEqual(t.remove(), t)

        t.switch()

        self.assertEqual(valueIn[0],valueOut[0])

    def test_remove_and_run(self):
        valueOut = [-1]
        valueIn = [1]

        def foo(x):
            valueOut[0] = x
        
        t = scheduler.tasklet(foo)(valueIn[0])

        self.assertEqual(t.remove(), t)

        t.run()

        self.assertEqual(valueIn[0],valueOut[0])



    def test_insert_from_another_thread(self):
        import threading

        valueIn = ["TEST_VALUE"]
        valueOut = []

        def callable_tasklet(value):
            valueOut.append(value)

        t = scheduler.tasklet(callable_tasklet)
        t.bind(callable_tasklet)
        t.setup(valueIn[0])

        def ThreadFunc():
            t.insert()

            # Tasklet should not add to threads queue
            self.assertEqual(self.getruncount(), 1)

        thread = threading.Thread(target=ThreadFunc)
        thread.start()
        thread.join()

        self.assertEqual(self.getruncount(), 2)

        scheduler.run()

        self.assertEqual(valueOut[0],valueIn[0])


    def test_remove_from_another_thread(self):
        import threading

        valueIn = ["TEST_VALUE"]
        valueOut = []

        def callable_tasklet(value):
            valueOut.append(value)

        t = scheduler.tasklet(callable_tasklet)(valueIn[0])

        def ThreadFunc():
            t.remove()

        thread = threading.Thread(target=ThreadFunc)
        thread.start()
        thread.join()

        self.assertEqual(self.getruncount(), 1)

        scheduler.run()

        self.assertEqual(len(valueOut),0)

        t.kill()

    def test_run_from_another_thread(self):
        import threading

        valueIn = ["TEST_VALUE"]
        valueOut = []

        def callable_tasklet(value):
            valueOut.append(value)

        t = scheduler.tasklet(callable_tasklet)(valueIn[0])

        def ThreadFunc():
            t.run()

            # Tasklet should not add to threads queue
            self.assertEqual(self.getruncount(), 1)

        thread = threading.Thread(target=ThreadFunc)
        thread.start()
        thread.join()

        self.assertEqual(self.getruncount(), 2)

        scheduler.run()

        self.assertEqual(valueOut[0],valueIn[0])

    def test_switch_from_another_thread(self):
        import threading

        valueIn = ["TEST_VALUE"]
        valueOut = []

        def callable_tasklet(value):
            valueOut.append(value)

        t = scheduler.tasklet(callable_tasklet)(valueIn[0])

        def ThreadFunc():
            self.assertRaises(RuntimeError, t.switch())

            # Tasklet should not add to threads queue
            self.assertEqual(self.getruncount(), 1)

        thread = threading.Thread(target=ThreadFunc)
        thread.start()
        thread.join()

        self.assertEqual(self.getruncount(), 2)

        scheduler.run()

        self.assertEqual(valueOut[0],valueIn[0])

    def test_kill_from_another_thread(self):
        import threading

        valueIn = ["TEST_VALUE"]
        valueOut = []

        def callable_tasklet(value):
            valueOut.append(value)

        t = scheduler.tasklet(callable_tasklet)(valueIn[0])

        def ThreadFunc():
            self.assertRaises(RuntimeError, t.kill())

            # Tasklet should not add to threads queue
            self.assertEqual(self.getruncount(), 1)

        thread = threading.Thread(target=ThreadFunc)
        thread.start()
        thread.join()

        self.assertEqual(self.getruncount(), 2)

        scheduler.run()

        self.assertEqual(valueOut[0],valueIn[0])

    
    def test_bind_from_another_thread(self):
        import threading

        valueIn = ["TEST_VALUE"]
        valueOut = []

        def callable_tasklet(value):
            valueOut.append(value)

        t = scheduler.tasklet(callable_tasklet)
        
        def ThreadFunc():
            self.assertRaises(RuntimeError, t.bind())

            # Tasklet should not add to threads queue
            self.assertEqual(self.getruncount(), 1)

        thread = threading.Thread(target=ThreadFunc)
        thread.start()
        thread.join()

        self.assertEqual(t.bind(callable_tasklet),t)
        self.assertEqual(t.setup(valueIn[0]),t)

        self.assertEqual(self.getruncount(), 2)

        scheduler.run()

        self.assertEqual(valueOut[0],valueIn[0])

    def test_setup_from_another_thread(self):
        import threading

        valueIn = ["TEST_VALUE"]
        valueOut = []

        def callable_tasklet(value):
            valueOut.append(value)

        t = scheduler.tasklet(callable_tasklet)
        t.bind(callable_tasklet)

        def ThreadFunc():
            self.assertRaises(RuntimeError, t.setup)

            # Tasklet should not add to threads queue
            self.assertEqual(self.getruncount(), 1)

        thread = threading.Thread(target=ThreadFunc)
        thread.start()
        thread.join()

        t.setup(valueIn[0])

        self.assertEqual(self.getruncount(), 2)

        scheduler.run()

        self.assertEqual(valueOut[0],valueIn[0])

    def test_times_switched_to(self):
        def foo(c):
            self.assertEqual(scheduler.getcurrent().times_switched_to, 1)
            c.receive()
            self.assertEqual(scheduler.getcurrent().times_switched_to, 2)
            scheduler.schedule()
            self.assertEqual(scheduler.getcurrent().times_switched_to, 3)

        chan = scheduler.channel()
        t = scheduler.tasklet(foo)(chan)
        scheduler.run()
        chan.send(None)

    def test_times_switched_to_bind_reset(self):
        def foo(c):
            self.assertEqual(scheduler.getcurrent().times_switched_to, 1)
            c.receive()
            self.assertEqual(scheduler.getcurrent().times_switched_to, 2)
            scheduler.schedule()
            self.assertEqual(scheduler.getcurrent().times_switched_to, 3)

        def bar():
            self.assertEqual(scheduler.getcurrent().times_switched_to, 1)

        chan = scheduler.channel()
        t = scheduler.tasklet(foo)(chan)
        scheduler.run()
        chan.send(None)

        t.bind(bar)
        t.setup()
        scheduler.run()

class TestTaskletThrowBase(object):

    def after_check(self, s):
        # the tasklet ran immediately
        self.assertFalse(s.alive)

    def test_throw_noargs(self):
        c = scheduler.channel()

        def foo():
            self.assertRaises(IndexError, c.receive)

        s = scheduler.tasklet(foo)()

        self.assertEqual(self.getruncount(), 2)

        s.run()  # It needs to have started to run

        self.assertEqual(self.getruncount(), 1)

        self.assertEqual(c.balance, -1)

        self.throw(s, IndexError)

        self.after_check(s)

    def test_throw_args(self):
        c = scheduler.channel()

        def foo():
            try:
                c.receive()
            except Exception as e:
                self.assertTrue(isinstance(e, IndexError))
                self.assertEqual(e.args, (1, 2, 3))
        s = scheduler.tasklet(foo)()
        self.assertEqual(self.getruncount(), 2)
        s.run()  # It needs to have started to run
        self.assertEqual(self.getruncount(), 1)
        self.assertEqual(c.balance, -1)
        self.throw(s, IndexError, (1, 2, 3))
        self.after_check(s)

    def test_throw_inst(self):
        c = scheduler.channel()

        def foo():
            try:
                c.receive()
            except Exception as e:
                self.assertTrue(isinstance(e, IndexError))
                self.assertEqual(e.args, (1, 2, 3))
        s = scheduler.tasklet(foo)()
        self.assertEqual(self.getruncount(), 2)
        s.run()  # It needs to have started to run
        self.assertEqual(self.getruncount(), 1)
        self.assertEqual(c.balance,-1)
        self.throw(s, IndexError(1, 2, 3))
        self.after_check(s)

    def test_throw_exc_info(self):
        c = scheduler.channel()

        def foo():
            try:
                c.receive()
            except Exception as e:
                self.assertTrue(isinstance(e, ZeroDivisionError))
        s = scheduler.tasklet(foo)()
        self.assertEqual(self.getruncount(), 2)
        s.run()  # It needs to have started to run
        self.assertEqual(self.getruncount(), 1)
        self.assertEqual(c.balance, -1)

        def errfunc():
            1 / 0
        try:
            errfunc()
        except Exception:
            self.throw(s, *sys.exc_info())
        self.after_check(s)

    def test_throw_traceback(self):
        c = scheduler.channel()

        def foo():
            try:
                c.receive()
            except Exception:
                s = "".join(traceback.format_tb(sys.exc_info()[2]))
                self.assertTrue("errfunc" in s)
        s = scheduler.tasklet(foo)()
        self.assertEqual(self.getruncount(), 2)
        s.run()  # It needs to have started to run
        self.assertEqual(self.getruncount(), 1)
        self.assertEqual(c.balance, -1)

        def errfunc():
            1 / 0
        try:
            errfunc()
        except Exception:
            self.throw(s, *sys.exc_info())
        self.after_check(s)

    def test_new(self):
        c = scheduler.channel()

        def foo():
            try:
                c.receive()
            except Exception as e:
                self.assertTrue(isinstance(e, IndexError))
                raise
        s = scheduler.tasklet(foo)()
        self.assertEqual(self.getruncount(), 2)
        self.assertTrue(s.alive)
        # Test that the current "unhandled exception behaviour"
        # is invoked for the not-yet-running tasklet.

        def doit():
            self.throw(s, IndexError)
        if not self.pending:
            self.assertRaises(IndexError, doit)
        else:
            doit()
            self.assertRaises(IndexError, scheduler.run)

    def test_kill_new(self):

        def t():
            self.assertFalse("should not run this")
        s = scheduler.tasklet(t)()
        self.assertEqual(self.getruncount(), 2)
        # Should not do anything
        s.throw(scheduler.TaskletExit)
        self.assertEqual(self.getruncount(), 1)
        # the tasklet should be dead
        scheduler.run()
        self.assertEqual(self.getruncount(), 1)
        self.assertRaisesRegex(RuntimeError, "dead", s.run)
 
    def test_dead(self):
        c = scheduler.channel()

        def foo():
            c.receive()
        s = scheduler.tasklet(foo)()
        self.assertEqual(self.getruncount(), 2)
        s.run()
        self.assertEqual(self.getruncount(), 1)
        self.assertEqual(c.balance, -1)
        c.send(None)
        self.assertEqual(c.balance, 0)
        self.assertEqual(self.getruncount(), 1)
        scheduler.run()
        self.assertFalse(s.alive)

        def doit():
            self.throw(s, IndexError)
        self.assertRaises(RuntimeError, doit)

    def test_kill_dead(self):

        c = scheduler.channel()

        def foo():
            c.receive()
        s = scheduler.tasklet(foo)()
        self.assertEqual(self.getruncount(), 2)
        s.run()
        self.assertEqual(self.getruncount(), 1)
        self.assertEqual(c.balance, -1)
        c.send(None)
        self.assertEqual(c.balance, 0)
        self.assertEqual(self.getruncount(), 1)
        scheduler.run()
        self.assertFalse(s.alive)

        def doit():
            self.throw(s, scheduler.TaskletExit)
        # nothing should happen here.
        doit()
   
    def test_throw_invalid(self):
        s = scheduler.getcurrent()

        def t():
            self.throw(s)
        self.assertRaises(TypeError, t)

        def t():  # @DuplicatedSignature
            self.throw(s, IndexError(1), (1, 2, 3))
        self.assertRaises(TypeError, t)


class TestTaskletThrowImmediate(test_utils.SchedulerTestCaseBase, TestTaskletThrowBase):
    pending = False

    @classmethod
    def throw(cls, s, *args):
        s.throw(*args, pending=cls.pending)

    def after_check(self, s):
        # the tasklet ran immediately
        self.assertFalse(s.alive)


class TestTaskletThrowNonImmediate(TestTaskletThrowImmediate):
    pending = True

    def after_check(self, s):
        # After the throw, the tasklet still hasn't run
        self.assertTrue(s.alive)
        s.run()
        self.assertFalse(s.alive)


class TestKill(test_utils.SchedulerTestCaseBase):
    SLP_TASKLET_KILL_REBINDS_THREAD = False  # see tasklet.c function impl_tasklet_kill()

    def test_kill_pending_true(self):

        killed = [False]

        def foo():
            try:
                scheduler.schedule()
            except scheduler.TaskletExit:
                killed[0] = True
                raise
        t = scheduler.tasklet(foo)()
        self.assertEqual(self.getruncount(), 2)
        t.run()
        self.assertEqual(self.getruncount(), 2)
        self.assertFalse(killed[0])
        t.kill(pending=True)
        self.assertEqual(self.getruncount(), 2)
        self.assertFalse(killed[0])
        t.run()
        self.assertTrue(killed[0])
        self.assertEqual(self.getruncount(), 1)

    def test_kill_pending_False(self):

        killed = [False]

        def foo():
            try:
                scheduler.schedule()
            except scheduler.TaskletExit:
                killed[0] = True
                raise
        t = scheduler.tasklet(foo)()
        self.assertEqual(self.getruncount(), 2)
        t.run()
        self.assertEqual(self.getruncount(), 2)
        self.assertFalse(killed[0])
        t.kill(pending=False)
        self.assertEqual(self.getruncount(), 1)
        self.assertTrue(killed[0])

    def test_kill_current(self):

        killed = [False]

        def task():
            try:
                scheduler.getcurrent().kill()   #TODO replace getcurrent with current when working again
            except scheduler.TaskletExit:
                killed[0] = True
                raise
        t = scheduler.tasklet(task)()
        self.assertEqual(self.getruncount(), 2)
        t.run()
        self.assertTrue(killed[0])
        self.assertEqual(self.getruncount(), 1)
        self.assertFalse(t.alive)
        self.assertEqual(t.thread_id, scheduler.getcurrent().thread_id) #TODO replace getcurrent with current when working again

    def _test_kill_without_thread_state(self, nl, block):
        channel = scheduler.channel()
        loop = True

        def task():
            while loop:
                try:
                    if block:
                        channel.receive()
                    else:
                        scheduler.main.run()
                except scheduler.TaskletExit:
                    pass

        def other_thread_main():
            tlet.bind_thread()
            tlet.run()

        if nl == 0:
            tlet = scheduler.tasklet().bind(task, ())
        else:
            tlet = scheduler.tasklet().bind(apply_not_stackless, (task,))
        t = threading.Thread(target=other_thread_main, name="other thread")
        t.start()
        t.join()
        time.sleep(0.05)  # time for other_thread to clear its state

        loop = False
        if block:
            self.assertTrue(tlet.blocked)
        else:
            self.assertFalse(tlet.blocked)
        self.assertFalse(tlet.alive)
        self.assertEqual(tlet.thread_id, -1)
        self.assertRaisesRegex(RuntimeError, "tasklet has no thread", tlet.throw, scheduler.TaskletExit, pending=True)
        tlet.kill(pending=True)
        self.assertFalse(tlet.blocked)
        if self.SLP_TASKLET_KILL_REBINDS_THREAD and scheduler.enable_softswitch(None) and nl == 0:
            # rebinding and soft switching
            self.assertTrue(tlet.scheduled)
            self.assertTrue(tlet.alive)
            tlet.remove()
            tlet.bind(None)
        else:
            # hard switching
            self.assertFalse(tlet.scheduled)
            self.assertIsNone(tlet.next)
            self.assertIsNone(tlet.prev)
            self.assertFalse(tlet.alive)
            tlet.remove()
            tlet.kill()

    # TODO Reinstate
    #@unittest.skipUnless(withThreads, "requires thread support")
    #@testcase_leaks_references("chatches TaskletExit and does not die in its own thread", soft_switching=False)
    #def test_kill_without_thread_state_nl0(self):
    #    return self._test_kill_without_thread_state(0, False)

    #@unittest.skipUnless(withThreads, "requires thread support")
    #@testcase_leaks_references("chatches TaskletExit and does not die in its own thread")
    #def test_kill_without_thread_state_nl1(self):
    #    return self._test_kill_without_thread_state(1, False)

    #@unittest.skipUnless(withThreads, "requires thread support")
    #@testcase_leaks_references("chatches TaskletExit and does not die in its own thread", soft_switching=False)
    #def test_kill_without_thread_state_blocked_nl0(self):
    #    return self._test_kill_without_thread_state(0, True)

    #@unittest.skipUnless(withThreads, "requires thread support")
    #@testcase_leaks_references("chatches TaskletExit and does not die in its own thread")
    #def test_kill_without_thread_state_blocked_nl1(self):
    #    return self._test_kill_without_thread_state(1, True)
            

class TestExceptions(test_utils.SchedulerTestCaseBase):

    def test_raise_exception(self):

        taskletExceptHit = [False]

        def foo():
            try:
                scheduler.schedule()
            except TypeError:
                taskletExceptHit[0] = True

        t = scheduler.tasklet(foo)()

        t.run()

        t.raise_exception(TypeError)

        self.assertTrue(taskletExceptHit[0])

    def test_throw_exception(self):

        taskletExceptHit = [False]

        def foo():
            try:
                scheduler.schedule()
            except TypeError:
                taskletExceptHit[0] = True

        t = scheduler.tasklet(foo)()
        
        t.run()

        t.throw(TypeError)

        self.assertTrue(taskletExceptHit[0])

class TestBind(test_utils.SchedulerTestCaseBase):

    def setUp(self):
        super().setUp()
        self.finally_run_count = 0
        self.args = self.kwargs = None

    def task(self, with_c_state):
        try:
            if with_c_state:
                _testscheduler.test_cstate(lambda: scheduler.schedule_remove())
            else:
                scheduler.schedule_remove()
        finally:
            self.finally_run_count += 1

    def args_test(self, *args, **kwargs):
        self.args = args
        self.kwargs = dict(kwargs)

    def assertArgs(self, args, kwargs):
        self.assertEqual(args, self.args)
        self.assertEqual(kwargs, self.kwargs)

    def test_bind(self):
        import weakref
        t = scheduler.tasklet()
        self.assertEqual(self.getruncount(), 1)
        wr = weakref.ref(t)

        self.assertFalse(t.alive)

        t.bind(None)  # must not change the tasklet

        self.assertFalse(t.alive)

        t.bind(self.task)
        t.setup(False)

        self.assertEqual(self.getruncount(), 2)

        scheduler.run()
        self.assertEqual(self.getruncount(), 1)
        self.assertFalse(t.scheduled)
        self.assertTrue(t.alive)
        if scheduler.enable_softswitch(None):
            self.assertTrue(t.restorable)

        self.assertEqual(t.insert(),t)
        self.assertEqual(self.getruncount(), 2)
        scheduler.run()
        self.assertEqual(self.getruncount(), 1)

        # remove the tasklet. Must run the finally clause
        t = None
        self.assertIsNone(wr())  # tasklet has been deleted
        self.assertEqual(self.finally_run_count, 1)

    def test_bind_fail_not_callable(self):
        class C(object):
            pass
        self.assertRaisesRegex(TypeError, "callable", scheduler.getcurrent().bind, C())

    def test_unbind_ok(self):
        import weakref

        def task():
            scheduler.schedule_remove()

        t = scheduler.tasklet(task)()
        self.assertEqual(self.getruncount(), 2)
        wr = weakref.ref(t)

        # prepare a paused tasklet
        scheduler.run()
        self.assertEqual(self.getruncount(), 1)
        self.assertFalse(t.scheduled)
        self.assertTrue(t.alive)

        t.bind(None)
        self.assertFalse(t.alive)

        # remove the tasklet. Must not run the finally clause
        t = None
        self.assertIsNone(wr())  # tasklet has been deleted
        self.assertEqual(self.finally_run_count, 0)

    def test_unbind_fail_current(self):
        self.assertRaisesRegex(RuntimeError, "current tasklet", scheduler.getcurrent().bind, None)

    def test_unbind_fail_scheduled(self):
        t = scheduler.tasklet(self.task)(False)
        self.assertEqual(self.getruncount(), 2)
        # prepare a paused tasklet
        scheduler.run()
        self.assertEqual(self.getruncount(), 1)
        t.insert()
        self.assertEqual(self.getruncount(), 2)
        self.assertTrue(t.scheduled)
        self.assertTrue(t.alive)

        self.assertRaisesRegex(RuntimeError, "scheduled", t.bind, None)

    def test_bind_noargs(self):
        t = scheduler.tasklet(self.task)
        self.assertEqual(self.getruncount(), 1)
        t.bind(self.args_test)
        self.assertRaises(RuntimeError, t.run)

    def test_bind_args(self):
        args = "foo", "bar"
        t = scheduler.tasklet(self.task)
        self.assertEqual(self.getruncount(), 1)
        t.bind(self.args_test, args)
        self.assertEqual(self.getruncount(), 1)
        t.run()
        self.assertEqual(self.getruncount(), 1)
        self.assertArgs(args, {})

        t = scheduler.tasklet(self.task)
        self.assertEqual(self.getruncount(), 1)
        t.bind(self.args_test, args=args)
        self.assertEqual(self.getruncount(), 1)
        t.run()
        self.assertEqual(self.getruncount(), 1)
        self.assertArgs(args, {})

    def test_bind_kwargs(self):
        t = scheduler.tasklet(self.task)
        self.assertEqual(self.getruncount(), 1)
        kwargs = {"hello": "world"}
        t.bind(self.args_test, None, kwargs)
        self.assertEqual(self.getruncount(), 1)
        t.run()
        self.assertEqual(self.getruncount(), 1)
        self.assertArgs((), kwargs)

        t = scheduler.tasklet(self.task)
        self.assertEqual(self.getruncount(), 1)
        t.bind(self.args_test, kwargs=kwargs)
        self.assertEqual(self.getruncount(), 1)
        t.run()
        self.assertEqual(self.getruncount(), 1)
        self.assertArgs((), kwargs)

    def test_bind_args_kwargs(self):
        args = ("foo", "bar")
        kwargs = {"hello": "world"}

        t = scheduler.tasklet(self.task)
        self.assertEqual(self.getruncount(), 1)
        t.bind(self.args_test, args, kwargs)
        self.assertEqual(self.getruncount(), 1)
        t.run()
        self.assertEqual(self.getruncount(), 1)
        self.assertArgs(args, kwargs)

        t = scheduler.tasklet(self.task)
        self.assertEqual(self.getruncount(), 1)
        t.bind(self.args_test, args=args, kwargs=kwargs)
        self.assertEqual(self.getruncount(), 1)
        t.run()
        self.assertEqual(self.getruncount(), 1)
        self.assertArgs(args, kwargs)

    def test_bind_args_kwargs_nofunc(self):
        args = ("foo", "bar")
        kwargs = {"hello": "world"}

        t = scheduler.tasklet(self.args_test)
        self.assertEqual(self.getruncount(), 1)
        t.bind(None, args, kwargs)
        self.assertEqual(self.getruncount(), 1)
        t.run()
        self.assertEqual(self.getruncount(), 1)
        self.assertArgs(args, kwargs)

        t = scheduler.tasklet(self.args_test)
        self.assertEqual(self.getruncount(), 1)
        t.bind(args=args, kwargs=kwargs)
        self.assertEqual(self.getruncount(), 1)
        t.run()
        self.assertEqual(self.getruncount(), 1)
        self.assertArgs(args, kwargs)

    def test_bind_args_not_runnable(self):
        args = ("foo", "bar")
        kwargs = {"hello": "world"}

        t = scheduler.tasklet(self.task)
        self.assertEqual(self.getruncount(), 1)
        t.bind(self.args_test, args, kwargs)
        self.assertEqual(self.getruncount(), 1)
        self.assertFalse(t.scheduled)
        t.run()
        self.assertEqual(self.getruncount(), 1)

    @unittest.skip('TODO - Threading not yet fully implemented')
    def test_unbind_main(self):
        self.skipUnlessSoftswitching()

        done = []

        def other():
            main = scheduler.main
            self.assertRaisesRegex(RuntimeError, "can't unbind the main tasklet", main.bind, None)

        # the initial nesting level depends on the test runner.
        # We need a main tasklet with nesting_level == 0. Therefore we
        # use a thread
        def other_thread():
            self.assertEqual(scheduler.current.nesting_level, 0)
            self.assertIs(scheduler.current, scheduler.main)
            scheduler.tasklet(other)().switch()
            done.append(True)

        t = threading.Thread(target=other_thread, name="other thread")
        t.start()
        t.join()
        self.assertTrue(done[0])

    @unittest.skip('TODO - Threading not yet fully implemented')
    def test_rebind_main(self):
        # rebind the main tasklet of a thread. This is highly discouraged,
        # because it will deadlock, if the thread is a non daemon threading.Thread.
        self.skipUnlessSoftswitching()

        ready = thread.allocate_lock()
        ready.acquire()

        self.target_called = False
        self.main_returned = False

        def target():
            self.target_called = True
            ready.release()

        def other_thread_main():
            self.assertTrue(scheduler.current.is_main)
            try:
                scheduler.tasklet(scheduler.main.bind)(target, ()).switch()
            finally:
                self.main_returned = True
                ready.release()

        thread.start_new_thread(other_thread_main, ())
        ready.acquire()

        self.assertTrue(self.target_called)
        self.assertFalse(self.main_returned)

    @unittest.skip('TODO - recusion_depth is not implemented')
    def test_rebind_recursion_depth(self):
        self.skipUnlessSoftswitching()
        self.recursion_depth_in_test = None

        def tasklet_outer():
            tasklet_inner()

        def tasklet_inner():
            scheduler.main.switch()

        def test():
            self.recursion_depth_in_test = scheduler.current.recursion_depth

        tlet = scheduler.tasklet(tasklet_outer)()
        self.assertEqual(tlet.recursion_depth, 0)
        tlet.run()
        self.assertEqual(tlet.recursion_depth, 2)
        tlet.bind(test, ())
        self.assertEqual(tlet.recursion_depth, 0)
        tlet.run()
        self.assertEqual(tlet.recursion_depth, 0)
        self.assertEqual(self.recursion_depth_in_test, 1)

    def test_rebind_after_run(self):
        results = []
        def foo(x):
            results.append(x)

        t = scheduler.tasklet()
        t.bind(foo)
        t.setup(1)
        t.run()

        t.bind(foo)
        t.setup(2)
        t.run()

        self.assertEqual(results, [1,2])



class TestTaskletExitException(test_utils.SchedulerTestCaseBase):

    def test_tasklet_raising_standard_exception(self):

        def func():
            raise(TypeError)
        
        t = scheduler.tasklet(func)()

        self.assertEqual(self.getruncount(), 2)

        self.assertRaises(TypeError, t.run)

        self.assertEqual(self.getruncount(), 1)


    def test_tasklet_raising_TaskletExit_exception(self):
        value = [False]

        def func():
            try:
                raise(scheduler.TaskletExit)
            except scheduler.TaskletExit:
                value[0] = True

        t = scheduler.tasklet(func)()

        self.assertEqual(self.getruncount(), 2)

        t.run()

        self.assertEqual(self.getruncount(), 1)

        self.assertEqual(value[0], True)

    def test_tasklet_cannot_accidentally_catch_taskletexit(self):
        def task():
            try:
                scheduler.schedule()
            except Exception:
                self.fail("TaskletExit should not inherit from Exception")

        t = scheduler.tasklet(task)()
        t.run()
        t.kill()
        self.assertFalse(t.alive)

    def test_tasklet_get_frame(self):
        channel = scheduler.channel()

        def foo(chan):
            chan.receive()

        t = scheduler.tasklet(foo)(channel)
        t.run()

        try:
            t.frame
        except RuntimeError:
            pass

        channel.send(None)

    def test_kill_unbound_tasklet(self):
        def test():
            c = scheduler.tasklet().kill(pending=True)

        scheduler.tasklet(test)()
        scheduler.run()

    def test_call_setup_twice(self):
        def foo():
            return 0

        t = scheduler.tasklet(foo)()
        # call setup directly
        self.assertRaises(RuntimeError, t.setup)
        # call setup through tasklets tp_call function
        self.assertRaises(RuntimeError, t)

class TestTaskletMetricsCollection(test_utils.SchedulerTestCaseBase):

    def test_method_name(self):
        def testMethod():
            return 0

        t = scheduler.tasklet(testMethod)()
        self.assertEqual("testMethod", t.method_name)

    def test_line_number(self):
        def testMethod():
            return 0

        t = scheduler.tasklet(testMethod)()
        self.assertEqual(testMethod.__code__.co_firstlineno, t.line_number)

    def test_file_name(self):
        def testMethod():
            return 0

        t = scheduler.tasklet(testMethod)()
        self.assertTrue(t.file_name.endswith("test_tasklet.py"))


    def test_start_end_time(self):
        def testMethod():
            return 0

        t = scheduler.tasklet(testMethod)()

        self.assertEqual(t.startTime, 0)
        self.assertEqual(t.endTime, 0)
        
        scheduler.run()
        
        self.assertTrue(t.startTime > 0)
        self.assertTrue(t.endTime > t.startTime)

class TestTaskletDontRaise(test_utils.SchedulerTestCaseBase):

    def test_tasklet_dont_raise(self):
        a = [0]
        def testMethod():
            a[0] = 1
            raise TypeError("test")

        t = scheduler.tasklet()
        t.dont_raise = True
        t.bind(testMethod)
        t.setup()

        scheduler.run()

        self.assertEqual(a, [1])

    def test_tasklet_with_tracer(self):
        a = []

        class CtxMgr:
            def __init__(self, t):
                self.tasklet = t

            def __enter__(self):
                a.append((1, str(self.tasklet)))

            def __exit__(self, exctype, excinst, exctb):
                a.append((2, str(self.tasklet)))

        def testMethod():
            a.append(1)

        t = scheduler.tasklet()
        t.dont_raise = True
        t.bind(testMethod)
        t.context_manager_getter = CtxMgr
        t.setup()

        scheduler.run()

        self.assertEqual(a, [ (1, str(t)), 1, (2, str(t)) ])

    def test_raising_tasklet_with_tracer(self):
        a = []

        class CtxMgr:
            def __init__(self, t):
                self.tasklet = t

            def __enter__(self):
                a.append((1, str(self.tasklet)))

            def __exit__(self, exctype, excinst, exctb):
                a.append((2, str(self.tasklet)))

        def testMethod():
            a.append(1)
            raise TypeError("test")
            a.append(2)

        t = scheduler.tasklet()
        t.dont_raise = True
        t.bind(testMethod)
        t.context_manager_getter = CtxMgr
        t.setup()

        scheduler.run()

        self.assertEqual(a, [ (1, str(t)), 1, (2, str(t)) ])

    def test_tasklet_with_raising_tracer_enter(self):
        a = []

        class CtxMgr:
            def __init__(self, t):
                self.tasklet = t

            def __enter__(self):
                a.append((1, str(self.tasklet)))
                raise TypeError("test")

            def __exit__(self, exctype, excinst, exctb):
                a.append((2, str(self.tasklet)))

        def testMethod():
            a.append(1)

        t = scheduler.tasklet()
        t.dont_raise = True
        t.bind(testMethod)
        t.context_manager_getter = CtxMgr
        t.setup()

        self.assertRaises(TypeError, scheduler.run)

        self.assertEqual(a, [ (1, str(t)) ])

    def test_tasklet_with_raising_tracer_exit(self):
        a = []

        class CtxMgr:
            def __init__(self, t):
                self.tasklet = t

            def __enter__(self):
                a.append((1, str(self.tasklet)))

            def __exit__(self, exctype, excinst, exctb):
                a.append((2, str(self.tasklet)))
                raise TypeError("test")

        def testMethod():
            a.append(1)

        t = scheduler.tasklet()
        t.dont_raise = True
        t.context_manager_getter = CtxMgr
        t.bind(testMethod)
        t.setup()

        self.assertRaises(TypeError, scheduler.run)

        self.assertEqual(a, [ (1, str(t)), 1, (2, str(t)) ])

    def test_raising_tasklet_with_raising_tracer_exit(self):
        a = []

        class CtxMgr:
            def __init__(self, t):
                self.tasklet = t

            def __enter__(self):
                a.append((1, self.tasklet))

            def __exit__(self, exctype, excinst, exctb):
                a.append((2, self.tasklet))
                raise TypeError("test")

        def testMethod():
            a.append(1)
            raise RuntimeError("test")
            

        t = scheduler.tasklet()
        t.dont_raise = True
        t.context_manager_getter = CtxMgr
        t.bind(testMethod)
        t.setup()

        self.assertRaises(TypeError, scheduler.run)

        self.assertEqual(a, [ (1, t), 1, (2, t) ])

    def test_exception_handler(self):
        def testMethod():
            raise TypeError("test")

        info = []

        def exception_handler(infostring):
            import sys
            type, _, _ = sys.exc_info()
            info.append(type)

        t = scheduler.tasklet()
        t.dont_raise = True
        t.bind(testMethod)
        t.setup()
        t.exception_handler = exception_handler
        scheduler.run()

        self.assertEqual(info, [TypeError])

    def test_exception_handler_none(self):
        def testMethod():
          raise TypeError("test")

        t = scheduler.tasklet()
        t.dont_raise = True
        t.bind(testMethod)
        t.setup()
        t.exception_handler = None
        scheduler.run()

    def test_exception_handler_raises(self):
        def testMethod():
            raise TypeError("test")

        info = []

        def exception_handler(infostring):
            import sys
            type, _, _ = sys.exc_info()
            info.append(type)
            raise RuntimeError("this should not bubble up")

        t = scheduler.tasklet()
        t.dont_raise = True
        t.bind(testMethod)
        t.setup()
        t.exception_handler = exception_handler
        scheduler.run()

        self.assertEqual(info, [TypeError])

    def test_new_tasklets_cleanup_on_thread_finish(self):
        ''' Test that tasklets belonging to a finished thread are removed from channel. '''
        import threading
        c = scheduler.channel()

        tasklet = [None]

        def thread_func():
            tasklet[0] = scheduler.tasklet(lambda:None)()

        thread = threading.Thread(target=thread_func)
        thread.start()
        thread.join()

        # There should now only be one reference remaining (2 for sys.getrefcount)
        # Indicates that Tasklet reference held by thread schedule manager is removed
        self.assertEqual(sys.getrefcount(tasklet[0]),2)
        tasklet[0] = None 

    def test_partially_complete_tasklets_cleanup_on_thread_finish(self):
        ''' Test that tasklets belonging to a finished thread are removed from channel. '''
        import threading

        tasklet = [None]
        testValue = [0]

        def callable():
            try:
                scheduler.schedule()
                # Code should never be reached
                testValue[0] = 1
            except scheduler.TaskletExit:
                # Will be called when thread finishes
                testValue[0] = 2

        def thread_func():
            tasklet[0] = scheduler.tasklet(callable)()
            tasklet[0].run()

        thread = threading.Thread(target=thread_func)
        thread.start()
        thread.join()

        self.assertEqual(testValue[0],2)

        # There should now only be one reference remaining (2 for sys.getrefcount)
        self.assertEqual(sys.getrefcount(tasklet[0]),2)
        tasklet[0] = None