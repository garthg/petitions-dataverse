"""dataversehelper.py

Copyright 2018 Garth Griffin.
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
"""
import sys
import requests
import urllib
import os
import json
import httplib2
from xml import etree
import zipfile
import io
from StringIO import StringIO


class DataverseHelper(object):
  dataverse_server = 'dataverse.harvard.edu'  # Production.

  def __init__(self, api_key, dataverse_object_or_name='', 
      entity_id_cache_file=None, server=None):
    self.api_key = api_key
    self.dataverse_server = (server if server else
        DataverseHelper.dataverse_server)
    self.api_base_url = 'https://%s/api' % self.dataverse_server
    self.query_base_url = '%s/search?key=%s&show_entity_ids=true&q=' % (
        self.api_base_url, api_key)
    self.entity_id_cache_file = entity_id_cache_file
    if entity_id_cache_file is not None:
      if os.path.isfile(entity_id_cache_file):
        with open(entity_id_cache_file) as fid:
          cache_string = fid.read()
          self.entity_id_cache = json.loads(cache_string)
          print 'Loaded %d cache entries from file: %s' % (
              len(self.entity_id_cache), entity_id_cache_file)
      else:
        print >>sys.stderr, 'Initializing empty cache from file: %s' % (
            entity_id_cache_file)
        self.entity_id_cache = {}
    else:
      print >>sys.stderr, 'Initializing memory-only cache.'
      self.entity_id_cache = {}
    self.dataverse_connection = None
    if isinstance(dataverse_object_or_name, basestring):
      self.dataverse_object = None
      self.dataverse_name = dataverse_object_or_name
    else:
      self.dataverse_object = dataverse_object_or_name

  @staticmethod
  def _httpget(url, asjson=True):
    resp, content = httplib2.Http().request(url)
    if not resp['status'] == '200':
      print content
      raise RuntimeError('URL request failed: %s' % url)
    if asjson:
      content = json.loads(content)
    return content

  def query(self, query, unique=True):
    url = self.query_base_url + urllib.quote(query)
    print 'Run query%s: %s --> %s' % ((' (unique)' if unique else ''), query, 
        url)
    data = self._httpget(url)
    if not data.get('status') == 'OK':
      raise RuntimeError('Query failed bad status "%s": %s' % (
        data.get('status'), url))
    result_container = data.get('data')
    if not result_container:
      raise RuntimeError('Query failed with no data: %s' % url)
    results = result_container.get('items')
    if results is None:
      raise RuntimeError('Query failed with no items: %s' % url)
    if unique and len(results) == 0:
      return None
    if unique and len(results) > 1:
      raise RuntimeError('Multiple matches for unique query: %s' % url)
    if unique:
      return results[0]
    return results

  def get_study_header(self, doi):
    result = self.query('dsPersistentId:"'+doi.replace(':','\\:')+'"', True)
    if result is None:
      return None
    if not result.get('global_id') == doi:
      raise RuntimeError('Query returned unmatched doi "%s": %s' % (
        result.get('global_id'), url))
    return result
  
  def _get_entity_id(self, doi):
    data = self.get_study_header(doi)
    if data is None:
      return None
    return data['entity_id']

  def set_entity_id(self, doi, entity_id):
    self.entity_id_cache[doi] = entity_id
    if self.entity_id_cache_file is not None:
      with open(self.entity_id_cache_file, 'w') as fid:
        fid.write(json.dumps(self.entity_id_cache, indent=2))
      print >>sys.stderr, 'Wrote %d entries to cache file: %s' % (
          len(self.entity_id_cache), self.entity_id_cache_file)

  def get_entity_id(self, doi):
    if not doi in self.entity_id_cache:
      entity_id = self._get_entity_id(doi)
      if entity_id is not None:
        self.set_entity_id(doi, entity_id)
      return entity_id
    return self.entity_id_cache[doi]

  def get_study_metadata(self, doi, version='latest'):
    # Set version=None to retrieve a list containing the data for ALL versions.
    entity_id = self.get_entity_id(doi)
    if entity_id is None:
      raise ValueError('Dataset DOI %s not found.' % doi)
    # URL adapted from Python wrapper:
    # https://github.com/IQSS/dataverse-client-python/blob/master/dataverse/dataset.py
    if version is not None:
      url = '{0}/datasets/{1}/versions/:{2}?key={3}'.format(
          self.api_base_url,
          entity_id,
          version,
          self.api_key
          )
    else:
      url = '{0}/datasets/{1}/versions/?key={2}'.format(
          self.api_base_url, 
          entity_id, 
          self.api_key
          )
    data = self._httpget(url)
    if not data['status'] == 'OK':
      raise RuntimeError('Bad Dataverse API status %s from URL: %s' % (
        data['status'], url))
    if not 'data' in data or not data['data']:
      raise RuntimeError('No Dataverse API data returned from URL: %s' % (url))
    return data['data']

  def update_study_metadata(self, doi, metadata):
    entity_id = self.get_entity_id(doi)
    # URL adapted from Python wrapper:
    # https://github.com/IQSS/dataverse-client-python/blob/master/dataverse/dataset.py
    url = '{0}/datasets/{1}/versions/:draft'.format(
        self.api_base_url,
        entity_id
        )
    resp = requests.put(
        url,
        headers={'Content-Type': 'application/json'},
        data=json.dumps(metadata),
        params={'key': self.api_key},
        )
    if resp.status_code != 200:
      raise RuntimeError('Failed: %s %s' % (str(resp), resp.content))
    updated_metadata = resp.json()['data']
    return updated_metadata

  def _get_current_dataverse(self):
    if self.dataverse_object:
      return self.dataverse_object
    import dataverse  # Import here in case not installed.
    conn = dataverse.Connection(self.dataverse_server, self.api_key)
    dv = conn.get_dataverse(self.dataverse_name)
    if not dv:
      raise RuntimeError('No dataverse found with name: %s' % 
          self.dataverse_name)
    print 'Connected to dataverse'
    return dv

  def _get_edit_uri_base_BROKEN(self):
    # TODO This should not be hardcoded.
    # However, the below calls to dataverse are failing because the call to 
    # get_collection_info() is failing on large results.
    return 'https://dataverse.harvard.edu/dvn/api/data-deposit/v1.1/swordv2/edit/study/'
    print 'Loading edit uri from collection info'
    try:
      import dataverse
    except ImportError:
      print >>sys.stderr, 'WARNING: Continuing without "dataverse" module.'
      return 'https://dataverse.harvard.edu/dvn/api/data-deposit/v1.1/swordv2/edit/study/'
    conn = dataverse.Connection(self.dataverse_server, self.api_key)
    #edit_uri = conn.sword_base_url+'/edit/study/'  # Not sure why this breaks.
    #print edit_uri
    #return edit_uri
    # This is fragile, it would be better to get the edit_uri some other way.
    dv = self._get_current_dataverse()
    dv_info = dv.get_collection_info()
    print 'Loaded collection info'
    entry_text = dv_info[dv_info.find('<entry'):dv_info.find('</entry>')+8]
    root = etree.ElementTree.fromstring(entry_text)
    links = filter(lambda x: x.tag == 'link' and x.get('rel') == 'edit-media',
        root)
    if not links:
      raise RuntimeError('Failed to find <link rel="edit-media"> element.')
    link = links[0]
    full_href = link.get('href')
    base = full_href[:full_href.find('/study/doi:')+7]
    print 'Parsed edit URL base: %s' % base
    return base

  def get_edit_media_uri(self, doi):
    # TODO not hardcoded
    return 'https://{0}/dvn/api/data-deposit/v1.1/swordv2/edit-media/study/{1}'.format(self.dataverse_server, doi)

  def get_edit_uri(self, doi):
    return 'https://{0}/dvn/api/data-deposit/v1.1/swordv2/edit/study/{1}'.format(self.dataverse_server, doi)

  def get_doi_from_search(self, query):
    result = self.query(query, True)
    if not result:
      print 'No result for query: %s' % query
      return None
    if not 'global_id' in result or not result['global_id']:
      raise RuntimeError('Bad result field global_id from query: %s' % query)
    return result['global_id']

  def create_blank_study_BROKEN(self):
    import dataverse  # Import here in case it's not installed.
    if not self.dataverse_connection:
      self.dataverse_connection = dataverse.Connection(self.dataverse_server,
          self.api_key)
    dv_list = self.dataverse_connection.get_dataverses()
    if not dv_list:
      raise RuntimeError('No dataverse found.')
    if len(dv_list) > 1:
      raise RuntimeError('Too many available dataverses.')
    curr_dv = dv_list[0]
    dataset = curr_dv.create_dataset(
        'untitled', 
        'This study is intentionally blank, set up via automation.',
        'Dataverse API Creator')
    if not dataset:
      raise RuntimeError('Failed to create dataset.')
    self.set_entity_id(dataset.doi, dataset.id)
    return dataset


  def upload_file_BROKEN(self, doi, filepath):
    buf = StringIO()
    zip_file = zipfile.ZipFile(buf, 'w')
    zip_file.write(filepath)
    zip_file.close()
    data = buf.getvalue()
    headers = {
        'Packaging': 'http://purl.org/net/sword/package/SimpleZip', 
        'Content-Type': 'application/zip', 
        'Content-Disposition': 'filename=temp.zip'
        }
    auth = self._get_current_dataverse().connection.auth
    r = requests.post(self.get_edit_media_uri(doi), data=data, headers=headers,
        auth=auth)
    r.raise_for_status()

  def publish_study(self, doi):
    r = requests.post(
        self.get_edit_uri(doi),
        headers={'In-Progress': 'false', 'Content-Length': '0'},
        auth=(self.api_key, None),
        )
    r.raise_for_status()

  def create_and_publish_new_study(self,
      title='untitled',
      description='This study is intentionally blank, set up via automation.',
      creator='Dataverse API creator'
      ):
    import dataverse
    dv = self._get_current_dataverse()
    # Set up the Dataset to be created.
    dataset = dataverse.Dataset(
        title=title,
        description=description,
        creator=creator
        )
    # Add the Dataset to the Dataverse.
    # TODO remove these two lines and just use dv.collection.get('href')
    #url = dv.collection.get('href').replace('beta.harvard.edu', 'beta.dataverse.org')
    url = dv.collection.get('href')
    print 'resp = requests.post(%r,\n  data="<entry xmlns=...>...</entry>",\n  headers={"Content-type": "application/atom+xml"},\n  auth=(my_api_key, None))' % (url)
    resp = requests.post(
        #dv.collection.get('href'),
        url,
        data=dataset.get_entry(),
        headers={'Content-type': 'application/atom+xml'},
        auth=dv.connection.auth,
        )
    if resp.status_code != 201:
      raise RuntimeError('Failed to add newly created dataset to Dataverse.')
    # Parse the content ID from the result.
    content_id = dataverse.utils.get_element(resp.content, 'id')
    doi = content_id.text.split('study/')[-1]
    # Publish the newly-uploaded Dataset so we can find its entity ID later.
    edit_uri = dataverse.utils.get_element(resp.content,
        tag='link', 
        attribute='rel', 
        attribute_value='edit').get('href')
    self.publish_study(doi)
    dataset._id = self.get_entity_id(doi)
    return dataset


if __name__ == '__main__':
  api_key = sys.argv[1]

  # This block for test server.
  from datetime import datetime
  dvhelper = DataverseHelper(api_key, 'gwgtest', server='beta.dataverse.org')
  if dvhelper.get_doi_from_search('notreal'):
    raise RuntimeError('Problem!')
  test_description = 'This is a description '+str(datetime.utcnow())
  print test_description
  dataset = dvhelper.create_and_publish_new_study('new title', test_description)
  print dataset
  print dataset.doi
  print dataset._id
  test_metadata = json.loads(
      open('testdata/jsonformatter_testdata.json').read())
  #dvhelper.update_study_metadata(dataset.doi, test_metadata)
  #dataset.update_metadata(test_metadata)
  dvhelper.upload_file(dataset.doi, 'input_2016-11-18/petitions.xlsx')
  #dataset.publish()
  dvhelper.publish_study(dataset.doi)
  sys.exit(0)


  cache_file = 'dataverse_entity_ids.json'
  dvhelper = DataverseHelper(api_key, cache_file)

  '''
  # This block for creating an empty study.
  doi = dvhelper.create_blank_study()
  print 'Created study'
  print 'Created: %s' % doi
  print dvhelper.get_study_metadata(doi)
  sys.exit(0)
  '''
  

  '''
  # Read DOIs from a file.
  doi_file = sys.argv[2]
  with open(doi_file) as fid:
    dois = filter(None, [x.strip() for x in fid.readlines()])
  '''

  # Pass one DOI on the command line.
  dois = [sys.argv[2]]

  '''
  # Run a query from the command line to find a DOI.
  query = sys.argv[2]
  doi_result = dvhelper.get_doi_from_search(query)
  print '%s -> %s' % (query, doi_result)
  if not doi_result: raise RuntimeError('Failed to find DOI')
  dois = [doi_result]
  '''

  ctr = 0
  for doi in dois:
    ctr += 1
    print '%d/%d' % (ctr, len(dois))
    res = dvhelper.get_entity_id(doi)
    print '%s -> %s' % (doi, res)
    print json.dumps(dvhelper.get_study_metadata(doi), indent=2)
    #print json.dumps(dvhelper.get_study_header(doi), indent=2)
    #header = dvhelper.get_study_header(doi)
    #print header['name']
    #print header['url']
