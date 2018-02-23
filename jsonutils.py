'''jsonutils.py

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
Date: February 23 2018
'''
import json
import difflib


def jpath(root, path, setdata=None):
  path_parts = path.strip('/').split('/')
  if setdata is not None:
    if len(path_parts) == 1:
      elem = root
    else:
      elem = jpath(root, '/'.join(path_parts[:-1]))
    elem[path_parts[-1]] = setdata
    return
  elem = root
  for p in path_parts:
    try:
      p = int(p)
      if type(elem) == list:
        elem = elem[p]
      else:
        elem = elem.get(p) 
    except ValueError:
      if type(elem) == dict:
        elem = elem.get(p, None)
      else:
        #raise ValueError('Invalid path: %s at node: %s' % (path, p))
        return None
  return elem


def jpath_create_dicts(root, path):
  path_parts = path.strip('/').split('/')
  elem = root
  for p in path_parts:
    if not p in elem:
      elem[p] = {}
    elem = elem[p]
  

def jpath_delete(root, path):
  if jpath(root, path) is None:
    return
  path_parts = path.strip('/').split('/')
  if len(path_parts) == 0:
    return
  if len(path_parts) == 1:
    parent = root
  else:
    parent = jpath(root, '/'.join(path_parts[:-1]))
  del parent[path_parts[-1]]

def jsondiff(a, b, verbose=True):
  alines = json.dumps(a, sort_keys=True, indent=2).split('\n')
  blines = json.dumps(b, sort_keys=True, indent=2).split('\n')
  match = True
  for x in difflib.context_diff(alines, blines):
    match = False
    if verbose:
      print x
    else:
      break
  return match

def jsondiff2(a, b, verbose=True, printlen=44, path=[]):
  # Should use difflib.SequenceMatcher with hashes of list elements to do
  # diff of lists.
  if type(a) in [str, unicode, int, bool]:
    if type(b) != type(a):
      if verbose:
        print '--- %s' % path
        print '<\ttype was %s: %s' % (type(a), repr(a)[:printlen])
        print '>\ttype now %s: %s' % (type(b), repr(b)[:printlen])
      return False
    if a != b:
      if verbose:
        print '--- %s' % path
        print '<\t%s' % (repr(a)[:printlen])
        print '>\t%s' % (repr(b)[:printlen])
      return False
  elif type(a) == list:
    if type(b) != list:
      if verbose:
        print '--- %s' % path
        print '<\t    list: %s' % (repr(a)[:printlen])
        print '>\tnon-list: %s' % (repr(b)[:printlen])
      return False
    match = True
    if len(a) != len(b):
      match = False
    if verbose:
      i_a = 0
      i_b = 0
      rem_a = []
      add_b = []
      while i_a < len(a):
        if jsondiff(a[i_a], b[i_b], False, printlen, path+[i_a]):
          i_b += 1
          i_a += 1
        else:
          match = False
          foundahead = False
          for j in xrange(10):
            if i_b+j < len(b):
              if jsondiff(a[i_a], b[i_b+j], False, 0, []):
                add_b.extend(range(i_b, i_b+j))
                i_b = i_b+j
                foundahead = True
                break
            else:
              break
          if not foundahead:
            jsondiff(a[i_a], b[i_b], verbose, printlen, path+[i_a])
            rem_a.append(i_a)
          i_a += 1
      if i_b < len(b):
        match = False
        add_b.extend(range(i_b, len(b)))
      if rem_a or add_b:
        print '--- %s' % path
      for i in rem_a:
        print '-\t[%d]: %s' % (i, repr(a[i])[:printlen])
      for i in add_b:
        print '+\t[%d]: %s' % (i, repr(b[i])[:printlen])
    if not match:
      return False
  elif type(a) == dict:
    if not type(b) == dict:
      if verbose:
        print '--- %s' % path
        print '<\t    dict: %s' % (repr(a)[:printlen])
        print '>\tnon-dict: %s' % (repr(b)[:printlen])
      return False
    match = True
    extra_b = set(b.keys())
    printlines = []
    for k in sorted(a.iterkeys()):
      if k in b:
        extra_b.remove(k)
        if not jsondiff(a[k], b[k], verbose, printlen, path+[k]):
          match = False
      else:
        printlines.append('-\t%s: %s' % (k, repr(a[k])[:printlen]))
        match = False
    for k in extra_b:
      printlines.append('+\t%s: %s' % (k, repr(b[k])[:printlen]))
      match = False
    if verbose and printlines:
      print '--- %s' % path
      for line in printlines:
        print line
    if not match:
      return False
  else:
    raise ValueError('Unexpected element type: %s' % type(a))
  return True


def Test():
  import copy
  r = {'testroot':{'testroot1':[{'list1':1},{'list2':2}],'testroot2':'foo'}}
  rcopy = copy.deepcopy(r)
  assert(jpath(r, 'testroot/testroot1/1/list2') == 2)
  assert(jpath(r, '/testroot/testroot2/') == 'foo')
  assert(jpath(r, 'notreal') == None)
  assert(jpath(r, '/testroot/notreal') == None)
  jpath(r, 'newroot', {'newroot1':'bar'})
  assert(jpath(r, 'newroot/newroot1') == 'bar')
  jpath_create_dicts(r, 'newrootcreate/newrootcreate1/newrootcreate2')
  assert(jpath(r, 'newrootcreate/newrootcreate1/newrootcreate2') == {})
  jpath(r, 'newrootcreate/newrootcreate1/newrootcreate2', 'baz')
  assert(jpath(r, 'newrootcreate/newrootcreate1/newrootcreate2') == 'baz')
  jpath(r, 'newrootcreate/newrootcreate11', 'baz11')
  for i in xrange(2):
    jpath_delete(r, 'newrootcreate/newrootcreate1')
    assert(jpath(r, 'newrootcreate/newrootcreate1') == None)
    assert(jpath(r, 'newrootcreate/newrootcreate11') == 'baz11')
  assert(jsondiff(rcopy, r, verbose=False) == False)
  jpath_delete(r, 'newrootcreate')
  jpath_delete(r, 'newroot')
  jpath_create_dicts(r, 'newrootlist')
  jpath(r, 'newrootlist/testlist', ['list1',{'listdict':2}])
  assert(jpath(r, 'newrootlist/testlist/0') == 'list1')
  jpath(r, 'newrootlist/testlist/1/listdict', 3)
  assert(jsondiff(rcopy, r, verbose=False) == False)
  jpath_delete(r, 'newrootlist')
  assert(jsondiff(rcopy, r, verbose=True) == True)
  print 'Tests passed.'
 

if __name__ == '__main__':
  Test()
