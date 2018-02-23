'''timeout.py

Copyright 2018 Garth Griffin
Distributed under the GNU GPL v3. For full terms see the file LICENSE.

This file is part of PetitionsDataverse.

PetitionsDataverse is free software: you can redistribute it and/or
modify it under the terms of the GNU General Public License as published by the
Free Software Foundation, either version 3 of the License, or (at your option)
any later version.

PetitionsDataverse is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY
or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public License for
more details.

You should have received a copy of the GNU General Public License along with
PetitionsDataverse.  If not, see <http://www.gnu.org/licenses/>.
________________________________________________________________________________

Author: Garth Griffin (http://garthgriffin.com)
February 23 2018
'''
from functools import wraps
import errno
import os
import signal  # Unix only.

class TimeoutError(Exception):
  pass

'''
# WARNING: This is not thread-safe. Use only in single-threaded programs.
def timeoutdecorator(seconds=10):
  def decorator(func):
    def _handle_timeout(signum, frame):
      raise TimeoutError('Function timed out after %d seconds.' % seconds)

    def wrapper(*args, **kwargs):
      signal.signal(signal.SIGALRM, _handle_timeout)
            signal.alarm(seconds)
            try:
              result = func(*args, **kwargs)
            finally:
              signal.alarm(0)
            return result
        return wraps(func)(wrapper)
    return decorator
'''

def timeout(func, seconds=10):
  def _handle(signum, frame):
    raise TimeoutError('Function timed out after %d seconds.' % seconds)
  signal.signal(signal.SIGALRM, _handle)
  signal.alarm(seconds)
  try:
    result = func()
  finally:
    signal.alarm(0)
  return result
