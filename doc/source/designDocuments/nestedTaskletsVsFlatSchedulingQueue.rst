Nested Tasklets vs Flat Scheduling Queue
========================================

Tasklets execution order initially was designed to match Stackless.

Inserted Tasklets are added to the back of the Schedule Managers queue.

When processing :py:func:`scheduler.run` Tasklets are evaluated from the front of the queue.

This changes however if :py:func:`tasklet.run` is called.

:py:func:`scheduler.run` creates something resembling nesting.

This is best demonstraited by example.

.. code-block:: python

    import scheduler
    def foo(i):
        print(i)

    def bar():
        t4 = scheduler.tasklet(foo)("Dog")
        t5 = scheduler.tasklet(foo)("Cat")
        t6 = scheduler.tasklet(foo)("Monkey")
        t4.run()
        print("End of Tasklet")

    t1 = scheduler.tasklet(foo)("Rabbit")
    t2 = scheduler.tasklet(bar)()
    t3 = scheduler.tasklet(foo)("Donkey")

    scheduler.run()

The above code will produce the output:

.. code-block::

   >>>Rabbit
   >>>Dog
   >>>Cat
   >>>Monkey
   >>>End of Tasklet
   >>>Donkey

As can be seen, even though :py:func:`tasklet.run` was only called on ``t4``, ``t5`` and ``t6`` were also run before ``t3`` that was added to the queue before them.

This nesting behaviour can produce complex heirarchies that can be hard to follow and counterintuitive.

Historically this has also lead to cases where greenlet scheduling and carbon-scheduler could diverge ending in switching to Tasklets that have already been cleaned up.

The most complex code in carbon-scheduler is directly related to support for this nesting execution order.

It is hard to see what benefit we get from supporting nested tasklets. Especially when considering that :py:func:`scheduler.schedule` will move a Tasklet out of the nest so it cannot be treated like an isolated scheduling area.

It is also worth noting that currently time and tasklet limited runs using PyScheduler_RunWithTimeout or :py:func:`scheduler.run_n_tasklets` do not evaluate timeouts on nested Tasklets. This
is only a limitation currently to keep the codebase clean. It is possible.

Flat Scheduling Queue
---------------------
carbon-scheduler offers the option to turn off Tasklet execution nesting via :py:func:`scheduler.set_use_nested_tasklets`.

Currently this is optional and not default at present. However, if adopted by our products, support for Nested Tasklets would be reevaluated as removal would greatly simplify the carbon-scheduler codebase.

Benefits of flat scheduling:

1. Reduced complexity of Tasklet execution order.
2. Provides more logical execution order that behaves more as a consumer may expect
3. Reduced liklihood of discovering new situations leading to invalid memory crashes.
4. Time and Tasklet limit evaluation is evaluated for each Tasklet switch.
5. An extra yield is introduced resulting in more frequent timeout checks.

The downside is that this approach results in divergence between Stackless and carbon-scheduler for Tasklet execution order.

Flat scheduling execution order preserves logical assumptions.

Again it is simpler to show by example. Here is the same example as above and how it changes.

.. code-block:: python

    import scheduler
    def foo(i):
        print(i)

    def bar():
        t4 = scheduler.tasklet(foo)("Dog")
        t5 = scheduler.tasklet(foo)("Cat")
        t6 = scheduler.tasklet(foo)("Monkey")
        t4.run()
        print("End of Tasklet")

    t1 = scheduler.tasklet(foo)("Rabbit")
    t2 = scheduler.tasklet(bar)()
    t3 = scheduler.tasklet(foo)("Donkey")

    scheduler.run()

The above code will produce the output:

.. code-block::

   >>>Rabbit
   >>>Dog
   >>>End of Tasklet
   >>>Donkey
   >>>Cat
   >>>Monkey

This time :py:func:`tasklet.run`  called on ``t4`` only changes the execution order of ``t4``.

The rest of the execution order simply remains dictated by the order the Tasklets were created.