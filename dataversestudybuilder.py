'''dataversestudybuilder.py -- Tools to format Study entries for a Dataverse.

Copyright 2014 Garth Griffin
Distributed under the GNU GPL v3. For full terms see the file LICENSE.

This file is part of AntislaveryPetitionsDataverse.

AntislaveryPetitionsDataverse is free software: you can redistribute it and/or
modify it under the terms of the GNU General Public License as published by the
Free Software Foundation, either version 3 of the License, or (at your option)
any later version.

AntislaveryPetitionsDataverse is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY
or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public License for
more details.

You should have received a copy of the GNU General Public License along with
AntislaveryPetitionsDataverse.  If not, see <http://www.gnu.org/licenses/>.
________________________________________________________________________________

Author: Garth Griffin (http://garthgriffin.com)
Date: August 6, 2014

This module provides tools for formatting data for Study entries in the Harvard
Dataverse Network [1].

The typical usage is to create a new DataverseStudyBuilder object for every
Study that is to be entered into a Dataverse. The methods of the 
DataverseStudyBuilder object are then used to add the content into the fields
for the Study.

If the Study will be exported to DDI XML, this will be done using the 
xmlformatter.py module, which should be included in the same folder as this
file. The valid field names for the Study object are defined in the 
xmlformatter.py module in the XML_FIELD_MAP structure. Generally speaking,
the field names are the same as what is seen in the Dataverse user interface
website [1].

For more information, contact Technical Support for the Harvard Institute for
Quantitative Social Science (IQSS) [2].

[1] https://thedata.harvard.edu/dvn/
[2] http://www.iq.harvard.edu/contact-us
'''

import re
import shutil
import os
import math
import traceback
from datetime import datetime

import xmlformatter


def HasNonblank(input_dict, key):
  '''HasNonblank

  Checks whether "input_dict" has a nonblank value for the key "key".

  Params:
    input_dict: Dict to check.
    key: Key to check in "input_dict".

  Returns:
    True if there is a nonblank value and false otherwise.
  '''
  return (
    key in input_dict and
    input_dict[key].strip())


def ParseBoolean(input_dict, key):
  '''ParseBoolean

  Parses a boolean value of the strings "yes" or "no" from input_dict[key].

  Params:
    input_dict: The dict containing the value to parse at key "key".
    key: The key of the value to parse.

  Returns:
    True if the value is like "yes", False if like "no", otherwise None.
  '''
  if HasNonblank(input_dict, key):
    value = input_dict[key].lower().strip()
    if value == 'na': return None
    if value == 'yes': return True
    if value == 'no': return False
    print 'Unrecognized boolean to parse: "%s"' % value
  return None


def ParseList(input_string, delimiter=','):
  '''ParseList

  Parses a list of strings from a single delimited sring.

  Params:
    input_string: The delimited string to parse.
    delimiter: Optional string of the delimiter, defaults to ",".

  Returns:
    A list of stripped strings parsed from the input string.
  '''
  return [x.strip() for x in input_string.split(delimiter)]


def ParseDate(input_date):
  '''ParseDate

  Converts an input date in a variety of formats into an ISO date string.

  Valid input formats include:
    YYYYMMDD as string
    YYYY as string
    YYYYMMDD as int
    YYYY as int
    YYYYMMDD as string in E notation (e.g. 1.8500101E7)

  Raises an error if no valid parsing was found.
  Replaces trailing zeros with 1: YYYY-MM-00 becomes YYYY-MM-01.

  Params:
    input_date: The input date string to parse.

  Returns:
    The date in ISO format YYYY-MM-DD.
  '''
  if ',' in input_date:
    return min([ParseDate(x.strip()) for x in input_date.split(',')])
  canonical = None
  full_matcher = re.compile(r'^(\d{4})(\d{2})(\d{2})$')
  year_matcher = re.compile(r'^(\d{4})$')
  if re.match(r'\d{4}-\d{2}-\d{2}', input_date):
    canonical = input_date
  elif full_matcher.match(input_date):
    canonical = re.sub(full_matcher, r'\1-\2-\3', input_date)
  elif year_matcher.match(input_date):
    return input_date
  else:
    # Then assume it's in scientific notation 1.8190527E7
    use_date = str(int(float(input_date)))
    if not full_matcher.match(use_date):
      raise ValueError('Failed to parse input date: "%s"' % input_date)
    canonical = re.sub(full_matcher, r'\1-\2-\3', use_date)
  # Verify that the canonical date string is legal.
  if canonical.endswith('00'):
    # Treat as the first of the month for 00.
    canonical = canonical[:-2]+'01'
  try:
    dateobject = datetime.strptime(canonical, '%Y-%m-%d')
  except ValueError, e:
    raise ValueError('Failed to parse input date: "%s"\n%s' % (
      input_date, traceback.format_exc(e)))
  return canonical


class DataverseStudyBuilder(object):
  '''DataverseStudyBuilder

  Class for building a Study object for the Harvard Dataverse Network.

  The field values for the Study are set using the various assignment
  methods on the class. The resulting Study object can then be formatted either
  as DDI XML using the xmlformatter.py class or as a key-value mapping in a
  dict.

  These objects can be used with WriteStudiesToXmlFolders to create a zip
  archive of Studies suitable for batch import by the Harvard IQSS team.
  '''

  def __init__(self, ignore_values=[]):
    '''__init__

    Called when creating a new DataverseStudyBuilder object.

    Params:
      ignore_values: A list of strings to consider as null if passed as inputs.
    '''
    self.description_parts = []
    self.keywords = []
    self.used_input_columns = set()
    self.output = {}
    self.ignore_values = [x.lower().strip() for x in ignore_values]
    self.dirty = False

  def Has(self, input_dict, key):
    '''Has

    Returns true if the passed "input_dict" has a valid value for key "key".

    Params:
      input_dict: The input dict to check.
      key: The key to check in input_dict.

    Returns:
      True if input_dict[key] is a valid nonblank value, false otherwise.
    '''
    return (HasNonblank(input_dict, key) and
        input_dict[key].lower().strip() not in self.ignore_values)

  def Set(self, output_field, output_value):
    '''Set

    Assigns the passed value to the passed Study field.

    Valid fields are the same as the fields shown in the Dataverse website.
    They are also listed in XML_FIELD_MAP in xmlformatter.py.

    Currently implemented fields:
      Author
      Availability Status
      Country/Nation
      Distributor
      Geographic Coverage
      Geographic unit
      Original Archive
      Production Date
      Publication Citation
      Publication URL
      Size of Collection
      Time Period Covered End
      Time Period Covered Start
      Title

    The following fields are treated specially:
      Description -- See "AddDescriptionHtml" and "AddDescriptionEntry".
      Keywords -- See "AddKeyword" and "AddKeywordEntry"

    Params:
      output_field: The field in the Study to assign the value.
      output_value: The value to assign to the field.
    '''
    self.output[output_field] = output_value

  def SingleAssign(self, input_dict, input_key, output_field):
    '''SingleAssign

    Assigns the value of input_dict[input_key] to output_field in the Study.

    Null or blank values are discarded. Valid options for output_field are
    described in the documentation for the "Set" method above.

    Params:
      input_dict: The input dictionary containing the value to assign.
      input_key: The key in input_dict with the value to assign.
      output_field: The field in the Study to which the value is assigned.
    '''
    if self.Has(input_dict, input_key):
      self.used_input_columns.add(input_key)
      value = input_dict[input_key].strip()
      self.output[output_field] = value

  def AddDescriptionHtml(self, html_data, order):
    '''AddDescriptionHtml

    Adds a string of HTML into the Description field of the Study.

    The "order" parameter provides a sorting key for all pieces of data
    assigned to the Description field of the Study. When the Study is rendered,
    the Description will be assembled in the order specified by the "order"
    parameter in all cals of AddDescriptionHtml and AddDescriptionEntry below.

    Params:
      html_data: A string of HTML to insert into the Description.
      order: The order of this portion of the Description compared to the rest.
    '''
    self.description_parts.append((order, html_data))
    self.dirty = True

  def AddDescriptionEntry(self, input_dict, input_key, label, order,
      value_for_blank=None):
    '''AddDescriptionEntry

    Adds the value of input_dict[input_key] into the Description with a label.

    The data will be inserted into the Description as the following HTML string:
      <p>label: value</p>
    If the value is null or blank and value_for_blank is set, then the string
    passed in value_for_blank will be used instead, or otherwise the value is
    discarded.

    The "order" parameter provides a sorting key for all pieces of data
    assigned to the Description field of the Study. When the Study is rendered,
    the Description will be assembled in the order specified by the "order"
    parameter in all cals of AddDescriptionHtml and AddDescriptionHtml above.

    Params:
      input_dict: The input dictionary containing the value to assign.
      input_key: The key in input_dict with the value to assign.
      label: The label to give the value in the Description.
      order: The order of this portion of the Description compared to the rest.
      value_for_blank: Optional placeholder to use if the value is blank.
    '''
    html_data = None
    breaker = ' '
    if self.Has(input_dict, input_key):
      self.used_input_columns.add(input_key)
      data = True
      value = input_dict[input_key].strip()
      html_data = '<p>%s:%s%s </p>' % (label, breaker, value)
    elif value_for_blank is not None:
      html_data = '<p>%s:%s%s </p>' % (label, breaker, value_for_blank)
    if html_data: self.AddDescriptionHtml(html_data, order)

  def AddKeywordEntry(self, input_dict, input_key, keyword):
    '''AddKeywordEntry

    Assigns the value of input_dict[input_key] to the Study keyword "keyword".

    Params:
      input_dict: The input dictionary containing the value to assign.
      input_key: The key in input_dict with the value to assign.
      keyword: The keyword to which the value is assigned.
    '''
    if self.Has(input_dict, input_key):
      self.used_input_columns.add(input_key)
      self.AddKeyword(keyword, input_dict[input_key].strip())

  def AddKeyword(self, keyword, value):
    '''AddKeyword

    Assigns the passed value to the Study keyword "keyword".

    Keywords must be lowercase a-z.

    Params:
      keyword: The keyword to which the value is assigned.
      value: The value to assign to the keyword.
    '''
    self.keywords.append((keyword, value))
    self.dirty = True

  def Finalize(self):
    '''Finalize

    Renders the Description and Keyword lists to their final string values.

    This method can be called repeatedly and will only make changes if new
    inputs have been provided. It is called automatically when output is 
    requested with OutputAsDict or OutputAsXmlString.
    '''
    if self.dirty:
      if self.description_parts:
        self.output['Description'] = ' '.join(
            [x[1] for x in sorted(self.description_parts)])
      if self.keywords:
        self.output['Keywords'] = ', '.join(
            ['%s:"%s"' % (x[0], x[1]) for x in self.keywords])
      self.dirty = False

  def OutputAsDict(self):
    '''OutputAsDict

    Outputs the Study fields as a dict of key-value pairs.

    Returns:
      Dict of key-value pairs containing the Study fields.
    '''
    self.Finalize()
    return dict(self.output)

  def OutputAsXmlString(self, pretty=True):
    '''OutputAsXmlString

    Outputs the Study fields as DDI XML formatted with xmlformatter.py.

    Params:
      pretty: Optional boolean to pretty-print the XML, default True.

    Returns:
      String of XML data containing the Study in DDI format.
    '''
    self.Finalize()
    xml_object = xmlformatter.FormatToXml.Row(self.output)
    xml_string = xmlformatter.FormatToXml.ToString(xml_object, pretty)
    return xml_string

  def WriteXmlFile(self, output_filepath, pretty=True, verbose=True):
    '''WriteXmlFile

    Writes the Study DDI XML to a file.

    Params:
      output_filepath: The file path to write the XML.
      pretty: Optional boolean to pretty-print the XML, default True.
      verbose: Optional boolean to print logging information, default True.
    '''
    self.Finalize()
    if verbose:
      print 'Writing XML file...'
      print self.output['Title']
    output_xml = self.OutputAsXmlString(pretty)
    with open(output_filepath, 'wb') as fid:
      fid.write(output_xml)
    if verbose:
      num_lines = len(filter(lambda x: x=='\n', output_xml))
      print 'Wrote %d lines of XML to file: "%s"' % (num_lines, output_filepath)


def WriteStudiesToXmlFolders(study_builder_objects, output_root_dir,
    data_filepath=None, output_zip_file=None, pretty=True, verbose=True,
    max_study_per_folder=200):
  '''WriteStudiesToXmlFolders

  Writes a list of DataverseStudyBuilder objects to folders as XML.

  Each DataverseStudyBuilder will be output as an XML file in a separate folder
  with optional included data files. These folders will be themselves grouped
  into folders with up to max_study_per_folder studies. This is necessary to
  avoid a race condition in the IQSS batch import process. The entire directory
  can optionally be zipped into a single archive. This zipped archive is
  suitable for batch import by the technical team at Harvard IQSS.

  The full archive will look like this:
    <output_root_dir>
    |-- dir_studies_001ofXXX
        |-- study_UniqueStudyNameHere12345
            |-- <copy of data_filepath>
            |-- study.xml
        |-- study_OtherUniqueStudyName7890
            ...
        ...
    |-- dir_studies_002ofXXX
        ...

  NOTE: This has only been tested in Linux, as it relies on a call to os.system!

  Params:
    study_builder_objects: List of DataverseStudyBuilder objects to write out.
    output_root_dir: The root directory to contain subfolders for the Studies.
    data_filepath: Optional path to a data file to be included with every Study.
    output_zip_file: Optional path to write a zip archive of all the Studies.
    pretty: Optional boolean to pretty-print the XML, default True.
    verbose: Optional boolean to print logging information, default True.
    max_study_per_folder: Maximum studies per output folder, default 200.
  '''
  ctr = 0
  num_folder_splits = math.ceil(
      len(study_builder_objects)/float(max_study_per_folder))
  for study in study_builder_objects:
    ctr += 1
    row = study.OutputAsDict()
    if verbose: print 'Row to XML %d/%d' % (ctr, len(study_builder_objects))
    split_counter = math.ceil(ctr/float(max_study_per_folder))
    subfolder_split = 'dir_studies_%03dof%03d' % (split_counter, num_folder_splits)
    subfolder_study = 'study_%s' % xmlformatter.FormatToXml.SafeFilename(row)
    output_dir = os.path.join(output_root_dir, subfolder_split, subfolder_study)
    if not os.path.isdir(output_dir): os.makedirs(output_dir)
    xml_file = os.path.join(output_dir, 'study.xml')
    study.WriteXmlFile(xml_file, pretty=pretty, verbose=verbose)
    if data_filepath is not None:
      shutil.copy(data_filepath, output_dir)
  if output_zip_file is None:
    print '\nSuccess!\n\nWrote to folder: %s' % output_root_dir
  else:
    cmd = 'zip -r %s %s' % (output_zip_file, output_root_dir)
    if verbose: print cmd
    exitcode = os.system(cmd)
    if exitcode != 0:
      raise RuntimeError('Command failed with code %d: "%s"' % (exitcode, 
        cmd))
    print '\nSuccess!\n\nCreated archive file: %s' % output_zip_file


def TestDataverseStudyBuilder():
  '''TestDataverseStudyBuilder

  Runs a test of the DataverseStudyBuilder object, printing results to stdout.
  '''
  print 'Running test...'
  testdata_dir = os.path.join(os.path.dirname(__file__), 'testdata')
  truth_xml_file = 'dataversestudybuilder_testdata.xml'
  temp_xml_file = 'temp.xml'
  study = DataverseStudyBuilder(ignore_values=['n/a'])
  study.Set('Title', 'This is the title.')
  test_input = {
      'author':'This is the author.',
      'unusedgeo':'n/a',
      'description1':'Description part 1.',
      'description2':'Description part 2.',
      'keyword':'drowyekym',
      }
  study.SingleAssign(test_input, 'author', 'Author')
  study.SingleAssign(test_input, 'unusedgeo', 'Geographic Coverage')
  study.AddDescriptionEntry(test_input, 'description2', 'Describe again', 2)
  study.AddDescriptionEntry(test_input, 'description1', 'Describe first', 1)
  study.AddDescriptionHtml('<p>Describe bonus!</p>', 3)
  study.AddKeywordEntry(test_input, 'keyword', 'mykeyword')
  study.AddKeyword('myotherkeyword', 'drowyekrehtoym')
  test_truth_file = os.path.join(testdata_dir, truth_xml_file)
  with open(test_truth_file) as fid:
    truth_xml = fid.read()
  output_xml = study.OutputAsXmlString()
  if output_xml != truth_xml:
    print 'Assertion fails, writing current XML to temp file: %s' % (
        temp_xml_file)
    with open(temp_xml_file) as fid:
      fid.write(output_xml)
  assert(truth_xml == output_xml)
  print 'Passed.'


if __name__ == '__main__':
  TestDataverseStudyBuilder()
