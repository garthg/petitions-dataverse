'''jsonformatter.py

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
from datetime import datetime
import sys
import re
import copy
import json
import jsonutils
from jsonutils import jpath

    

class FormatToJson(object):
  CONTROLLED_VOCABULARIES = set([
    'country',
    'subject',
    ])

  @staticmethod
  def _field(name, value, childnames=[], unroll_as_list=False, 
      type_compound_force=None):
    ismult = (type(value) == list)
    if type_compound_force is not None:
      iscompound = type_compound_force
    else:
      iscompound = ismult
    if iscompound:
      if unroll_as_list:
        value = [{childnames[i]:FormatToJson._field(childnames[i], value[i])}
          for i in xrange(len(value))]
      else:
        value = [dict([
          (childnames[i], FormatToJson._field(childnames[i], value[i]))
          for i in xrange(len(value))])]
    if iscompound:
      typeclass = u'compound'
    else:
      if name in FormatToJson.CONTROLLED_VOCABULARIES:
        typeclass = u'controlledVocabulary'
        if type(value) is str:
          value = unicode(value)
      else:
        typeclass = u'primitive'
    output = {
        u'typeName':name,
        u'multiple':ismult,
        u'value':value,
        u'typeClass':typeclass,
        }
    return output

  @staticmethod
  def _keyword_field(keyword_string):
    keyword_re = re.compile(r'([a-z-]*):"([^"]*)",?')
    keyword_entries = keyword_re.findall(keyword_string)
    keyword_entries = filter(lambda x: 
        len(x[0].strip())>0 and len(x[1].strip())>0,
        keyword_entries)
    if not keyword_entries: return output
    keyword_entries.sort()
    fields = [
        {
        'keywordVocabulary':FormatToJson._field('keywordVocabulary',vocab),
        'keywordValue':FormatToJson._field('keywordValue',text)
        }
        for vocab,text in keyword_entries
        ]
    output = FormatToJson._field('keyword', [])
    output['value'] = fields
    return output

  @staticmethod
  def _citation_field(citation, url):
    return {
        u'typeName':'publication',
        u'multiple':True,
        u'value':[{
          'publicationCitation':FormatToJson._field('publicationCitation',
            citation),
          'publicationURL':FormatToJson._field('publicationURL', url)
          }],
        u'typeClass':u'compound'
        }

  @staticmethod
  def setrow(row, into={}):
    # Build citation metadata.
    citation = []
    citation.append(FormatToJson._field('title', row['Title']))
    citation.append(FormatToJson._field('author',
      [row['Author']], ['authorName']))
    citation.append(FormatToJson._field('datasetContact',
      [row['Dataverse Contact']], ['datasetContactEmail']))
    citation.append(FormatToJson._field('dsDescription', 
      [row['Description']], ['dsDescriptionValue']))
    if row.get('Dataverse Subject'):
      citation.append(FormatToJson._field('subject',
        [row['Dataverse Subject']], type_compound_force=False))
    citation.append(FormatToJson._keyword_field(row['Keywords']))
    if row.get('Publication Citation'):
      citation.append(FormatToJson._field('publication',
        [row['Publication Citation'], row['Publication URL']],
        ['publicationCitation', 'publicationURL']))
    if row.get('Production Date'):
      citation.append(FormatToJson._field('productionDate', 
        row['Production Date']))
    citation.append(FormatToJson._field('distributor',
      [row['Distributor'], 'Harvard Dataverse Network'],
      ['distributorName', 'distributorName'], unroll_as_list=True))
    citation.append(FormatToJson._field('dateOfDeposit', 
      datetime.utcnow().strftime('%Y-%m-%d')))
    if (row.get('Time Period Covered Start') and 
        row.get('Time Period Covered End')):
      citation.append(FormatToJson._field('timePeriodCovered',
        [row['Time Period Covered Start'], row['Time Period Covered End']],
        ['timePeriodCoveredStart', 'timePeriodCoveredEnd']))
    jsonutils.jpath_create_dicts(into, 'metadataBlocks/citation/fields')
    jpath(into, 'metadataBlocks/citation/fields', citation)
    jpath(into, 'metadataBlocks/citation/displayName', 'Citation Metadata')
    # Build geographic metadata.
    if row.get('Country/Nation'):
      geospatial = []
      if row.get('Geographic Coverage'):
        geospatial.append(FormatToJson._field('geographicCoverage',
          [row['Country/Nation'], row['Geographic Coverage']],
          ['country', 'city']))
      else:
        geospatial.append(FormatToJson._field('geographicCoverage',
          [row['Country/Nation']], ['country']))
      jsonutils.jpath_create_dicts(into, 'metadataBlocks/geospatial/fields')
      jpath(into, 'metadataBlocks/geospatial/fields', geospatial)
      jpath(into, 'metadataBlocks/geospatial/displayName', 
          'Geospatial Metadata')
    # Status fields from the bottom of the result.
    version_major = jpath(into, 'versionNumber')
    if version_major is None:
      jpath(into, 'versionNumber', 1)
      jpath(into, 'versionMinorNumber', 0)
    else:
      jpath(into, 'versionNumber', version_major)
      version_minor = jpath(into, 'versionMinorNumber')
      if version_minor is None:
        jpath(into, 'versionMinorNumber', 1)
      else:
        jpath(into, 'versionMinorNumber', version_minor+1)
    now_str = datetime.utcnow().strftime('%Y-%m-%dT%H:%H:%SZ')
    # TODO include these status lines?
    #jpath(into, 'lastUpdateTime', now_str)
    #jpath(into, 'createTime', now_str)
    #jpath(into, 'distributionDate', datetime.utcnow().strftime('%Y-%m-%d'))
    jpath(into, 'versionState', u'DRAFT')
    dbid = jpath(into, 'id')
    if dbid is not None:
      jpath(into, 'id', dbid)
    jsonutils.jpath_delete(into, 'releaseTime')
    return into
    

def Test():
  import os
  from datetime import timedelta
  import tsvfile
  testdata_dir = os.path.join(os.path.dirname(__file__), 'testdata')
  tempfile = os.path.join(testdata_dir, 'temp.json')
  infile_rows = os.path.join(testdata_dir, 'jsonformatter_input_testdata.tsv')
  infile_json = os.path.join(testdata_dir, 'jsonformatter_testdata.json')
  rows = tsvfile.ReadDicts(infile_rows)
  with open(infile_json) as fid:
    into = json.loads(fid.read())
  jsonutils.jpath_delete(into, 'files')
  prev = copy.deepcopy(into)
  FormatToJson.setrow(rows[0], into)
  with open(tempfile, 'w') as fid:
    outjson = json.dumps(into, indent=2)+'\n'
    fid.write(outjson)
  print 'Wrote %d characters to: %s' % (len(outjson), tempfile)
  with open(tempfile) as fid:
    test = json.loads(fid.read())
  #timefields = [
  #    'createTime',
  #    'distributionDate',
  #    'lastUpdateTime',
  #    ]
  #now = datetime.utcnow()
  #for field in timefields:
  #  val = jpath(test, field)
  #  assert(val is not None)
  #  parsetime = '%Y-%m-%d'
  #  if field.endswith('Time'):
  #    parsetime += 'T%H:%M:%SZ'
  #  assert((now - datetime.strptime(val, parsetime)) < timedelta(days=1))
  #  jpath(prev, field, '')
  #  jpath(test, field, '')
  jsonutils.jpath_delete(prev, 'releaseTime')
  prev_version = jpath(prev, 'versionMinorNumber')
  assert(prev_version != None)
  assert(prev_version+1 == jpath(test, 'versionMinorNumber'))
  jpath(prev, 'versionMinorNumber', '')
  jpath(test, 'versionMinorNumber', '')
  assert(jpath(test, 'versionState') == 'DRAFT')
  jpath(prev, 'versionState', '')
  jpath(test, 'versionState', '')
  for c in jpath(test, 'metadataBlocks/citation/fields'):
    if c['typeName'] in ['distributionDate', 'dateOfDeposit']:
      c['value'] = ''
  for c in jpath(prev, 'metadataBlocks/citation/fields'):
    if c['typeName'] in ['distributionDate', 'dateOfDeposit']:
      c['value'] = ''
  res = jsonutils.jsondiff(prev, test)
  assert(res)
  if os.path.exists(tempfile):
    os.remove(tempfile)
    print 'Removed temp file: %s' % tempfile
  print ''
  print 'Passed test.'


if __name__ == '__main__':
  Test()
