'''merge_doi_maps.py

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
import sys
import collections

import tsvfile

merge_into_tsv = sys.argv[1]
merge_new_tsvs = sys.argv[2:]

def merge(merge_into_tsv, merge_new_tsv):
  print 'Merge %s <-- %s' % (merge_into_tsv, merge_new_tsv)
  rows = tsvfile.ReadDicts(merge_into_tsv)
  update_rows = tsvfile.ReadDicts(merge_new_tsv)

  prev_map_id = dict([(x['Local ID'], x['DOI']) for x in rows])
  prev_map_doi = dict([(x['DOI'], x['Local ID']) for x in rows])

  if len(prev_map_id) != len(rows):
    raise ValueError('Non-unique local IDs in %s' % merge_into_tsv)
  if len(prev_map_doi) != len(rows):
    raise ValueError('Non-unique DOIs in %s' % merge_into_tsv)

  counters = collections.defaultdict(int)
  for row in update_rows:
    counters['total'] += 1
    local_id = row['Local ID']
    doi = row['DOI']
    needs_update = True
    if local_id in prev_map_id:
      if prev_map_id[local_id] != doi:
        raise ValueError('Conflicted local ID in %s: %s' % (
          merge_new_tsv, local_id))
      needs_update = False
    if doi in prev_map_doi:
      if prev_map_doi[doi] != local_id:
        raise ValueError('Conflicted DOI in %s: %s' % (merge_new_tsv, doi))
      needs_update = False
    if needs_update:
      counters['update'] += 1
      prev_map_id[local_id] = doi
      prev_map_doi[doi] = local_id
      rows.append(row)
    else:
      counters['preexisting'] += 1

  print str(dict(counters))
  tsvfile.WriteDicts(merge_into_tsv, rows)

for f in merge_new_tsvs:
  merge(merge_into_tsv, f)
