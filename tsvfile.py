'''tsvfile.py -- Helper methods for tabular data in tab-delimited files.

Copyright 2014 Garth Griffin
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
Date: August 5, 2014. Adapted from code written in 2011 for twit-hax project.

This module defines several helper methods for working with tabular data in
tab-delimited files.
'''
import os
import collections
import csv
import itertools


def ReadDicts(infile):
  '''ReadDicts
  
  Reads tab-delimited data from a file and returns a list of dicts for the rows.

  See also: WriteDicts

  Params:
    infile: File path of the tab-delimited file to read.

  Returns:
    A list of dicts where each row is represented with one dict.
  '''
  with open(infile, 'rbU') as fid:
    reader = csv.DictReader(fid, delimiter='\t')
    rows = list(reader)
  return rows

def WriteDicts(outfile, rows, tempfile=None):
  '''WriteDicts

  Writes tabular data in a list of dicts to a tab-delimited file.

  See also: ReadDicts

  If tempfile is None, interrupting this method while writing can cause
  corrupted data in the file specified by outfile. Specify tempfile to use
  atomic rewrites.

  Params:
    outfile: Path of the output tab-delimited file to write.
    rows: The input data to write out, as a list of dicts.
    tempfile: Optional path to a temp file to provide atomic rewrite.
  '''
  header = sorted(list(set(itertools.chain(*[x.keys() for x in rows]))))
  if tempfile is not None:
    writeout = tempfile
  else:
    writeout = outfile
  with open(writeout, 'wb') as fid:
    writer = csv.DictWriter(fid, header, delimiter='\t')
    writer.writeheader()
    for row in rows:
      writer.writerow(row)
  if tempfile is not None:
    os.rename(tempfile, outfile)
  print 'Wrote %d rows to file: %s' % (len(rows), outfile)
  
def ReadOrInit(iofile):
  '''ReadOrInit

  Reads a tab-delimited file if it exists, or returns an empty list.

  See also: ReadDicts

  Params:
    infile: File path of the tab-delimited file to read.

  Returns:
    If infile exists, returns the contents of the file, otherwise an empty list.
  '''
  if os.path.isfile(iofile):
    rows = ReadDicts(iofile)
  else:
    rows = []
  return rows

def GroupBy(rows, fields, unique=False):
  '''GroupBy

  Groups a list of dicts according to a particular set of keys.

  Conceptually, this divides a tabular dataset of rows according the values of 
  the rows in the given set of columns. The result is a dict that groups the
  rows by the values they have in those columns.

  The unique parameter determines whether multiple matches in the given columns
  are grouped as a list (unique=False) or whether a single matching row is
  expected (unqiue=True).

  Params:
    rows: A list of dicts to be grouped.
    fields: The dict keys with which to group the input rows.
    unique: Optional boolean, set True to check for unique matches on fields.

  Returns:
    A dict mapping the values in column "fields" to the rows with that value.
  '''
  if type(fields) == str:
    keyfunc = lambda x: x[fields]
  elif type(fields) in (list, tuple):
    keyfunc = lambda x: tuple([x[y] for y in fields])
  else:
    raise ValueError('Paramter "fields" must be str, list, or tuple.')
  if unique:
    output = {}
    for row in rows:
      key = keyfunc(row)
      if key in output: raise ValueError('Non unique key: %s' % key)
      output[key] = row
  else:
    output = collections.defaultdict(list)
    for row in rows:
      output[keyfunc(row)].append(row)
  return dict(output)

def GroupByUnique(rows, fields):
  '''GroupByUnique

  Groups a list of dicts according to a particular set of unique keys.

  Equivalent to: GroupBy(rows, fields, True)

  Params:
    rows: A list of dicts to be grouped.
    fields: The dict keys with which to group the input rows.

  Returns:
    A dict mapping the values in column "fields" to the rows with that value.
  '''
  return GroupBy(rows, fields, True)
