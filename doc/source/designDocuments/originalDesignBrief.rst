Original Design Brief
=====================

TLDR
----
Create a Python 3.12 Cextension to offer required functionality from `Stackless Python <https://stackless.readthedocs.io/en/3.8-slp/stackless-python.html>`_ utilising `Greenlet <https://greenlet.readthedocs.io/en/latest/>`_.


Brief History
-------------

EVE Online was originally designed it was built atop of a flavour of Python 2.7 known as `Stackless Python <https://stackless.readthedocs.io/en/3.8-slp/stackless-python.html>`_.

    Stackless-Python is an enhanced version of the Python® programming language1. It allows programmers to reap the benefits of thread-based programming without the performance and complexity problems associated with conventional threads. The microthreads that Stackless adds to the Python® programming language are a cheap and lightweight convenience, which if used properly, can not only serve as a way to structure an application or framework, but by doing so improve program structure and facilitate more readable code.

From `Stackless Python <https://stackless.readthedocs.io/en/3.8-slp/stackless-python.html>`_

The tech that EVE Online was built atop was subsequently called Carbon and in 2023 it was decided to update Carbon to Python3.

Although there is support for `Stackless Python <https://stackless.readthedocs.io/en/3.8-slp/stackless-python.html>`_ up to Python 3.8, it was decided to not take on the work to update `Stackless Python <https://stackless.readthedocs.io/en/3.8-slp/stackless-python.html>`_ and instead invest the time to support Vanilla Python.

To achieve this a new Python cextension was to be required to offer the lost functionality that was previously provided by `Stackless Python <https://stackless.readthedocs.io/en/3.8-slp/stackless-python.html>`_.

Fortunately the core stack switching functionality central to `Stackless Python <https://stackless.readthedocs.io/en/3.8-slp/stackless-python.html>`_ had already been spun out and offered as module `Greenlet <https://greenlet.readthedocs.io/en/latest/>`_

    The “greenlet” package is a spin-off of Stackless, a version of CPython that supports micro-threads called “tasklets”.

From `Greenlet History <https://greenlet.readthedocs.io/en/latest/history.html>`_

The aim was to then create a new Python 3.12 Cextension to provide **some** of the original Tasklet and Channel logic of `Stackless Python <https://stackless.readthedocs.io/en/3.8-slp/stackless-python.html>`_ so it could be replaced in the Carbon codebase.

Only the functionality investigated as required for Carbon was to be reimplemented.

Following the Carbon component naming convention, the resulting Cextension is

carbon-scheduler

