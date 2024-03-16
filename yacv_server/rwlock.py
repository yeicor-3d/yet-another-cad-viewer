# -*- coding: utf-8 -*-
""" rwlock.py

    A class to implement read-write locks on top of the standard threading
    library.

    This is implemented with two mutexes (threading.Lock instances) as per this
    wikipedia pseudocode:

    https://en.wikipedia.org/wiki/Readers%E2%80%93writer_lock#Using_two_mutexes

    Code written by Tyler Neylon at Unbox Research.

    This file is public domain.
"""

# _______________________________________________________________________
# Imports

from contextlib import contextmanager
from threading import Lock


# _______________________________________________________________________
# Class

class RWLock(object):
    """ RWLock class; this is meant to allow an object to be read from by
        multiple threads, but only written to by a single thread at a time. See:
        https://en.wikipedia.org/wiki/Readers%E2%80%93writer_lock

        Usage:

            from rwlock import RWLock

            my_obj_rwlock = RWLock()

            # When reading from my_obj:
            with my_obj_rwlock.r_locked():
                do_read_only_things_with(my_obj)

            # When writing to my_obj:
            with my_obj_rwlock.w_locked():
                mutate(my_obj)
    """

    def __init__(self):

        self.w_lock = Lock()
        self.num_r_lock = Lock()
        self.num_r = 0

    # ___________________________________________________________________
    # Reading methods.

    def r_acquire(self, *args, **kwargs):
        self.num_r_lock.acquire(*args, **kwargs)
        self.num_r += 1
        if self.num_r == 1:
            self.w_lock.acquire(*args, **kwargs)
        self.num_r_lock.release()

    def r_release(self, *args, **kwargs):
        assert self.num_r > 0
        self.num_r_lock.acquire(*args, **kwargs)
        self.num_r -= 1
        if self.num_r == 0:
            self.w_lock.release()
        self.num_r_lock.release()

    @contextmanager
    def r_locked(self, *args, **kwargs):
        """ This method is designed to be used via the `with` statement. """
        try:
            self.r_acquire(*args, **kwargs)
            yield
        finally:
            self.r_release()

    # ___________________________________________________________________
    # Writing methods.

    def w_acquire(self, *args, **kwargs):
        self.w_lock.acquire(*args, **kwargs)

    def w_release(self):
        self.w_lock.release()

    @contextmanager
    def w_locked(self, *args, **kwargs):
        """ This method is designed to be used via the `with` statement. """
        try:
            self.w_acquire(*args, **kwargs)
            yield
        finally:
            self.w_release()
