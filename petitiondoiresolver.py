'''petitiondoiresolver.py

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
import traceback
import sys
import os
import re
import collections
import dataversehelper
import tsvfile


resolver_fields = [
    'Date of creation',
    'Petition subject',
    'Original',
    'Petition location',
    'Legislator, committee, or address that the petition was sent to',
    'Selected signatures',
    'Total signatures',
    ]


def resolve(dataverse_helper_instance, row):
  description_html = row['Description']
  query_parts = description_html.split('</p>')
  query_parts_text = filter(None, [
      re.sub(r'  *', ' ', re.sub(r'<[^>]*>', ' ', x).strip())
      for x in query_parts])
  query_parts_text_filter = filter(
      lambda x: any([x.startswith(y) for y in resolver_fields]),
      query_parts_text)
  min_field_count = len(resolver_fields) - 2
  if len(query_parts_text_filter) < min_field_count:
    print 'Not enough query fields (found %d, need %d)' % (
        len(query_parts_text_filter), min_field_count)
    return None
  query = '"' + '" AND "'.join(query_parts_text_filter) + '"'
  doi = dataverse_helper_instance.get_doi_from_search(query)
  return doi


if __name__ == '__main__':
  api_key = sys.argv[1]  # `cat credentials.txt | tail -n 1`
  dataset_tsv = sys.argv[2]  # ignored_outputs/studydata_*.tsv
  entity_cache_file = sys.argv[3]  # dataverse_entity_ids.json
  outfile = sys.argv[4]  # ...

  cache = {}
  output_rows = []
  if os.path.isfile(outfile):
    print 'Outfile exists, reading finished rows...'
    output_rows = tsvfile.ReadDicts(outfile)
    cache = dict([(x['Local ID'], x['DOI']) for x in output_rows])
    print 'Loaded %d prior entries from outfile: %s' % (len(cache), outfile)

  rows = tsvfile.ReadDicts(dataset_tsv)
  dvhelper = dataversehelper.DataverseHelper(api_key, entity_cache_file)

  counters = collections.defaultdict(int)
  ctr = 0
  for row in rows:
    try:
      print str(dict(counters))
      ctr += 1
      local_id = row['Local ID']
      print 'Processing %d/%d: %s' % (ctr, len(rows), local_id)
      counters['total'] += 1
      if local_id in cache:
        print 'Cached, skipping %s' % local_id
        counters['skip'] += 1
        continue
      doi = resolve(dvhelper, row)
      if not doi:
        counters['failure'] += 1
        print '%s -> ???' % local_id
        continue
      counters['success'] += 1
      print '%s -> %s' % (local_id, doi)
      output_rows.append({
        'DOI':doi,
        'Local ID':local_id
        })
      tsvfile.WriteDicts(outfile, output_rows)
    except KeyboardInterrupt: raise KeyboardInterrupt
    except SystemExit: raise SystemExit
    except:
      print 'ERROR: %s' % traceback.format_exc()
      counters['error'] += 1

  print 'Finished %d rows' % len(rows)
  print str(dict(counters))
