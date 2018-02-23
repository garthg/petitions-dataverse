'''update.py

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


import sys
import json
import re
import os
import time
import copy
import collections
import traceback
import optparse
from datetime import datetime

import dataverse

import dataversehelper
import dataversewrapper
import jsonformatter
import tsvfile
import jsonutils
import timeout
import petitiondoiresolver


parser = optparse.OptionParser()
parser.add_option('--api_key', help='Dataverse API key (credentials.txt')
parser.add_option('--doi_tsv', 
    help='Dataverse local ID to DOI mapping tsv file (local_id_to_doi.tsv)')
parser.add_option('--input_tsv', 
    help='Study data input tsv file (ignored_outputs/studydata_*.tsv)')
parser.add_option('--attachment_file',
    help='Excel file to attach to the Study entries (input_*/*.xlsx)')
parser.add_option('--doi_updates_output_tsv',
    help='Output tsv file to write updates to DOI mapping')
parser.add_option('--dataverse_name',
    help='Name of the already-present Dataverse to populate Studies into.')
options, unused_args = parser.parse_args()
api_key = options.api_key
doi_tsv = options.doi_tsv
infile = options.input_tsv
study_data_filepath = options.attachment_file
doi_update_tsv = options.doi_updates_output_tsv
dataverse_name = options.dataverse_name

# Use these for test/dev keys.
dv_test_api_key = ''
dv_beta_api_key = ''
  
#commit = False
commit = True
show_diff = True
force_update_file = False
#force_update_file = True
USE_NON_PROD_SERVER = False  # Set False for production.
#USE_NON_PROD_SERVER = True

# Check this before initializing Dataverse object for speed.
if not os.path.isfile(study_data_filepath):
  raise ValueError('Study data filepath not found: %s' % study_data_filepath)

dvid_cache_file = 'dataverse_entity_ids.json'
debug_json_file = 'tmp_update_last_metadata.json'

if not USE_NON_PROD_SERVER:
  # Production
  dataverse_conn = dataverse.Connection('dataverse.harvard.edu', api_key)
  dataverse_obj = dataverse_conn.get_dataverse(dataverse_name)
  dvhelper = dataversehelper.DataverseHelper(api_key, dataverse_obj,
      dvid_cache_file)
else:
  # Beta server
  dataverse_conn = dataverse.Connection('beta.dataverse.org', dv_beta_api_key)
  #dataverse_conn = dataverse.Connection('apitest.dataverse.org', dv_test_api_key)
  dataverse_obj = dataverse_conn.get_dataverse(dataverse_name)
  dvhelper = dataversehelper.DataverseHelper(dv_beta_api_key, dataverse_obj,
      None, 'beta.dataverse.org')


doi_lookup = dict([(x['Local ID'], x['DOI']) for x in 
  tsvfile.ReadDicts(doi_tsv)])

rows = tsvfile.ReadDicts(infile)

# TODO remove
# if non-empty, will filter to only the IDs in the list
debug_local_ids = [
    ]

if len(debug_local_ids) > 0:
  rows = filter(lambda x: x['Local ID'] in debug_local_ids, rows)
  print 'Filtered to %d rows from %d debug_local_ids' % (len(rows), 
      len(debug_local_ids))


def coerce_utf8(data):
  if type(data) is unicode: return data
  return unicode(data.decode('utf8'))

def avoid_update_on_dates(published_metadata, local_metadata):
  citation_date_fields = ['dateOfDeposit', 'distributionDate']
  citation_date_indices = {}
  citation_date_rewrites = []
  citation_path = 'metadataBlocks/citation/fields'
  published_citation = jsonutils.jpath(published_metadata, citation_path)
  for i, block in enumerate(jsonutils.jpath(published_metadata, citation_path)):
    for field in citation_date_fields:
      if block['typeName'] == field:
        citation_date_indices[field] = [i, None]
        print 'Published citation date field: %s/%d/typeName:"%s"' % (
            citation_path, i, field)
  for i, block in enumerate(jsonutils.jpath(local_metadata, citation_path)):
    for field in citation_date_indices:
      if block['typeName'] == field:
        citation_date_indices[field][1] = i
  #for key, rewrites in citation_date_indices.iteritems():
  #  if rewrites[1] is None:
  #    raise RuntimeError(
  #        'DOI %s: Failed to find local field for citation date field: %s' % (
  #          doi, key))
  citation_date_rewrites = [(x, y[0], y[1]) for x,y in 
      citation_date_indices.items()]
  citation_date_rewrites.sort(key=lambda x: 
      (2, -1*x[1]) if x[2] is None else (1,1))
  for field, old, new in citation_date_rewrites:
    old_path = '%s/%d/value' % (citation_path, old)
    if new is None:
      jsonutils.jpath(local_metadata, citation_path).insert(
          old, jsonutils.jpath(published_metadata, 
            '%s/%d' % (citation_path, old)))
      new_path = '%s/%d/value' % (citation_path, old)
      print 'Avoid update on date: inserted %s:"%s"' % (
          new_path, jsonutils.jpath(local_metadata, new_path))
    else:
      new_path = '%s/%d/value' % (citation_path, new)
      print 'Avoid update on date: %s:"%s" rewritten %s:"%s"' % (
          new_path, jsonutils.jpath(local_metadata, new_path),
          old_path, jsonutils.jpath(published_metadata, old_path))
      jsonutils.jpath(local_metadata, new_path,
          jsonutils.jpath(published_metadata, old_path))

def update(row, commit=True, show_diff=True,
    counters=collections.defaultdict(int), doi_update_rows=[],
    force_update_file=False):
  global doi_lookup
  local_id = row['Local ID']
  doi = None
  dataset = None
  if local_id in doi_lookup:
    print 'DOI cache hit for local ID: %s' % local_id
    doi = doi_lookup[local_id]
  else:
    print 'DOI cache miss for local ID: %s' % local_id
    doi = petitiondoiresolver.resolve(dvhelper, row)
    if not doi:
      print 'No DOI found for local ID: %s' % local_id
      print 'Attempting to create new study...'
      counters['create'] += 1
      if commit:
        dataset = dvhelper.create_and_publish_new_study(row['Title'],
            coerce_utf8(row['Description']))
        for i in range(3):
          try:
            doi = dataset.doi
            break
          except dataverse.NoContainerError:
            print 'WARNING: NoContainerError, waiting 30 seconds and retrying (%d attempts left)...' % i
          time.sleep(30)
        if not doi:
          raise RuntimeError('Failed to create new study for ID: %s.' % 
              local_id)
        print 'Newly created DOI %s for ID %s' % (doi, local_id)
      else:
        print 'Not committing changes, no dataset creation, aborting.'
        return doi
  print 'Resolved %s -> %s' % (local_id, doi)
  if local_id not in doi_lookup:
    print 'Writing new DOI %s for local ID: %s' % (doi, local_id)
    doi_update_rows.append({'Local ID':row['Local ID'], 'DOI':doi})
    tsvfile.WriteDicts(doi_update_tsv, doi_update_rows)
  print '%s | Beginning incremental update %s at %s' % (doi,
      ('committing changes' if commit else 'preview'), datetime.utcnow())
  #published_metadata = study_obj.get_metadata('latest-published')
  published_metadata = dvhelper.get_study_metadata(doi, 'latest-published')
  print '%s | Loaded study metadata.' % doi
  # Make a local copy of metadata.
  update_base = copy.deepcopy(published_metadata)
  # Remove database state fields.
  jsonutils.jpath_delete(update_base, 'lastUpdateTime')
  jsonutils.jpath_delete(update_base, 'createTime')
  jsonutils.jpath_delete(update_base, 'distributionDate')
  jsonutils.jpath_delete(update_base, 'files')
  local_metadata = json.loads(json.dumps(
    jsonformatter.FormatToJson.setrow(row, update_base)))
  with open(debug_json_file, 'wb') as fid:
    fid.write(json.dumps(local_metadata, sort_keys=True, indent=2))
  print '%s | Wrote local metadata to: %s' % (doi, debug_json_file)
  if not force_update_file:
    # Keep same citation dates for diff
    avoid_update_on_dates(published_metadata, local_metadata)
  if show_diff: print '%s | Diff begin' % doi
  unchanged = jsonutils.jsondiff(published_metadata['metadataBlocks'],
      local_metadata['metadataBlocks'], verbose=show_diff)
  if show_diff: print '%s | Diff end' % doi
  has_file = len(published_metadata['files']) > 0
  if not force_update_file and unchanged and has_file:
    print '%s | No update required.' % doi
    counters['unchanged'] += 1
  else:
    print '%s | Updating...' % doi
    counters['update'] += 1
    if commit:
      if dataset is not None:
        print '%s | Using newly-created study object...' % doi
        study_obj = dataset
      else:
        print '%s | Loading study object...' % doi
        #study_obj = dataverse_obj.get_dataset_by_doi(doi)  # Now fails
        study_obj = dataverse.Dataset(
            dataverse=dataverse_obj, 
            edit_media_uri=dvhelper.get_edit_media_uri(doi),
            edit_uri=dvhelper.get_edit_uri(doi),
            title='title')
      if study_obj is None:
        raise RuntimeError('Failed to load Dataset object for DOI: %s' % doi)
      print '%s | Loading dataverse entity ID...' % doi
      study_obj._id = dvhelper.get_entity_id(doi)  # Fix never-ending lookup.
      print '%s | Created study object' % doi
      study_obj.update_metadata(local_metadata)
      print '%s | Put new metadata.' % doi
      result = study_obj.get_metadata(refresh=False)
      if not jsonutils.jsondiff(local_metadata['metadataBlocks'], 
          result['metadataBlocks']):
        raise RuntimeError('Updated metadata differs from local.')
      print '%s | Uploading filepath: %s' % (doi, study_data_filepath)
      for prev_file in study_obj.get_files(refresh=False):
        print '%s | Delete file: %s %s' % (doi, prev_file.id, prev_file.name)
        study_obj.delete_file(prev_file)
      dataset = dataversewrapper.WrapDataset(dataverse_obj, doi,
          dvhelper.get_entity_id(doi))
      dataset.upload_filepath(study_data_filepath)
      #dvhelper.upload_file(doi, study_data_filepath)
      time.sleep(5)  # Sleep because ingestion can create a race condition.
      print '%s | Upload finished.' % doi
      dvhelper.publish_study(doi)
      print '%s | Published' % doi
      print '%s | Update finished at %s.' % (doi, datetime.utcnow())
    else:
      print '%s | Preview only, no changes.' % doi
  return doi

ctr = 0
counters = collections.defaultdict(int)
doi_update_rows = []
for row in rows:
  ctr += 1
  local_id = row['Local ID']
  print '%s Processing %d/%d: %s' % (datetime.utcnow(), ctr, len(rows), 
      local_id)
  counters['total'] += 1
  last_fail_timeout = False
  def f():
    doi = update(row, commit=commit, show_diff=show_diff, 
        counters=counters, doi_update_rows=doi_update_rows, 
        force_update_file=force_update_file)
  try:
    if last_fail_timeout:
      print 'Previous attempt timed out, waiting 30 seconds...'
      time.sleep(30)
    timeout.timeout(f, 180)
    counters['success'] += 1
    last_fail_timeout = False
  except KeyboardInterrupt: raise KeyboardInterrupt
  except SystemExit: raise SystemExit
  except Exception, e:
    print 'ERROR on row %d: %s' % (ctr, traceback.format_exc())
    if type(e) is timeout.TimeoutError:
      counters['timeout'] += 1
      last_fail_timeout = True
    else:
      counters['error'] += 1
  print str(dict(counters))
print 'Consider running `python merge_doi_maps.py %s %s`' % (
    doi_tsv, doi_update_tsv)


