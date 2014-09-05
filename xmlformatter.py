'''xmlformatter.py -- Convert tabular data into DDI XML for a Dataverse.

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
Date: July 28, 2014

This module defines a class that converts tabular input data into DDI format
XML trees suitable for use in the Harvard Dataverse Network [1].

The input data is expected to be in Python dictionaries such as would be read
from csv.DictReader. Helper functions for reading and writing this format are
included in tsvfile.py. Input data could also be generated programmatically as
key-value pairs. Parsing is done one row at a time with no state maintained.

Once parsed and formatted to XML, the resulting XML trees can be written to
files and given to an administrator of the Harvard Dataverse Network for batch
importing. To reach an administrator, contact Technical Support for the 
Harvard Institute for Quantitative Social Science (IQSS) [2].

The valid column names (i.e. valid dictionary keys) are defined in the 
XML_FIELD_MAP structure below. Functionality can be extended by adding new
entries to the structure.

Invoke this file with no arguments to run a series of validity tests:
python xmlformatter.py

[1] https://thedata.harvard.edu/dvn/
[2] http://www.iq.harvard.edu/contact-us
'''
import os
import re
import hashlib
from lxml import etree


class FormatToXml(object):

  SOURCE = 'DVN_3_0'

  '''XML_FIELD_MAP defines the mapping from input columns to output XML.

  Each entry consists of two parts:
  1. The input field name, which should be a dict key in each input row.
  2. The output map, which is an XML node traversal path to the leaf.

  So, to put the value from "Author" into the following XML leaf
    (root)
    |-- citation
        |-- rspStmt
            |-- AuthEnty
  you would specify ('Author', ('citation','rspStmt','AuthEnty')).

  You can also provide an arbitrary lambda in place of a node name in the
  output map. In this case, the lambda will be evaluated and must generate
  the appropriate etree Element for the leaf. The lambda will be called with
  the corresponding value from the input row. 
  '''
  XML_FIELD_MAP = (
      ('Author', ('citation','rspStmt','AuthEnty')),
      ('Availability Status', ('dataAccs','setAvail','avlStatus')),
      ('Country/Nation', ('stdyInfo','sumDscr','nation')),
      ('Description', ('stdyInfo','abstract')),
      ('Distributor', ('citation','distStmt', 'distrbtr')),
      ('Geographic Coverage', ('stdyInfo','sumDscr','geogCover')),
      ('Geographic Unit', ('stdyInfo','sumDscr','geogUnit')),
      ('Keywords',  ('stdyInfo','subject',
        lambda x: FormatToXml.KeywordsFromString(x))),
      ('Original Archive', ('dataAccs','setAvail','origArch')),
      ('Production Date', ('citation','prodStmt',
        lambda x: FormatToXml.TimePeriodNode('prodDate', x))),
      ('Publication Citation', ('othrStdyMat','relPubl','citation','biblCit')),
      ('Publication URL', ('othrStdyMat','relPubl','citation',
        lambda x: FormatToXml.NodeWithAttrAndText('holdings', 'URI', x))),
      ('Publication URL', ('dataAccs','setAvail','accsPlac')),
      ('Size of Collection', ('dataAccs','setAvail','collSize')),
      ('Time Period Covered End', ('stdyInfo','sumDscr',
        lambda x: FormatToXml.TimePeriodNode('timePrd', x, 'end'))),
      ('Time Period Covered Start', ('stdyInfo','sumDscr',
        lambda x: FormatToXml.TimePeriodNode('timePrd', x, 'start'))),
      ('Title', ('citation','titlStmt', 'titl')),
      )
  
  XML_ATTRIBUTES = {
      'citation':{'source':'DVN_3_0'},
      }

  @staticmethod
  def NodeWithAttrAndText(element_name, attribute_name, text):
    '''NodeWithAttrAndText

    Generates an XML node with one attribute whose value is the node text.

    E.g., <element_name attribute_name="text">text</element_name>

    Params:
      element_name: The element to create.
      attribute_name: The name of the attribute to set.
      text: The text for the node, which is also set as the attribute value.
    
    Returns:
      An XML node constructed according to the parameters.
    '''
    args={}
    args[attribute_name] = text
    elem = etree.Element(element_name, **args)
    elem.text = text
    return elem

  @staticmethod
  def TimePeriodNode(element_name, iso_date_string, event_name=None):
    '''TimePeriodNode

    Generates an XML DDI node for a date with an optional event name attribute.

    E.g., 
    <element_name event="event_name" date="1950-01-31">1950-01-31</element_name>

    Params:
      element_name: The element to create.
      iso_date_string: Date string in ISO format (YYYY-MM-DD) for the node.
      event_name: Optional value for the "event" attribute.

    Returns:
      An XML node constructed according to the parameters.
    '''
    args = {'date':iso_date_string}
    if event_name is not None:
      args['event'] = event_name
    elem = etree.Element(element_name, **args)
    elem.text = iso_date_string
    return elem

  @staticmethod
  def KeywordsFromString(keyword_string):
    '''KeywordsFromString

    Generates an XML list from a formatted string of keywords.

    The parameter keyword_string must be a string like:
      key1:"value1", key2:"multi word value 2", key3:"value3", ...

    The resulting XML list will be like:
      <keyword vocab="key1">value1</keyword>
      <keyword vocab="key2">multi word valued 2</keyword>
      <keyword vocab="key3">value3</keyword>
      ...

    Params:
      keyword_string: A suitably formatted string of keywords.

    Returns:
      An XML list that is a DDI representation of the keyword list.
    '''
    output = []
    keyword_re = re.compile(r'([a-z-]*):"([^"]*)",?')
    keyword_entries = keyword_re.findall(keyword_string)
    if not keyword_entries: return output
    keyword_entries.sort()
    for (vocab, text) in keyword_entries:
      elem = etree.Element('keyword',vocab=vocab)
      elem.text = text
      output.append(elem)
    return output

  @staticmethod
  def XmlRootNode():
    '''XmlRootNode

    Generates the root XML node for an IQSS DDI XML document.

    Returns:
      The XML root node.
    '''
    xmlns='http://www.icpsr.umich.edu/DDI'
    xsi='http://www.w3.org/2001/XMLSchema-instance'
    schema_location='http://www.icpsr.umich.edu/DDI http://www.icpsr.umich.edu/DDI/Version2-0.xsd'
    version = '2.0'
    root = etree.Element(
        'codeBook',
        nsmap={'xsi':xsi, None:xmlns},
        attrib={"{" + xsi + "}schemaLocation" : schema_location},
        version=version,
        source=FormatToXml.SOURCE)
    return root

  @staticmethod
  def ForceUTF8(input_data):
    '''ForceUTF8

    Coerces input such that it can be encoded as UTF-8 by etree.

    Params:
      input_data: A string of data to be coerced.

    Returns:
      An decoded byte string that is valid for encoding as UTF-8.
    '''
    if type(input_data) == unicode: return input_data
    return input_data.decode('utf8', 'ignore')

  @staticmethod
  def Row(row):
    '''Row

    Parses a dictionary containing one row of input and returns the XML tree.

    This is the main processing code for this class. It follows the spec
    defined in XML_FIELD_MAP above, parsing each field of input according to 
    the rules. The finished result will be a complete XML tree in DDI format
    that can be written to a file and used with the Harvard Dataverse Network.
    For more information, please see the documentation at the top of this file.

    Params:
      row: A dictionary representing one row of input.

    Returns:
      An XML tree that encodes the parsed input.
    '''
    root = FormatToXml.XmlRootNode()
    study = etree.Element('stdyDscr')
    root.append(study)
    for field_from, nodes_to in FormatToXml.XML_FIELD_MAP:
      # Skip any fields that are not present in the row.
      if field_from not in row or not row[field_from]: continue
      parent = study
      for i in xrange(len(nodes_to)):
        # For each node in the destination heirarchy.
        node_to = nodes_to[i]
        if i==len(nodes_to)-1:
          # If this is a leaf node, always make a new one.
          if type(node_to) == str:
            # Typical specification is a string that is the node name.
            curr = etree.Element(node_to)
            curr.text = FormatToXml.ForceUTF8(row[field_from])
            parent.append(curr)
          else:
            # Can instead provide a one-argument function to create the node.
            curr_eval = node_to(row[field_from])
            if type(curr_eval) == list:
              parent.extend(curr_eval)
            else:
              parent.append(curr_eval)
        else:
          # Otherwise, find if it already exists, or make a new one.
          if type(node_to) != str:
            raise NotImplementedError(
                'Node spec must be string for non-leaf nodes.')
          curr = parent.find(node_to)
          if curr is None:
            # If we didn't find it, create it.
            attribs = {}
            if node_to in FormatToXml.XML_ATTRIBUTES:
              attribs = FormatToXml.XML_ATTRIBUTES[node_to]
            curr = etree.Element(node_to, **attribs)
            parent.append(curr)
          # Set the new node as the parent and continue down the path.
          parent = curr
    return root

  @staticmethod
  def ToString(node, pretty=False):
    '''ToString

    Prints an XML tree to a string with optional indenting.

    Params:
      node: The root node of the tree to print.
      pretty: Optional boolean, set to True to pretty-print with indentation.

    Returns:
      A string containing the printed XML.
    '''
    return etree.tostring(node, xml_declaration=True, 
        encoding="UTF-8", pretty_print=pretty)

  @staticmethod
  def SafeFilename(row):
    '''SafeFilename

    Generates a mostly-unique filesystem-safe human-friendly name for the input.

    The input parameter should be the same as what is used for the method
    FormatToXml.Row(row) above.

    Params:
      row: A dictionary representing one row of input.

    Returns:
      String containing a mostly-unique filesystem-safe human-friendly name.
    '''
    description = row['Description']
    parts = [row['Title'], description[:description.find('href')-5]]
    messy_string = ''.join(parts)
    clean_string = filter(lambda x: x.isalnum(), messy_string)[:100]
    row_kv = sorted(row.items())
    clean_string += hashlib.md5(str([x[1] for x in row_kv])).hexdigest()[:8]
    return clean_string


def TestXML():
  '''TestXML

  This routine runs a series of tests using assertions.

  The tests are based on some known good outputs of the FormatToXml class. 
  These known good outputs should be included with this file in the "testdata/"
  subfolder. 

  If it is desirable to extend the tests, consider reimplementing this using
  the PyUnit test framework.
  '''
  import tsvfile
  print 'Invoked xmlformatter.TestXML() test routine.'
  testdata_dir = os.path.join(os.path.dirname(__file__), 'testdata')
  tempfile = os.path.join(testdata_dir, 'temp.xml')
  infile = os.path.join(testdata_dir, 'xmlformatter_testdata.tsv')
  rows = tsvfile.ReadDicts(infile)
  print 'Running %d tests...' % len(rows)
  for row in rows:
    print ''
    curr_xml_data = FormatToXml.ToString(FormatToXml.Row(row), True)
    curr_filename = FormatToXml.SafeFilename(row)+'.xml'
    curr_filepath = os.path.join(testdata_dir, curr_filename)
    print 'File: %s' % curr_filename
    assert(os.path.exists(curr_filepath))
    with open(curr_filepath) as fid:
      prev_xml_data = fid.read()
    if prev_xml_data != curr_xml_data:
      print 'Assertion fails, writing current XML to temp file: %s' % tempfile
      with open(os.path.join(testdata_dir, 'temp.xml'), 'w') as fid:
        fid.write(curr_xml_data)
    assert(prev_xml_data == curr_xml_data)
    print 'Passed.'
  print ''
  print 'Passed all %d tests.' % len(rows)
  if os.path.isfile(tempfile):
    os.remove(tempfile)


if __name__ == '__main__':
  TestXML()
