'''antislaverypetitions.py -- Main module for Antislavery Petitions MA dataset.

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
Date: August 11, 2014

This module provides an interface for generating Dataverse import files for the
Antislavery Petitions Massachusetts dataset.

For a short description on how to use this module, run it with no arguments:
  python antislaverypetitions.py
To see details of the command-line options, use the --help flag:
  python antislaverypetitions.py --help

For example input, see the file: testdata/input_testdata.tsv

Key people involved in this project:
  Dan Carpenter (lead researcher)
  Garth Griffin (developer)
  Nicole Topich (archivist)

For more information, contact Dan Carpenter:
https://www.radcliffe.harvard.edu/people/daniel-carpenter-0

You can see the full Dataverse of petition data at:
http://thedata.harvard.edu/dvn/dv/antislaverypetitionsma
'''
import sys
import itertools
import shutil
import os
import re
import traceback
import optparse
import calendar

import tsvfile
import dataversestudybuilder


def CustomDateParse(input_string):
  stripped = input_string.replace('CHECK WITH INDEX', '').strip().strip('?[]')
  try:
    return dataversestudybuilder.ParseDate(stripped)
  except ValueError, e:
    # Fix February 29 leap year errors.
    if stripped.endswith('0229'):
      return dataversestudybuilder.ParseDate(stripped[:-2]+'28')
    raise e


def ParseAntislaveryPetitions(input_rows, author, contact_email=None, 
    extra_keyword_column=[]):
  '''ParseAntislaveryPetitions

  Parses a list of dicts read from a tsv file and creates Study objects.

  The input can be correctly read using the tsvfile module. The parsing is done
  using the dataversestudybuilder.py module.

  Params:
    input_rows: The list of dicts from the tsv file to parse.
    contact_email: An optional email address for contact information.

  Returns:
    A list of DataverseStudyBuilder objects containing the parsed data.
  '''
  # List of values to ignore in the input data.
  ignore_values = ['not available', 'na']

  # Iterate over all inputs and collect output objects.
  output_studies = []
  for row in input_rows:
    # Setup
    curr = dataversestudybuilder.DataverseStudyBuilder(ignore_values)
    # Parse dates
    date_fields = ['Date of creation']+['dateaction%d' % i for i in xrange(1,7)]
    for date_field in date_fields:
      if curr.Has(row, date_field):
        try:
          row[date_field] = CustomDateParse(row[date_field])
        except ValueError, e:
          print (
              'WARNING: Failed to parse date "%s", will treat as string:\n%s'
              % (row[date_field], traceback.format_exc(e)))

    # Fields
    if contact_email:
      curr.Set('Dataverse Contact', contact_email)
    curr.Set('Dataverse Subject', 'Social Sciences')
    curr.Set('Author', author)
    curr.Set('Distributor', 'Massachusetts Archives. Boston, Mass.')
    curr.Set('Size of Collection', 'Single petition scanned as one or more 11x17 images.')
    curr.Set('Country/Nation', 'United States')
    curr.Set('Original Archive', 'Massachusetts Archives, Boston, MA')
    curr.Set('Availability Status', 'Public')
    curr.SingleAssign(row, 'PDS link', 'Publication URL')
    curr.SingleAssign(row, 'PDS link', 'Data Access Place')
    curr.AddDescriptionHtml('<p>Acknowledgements: Supported by the National Endowment for the Humanities (PW-5105612), Massachusetts Archives of the Commonwealth, Radcliffe Institute for Advanced Study at Harvard University, Center for American Political Studies at Harvard University, Institutional Development Initiative at Harvard University, and Harvard University Library.</p>', 99)
    if curr.Has(row, 'PDS link'):
      curr.used_input_columns.add('PDS link')
      value = row['PDS link'].strip()
      curr.AddDescriptionHtml(
          '<p>Original: <a href="%s">%s</a> </p>' % (
            value, value),
          2)
    if curr.Has(row, 'Scholarly citation'):
      curr.Set('Publication Citation',
          'D. Carpenter, N. Topich and G. Griffin. ' + 
          row['Scholarly citation'])
    curr.SingleAssign(row, 'Date of creation', 'Time Period Covered Start')
    curr.SingleAssign(row, 'Date of creation', 'Production Date')
    curr.AddDescriptionEntry(row, 'Date of creation', 'Date of creation', 3,
        '(unknown)')
    curr.AddDescriptionEntry(row,
        'Date received by legislature and legislative action',
        'Legislative action', 8)
    curr.AddDescriptionEntry(row, 'Legislative action summary',
        'Legislative action summary', 10)
    if curr.Has(row, 'Legislative action summary'):
      curr.used_input_columns.add('Legislative action summary')
      actions = set(dataversestudybuilder.ParseList(
        row['Legislative action summary']))
      for a in actions: curr.AddKeyword('action', a.lower())
    action_dates = []
    for field in ['dateaction%d' % i for i in range(1,7)]:
      if curr.Has(row, field):
        curr.used_input_columns.add(field)
        try:
          action_dates.append(CustomDateParse(row[field]))
        except ValueError, e:
          print (
              'WARNING: Failed to parse date "%s", will treat as string:\n%s'
              % (row[field], traceback.format_exc(e)))
    if action_dates:
      curr.AddDescriptionHtml('<p>Actions taken on dates: %s </p>' % (
        ','.join(action_dates)), 7)
    if curr.Has(row, 'Date of creation'):
      action_dates.append(row['Date of creation'])
    if action_dates:
      max_date = max(action_dates)
      min_date = min(action_dates)
      if len(min_date) < 7:
        min_date += '-01'
      if len(min_date) < 10 and '-' in min_date:
        min_date += '-01'
      if len(max_date) < 7:
        max_date += '-12'
      if len(max_date) < 10 and '-' in min_date:
        max_date += ('-'+str(
          calendar.monthrange(int(max_date[:4]), int(max_date[5:7]))[-1]))
      curr.Set('Time Period Covered End', max_date)
      curr.Set('Time Period Covered Start', min_date)
    curr.SingleAssign(row, 'Location', 'Geographic Coverage')
    if ('Geographic Coverage' in curr.output and
        curr.output['Geographic Coverage']):
      cover = curr.output['Geographic Coverage']
      if cover == 'Massachusetts':
        curr.Set('Geographic Unit', 'State')
      else:
        curr.Set('Geographic Unit', 'City/Town')
    curr.AddDescriptionEntry(row, 'Location', 'Petition location', 4)
    curr.AddKeywordEntry(row,
        'Legislator, committee, or address that the petition was sent to',
        'sent')
    curr.AddDescriptionEntry(row,
        'Legislator, committee, or address that the petition was sent to',
        'Legislator, committee, or address that the petition was sent to', 5)
    curr.AddDescriptionEntry(row, 'Subject', 'Petition subject', 1)
    curr.AddKeywordEntry(row, 'Total signatures', 'signatures-total')
    curr.AddKeywordEntry(row,
        'Legal voters or males not identified as being non-legal',
        'signatures-legal-voters')
    curr.AddKeywordEntry(row, 'Females', 'signatures-females')
    curr.AddKeywordEntry(row, 'Female only', 'signatures-female-only')
    curr.AddDescriptionEntry(row, 'Female only', 'Female only signatures', 17)
    curr.AddKeywordEntry(row, 'Females of color', 'signatures-females-of-color')
    curr.AddKeywordEntry(row, 'Other males', 'signatures-other-males')
    curr.AddKeywordEntry(row, 'Males of color', 'signatures-males-of-color')
    curr.AddKeywordEntry(row, 'Unidentified', 'signatures-unidentified')
    curr.AddDescriptionEntry(row, 'Total signatures', 'Total signatures', 9)
    curr.AddDescriptionEntry(row,
        'Legal voters or males not identified as being non-legal',
        'Legal voter signatures (males not identified as non-legal)', 11)
    curr.AddDescriptionEntry(row, 'Females', 'Female signatures', 12)
    curr.AddDescriptionEntry(row, 'Females of color', 'Females of color signatures',
        13)
    curr.AddDescriptionEntry(row, 'Males of color', 'Males of color signatures',
        14)
    curr.AddDescriptionEntry(row, 'Other males', 'Other male signatures', 15)
    curr.AddDescriptionEntry(row, 'Unidentified', 'Unidentified signatures', 16)
    if extra_keyword_column:
      for i,f in enumerate(extra_keyword_column):
        curr.AddKeywordEntry(row, f, '-'.join(x.lower() for x in f.split()))
        extra_idx = i-1-len(extra_keyword_column)
        extra_idx = 50+i
        curr.AddDescriptionEntry(row, f, f, extra_idx)
    loc = ('Location of the petition at the Massachusetts Archives of the '+
        'Commonwealth')
    curr.AddDescriptionEntry(row, loc, loc, 123)
    if curr.Has(row, 'Identifications'):
      curr.used_input_columns.add('Identifications')
      identifications = dataversestudybuilder.ParseList(row['Identifications'])
      clean_identifications = []
      for ident in identifications:
        curr_ident = str(ident)
        prev_ident_len = 0
        while prev_ident_len != len(curr_ident):
          prev_ident_len = len(curr_ident)
          for charpair in ('[]', '()', '""'):
            if (curr_ident.startswith(charpair[0]) and 
                curr_ident.endswith(charpair[1])):
              curr_ident = curr_ident[1:-1]
        clean_identifications.append(curr_ident)
      for i in clean_identifications: curr.AddKeyword('signatory-category', i)
      curr.AddDescriptionHtml(
          '<p>Identifications of signatories: %s </p>' % 
          ', '.join(identifications), 18)
    if curr.Has(row, 'Prayer format'):
      curr.used_input_columns.add('Prayer format')
      value = row['Prayer format']
      curr.AddKeyword('prayer-format', value)
      curr.AddDescriptionHtml(
          '<p>Prayer format was <a href="http://en.wikipedia.org/wiki/Printing">printed</a> vs. <a href="http://en.wikipedia.org/wiki/Manuscript">manuscript</a>: %s </p>'
          % value, 19)
    if curr.Has(row, 'At least 3 signatures from the petition'):
      curr.used_input_columns.add('At least 3 signatures from the petition')
      signatures = dataversestudybuilder.ParseList(
          row['At least 3 signatures from the petition'])
      if signatures:
        for s in signatures: curr.AddKeyword('signatory',s)
        curr.AddDescriptionHtml('<p>Selected signatures:<ol><li>%s</li></ol> </p>' %
            '</li><li>'.join(signatures), 6)
    title_parts = []
    if curr.Has(row, 'Scholarly citation'):
      curr.used_input_columns.add('Scholarly citation')
      citation = row['Scholarly citation']
      result = re.match(r'Digital Archive of Massachusetts Anti-Slavery and Anti-Segregation Petitions(.*) Massachusetts Archives. Boston, Mass.',
          citation)
      if result:
        reference = result.groups(1)[0].strip(' ;.,')
        title_parts.append(reference)
    if curr.Has(row, 'At least 3 signatures from the petition'):
      curr.used_input_columns.add('At least 3 signatures from the petition')
      signatures = dataversestudybuilder.ParseList(
          row['At least 3 signatures from the petition'])
      if signatures:
        title_parts.append('Petition of '+signatures[0])
    if title_parts:
      curr.Set('Title', ', '.join(title_parts))
    else:
      curr.Set('Title', '(untitled)')
    curr.AddDescriptionEntry(row, "Archivist's notes", 
        'Additional archivist notes', 122)
    separation_bool = dataversestudybuilder.ParseBoolean(row, 
        'Are the signature columns separated?')
    if separation_bool is not None:
      curr.used_input_columns.add('Are the signature columns separated?')
      value = 'column separated' if separation_bool else 'not column separated'
      curr.AddKeyword('signatory-column-format', value)
      curr.AddDescriptionHtml('<p>Signatory column format: %s </p>' % value, 20)
    docs_bool = dataversestudybuilder.ParseBoolean(row, 
        'Does the archives have additional non-petition or unrelated documents?')
    if docs_bool is not None:
      curr.used_input_columns.add(
          'Does the archives have additional non-petition or unrelated documents?'
          )
      value = ('additional documents available' if docs_bool else
          'no additional documents')
      curr.AddDescriptionHtml(
          '<p>Additional non-petition or unrelated documents available at archive: %s </p>' %
          value, 121)

    # Set a local ID
    id_fields = ['PDS link', 'Subject', 'Location',
        'At least 3 signatures from the petition']
    id_parts = [row.get(x, '').replace(' ', '')[:50] for x in id_fields]
    curr.Set('Local ID', '|'.join(id_parts))

    # Finalize
    curr.Finalize()
    output_studies.append(curr)

  return output_studies


def ColumnCoverage(input_rows, output_studies, verbose=True):
  '''ColumnCoverage

  Counts the used and unused input columns for a set of generated studies.

  Params:
    input_rows: List of dicts of input data.
    output_studies: List of DataverseStudyBuilder objects parsed from the input.
    verbose: Optional boolean, set True to print results to stdout.

  Returns:
    Tuple of (used, unused) with counts of used and unused columns.
  '''
  all_input_cols = set(itertools.chain(*
    [x.keys() for x in input_rows]))
  all_used_cols = set(itertools.chain(*
    [x.used_input_columns for x in output_studies]))
  bad_reports = all_used_cols - all_input_cols
  if bad_reports:
    raise RuntimeError('BUG bad column reports: %s' % ', '.join(
        sorted(list(bad_reports))))
  unused_cols = all_input_cols-all_used_cols
  if verbose:
    print 'Used columns: %d/%d' % (len(all_used_cols), len(all_input_cols))
    print 'Unused: %s' % ', '.join(sorted(list(unused_cols)))
  return (all_used_cols, unused_cols)


def RunMain(input_tsv,
    author,
    print_column_coverage=False,
    output_tsv=None,
    output_ddi_dir=None,
    output_ddi_zip_file=None,
    output_ddi_data_file=None,
    contact_email=None,
    extra_keyword_column=[],
    ):
  '''RunMain

  Runs the parsing and output routine for given inputs.

  Typically the inputs and outputs are specified on the command-line and then
  passed to this function. Assumes verbose output and prints status to stdout.
  The input data must be formatted with the column names expected by the
  ParseAntislaveryPetitions function. An example should be available in
  "testdata/input_testdata.tsv".

  Params:
    input_tsv: File path of tab-delimited input data with appropriate columns.
    print_column_coverage: Optional boolean, set True to show column coverage.
    output_tsv: Optional file path to output parsed Studies as tab-delimited.
    output_ddi_dir: Optional directory path to output DDI XML of the Studies.
    output_ddi_zip_file: Optional file path to create archive of output_ddi_dir.
    output_ddi_data_file: Optional path of data file to include with Studies.
    contact_email: Optional email address for contact information.
  '''
  # Check usage.
  if not output_ddi_dir and output_ddi_zip_file:
    raise ValueError('Must specify output_ddi_dir to use output_ddi_zip_file')
  if not output_ddi_dir and output_ddi_data_file:
    raise ValueError('Must specify output_ddi_dir to use output_ddi_data_file')

  # Read the input data and parse it to create Study objects.
  input_rows = tsvfile.ReadDicts(input_tsv)
  output_studies = ParseAntislaveryPetitions(input_rows, author, contact_email,
      extra_keyword_column)
  output_rows = [x.OutputAsDict() for x in output_studies]
  print '=========================='
  print 'Processed %d input rows into %d output studies.' % (
      len(input_rows), len(output_studies))
  print 'All output keys:'
  print ', '.join(sorted(list(set(itertools.chain(*
    [x.keys() for x in output_rows])))))

  # If flagged, print the column coverage of the studies.
  if print_column_coverage:
    PrintColumnCoverage(input_rows, output_studies)

  # If we are writing an intermediate file, output the studies as dicts.
  if output_tsv:
    tsvfile.WriteDicts(output_tsv, output_rows)

  # If XML DDI output is specified, create the dir structure, output the
  # XML files, and optionally create a zip archive.
  if output_ddi_dir:
    print '=========================='
    print 'Creating DDI files:'
    dataversestudybuilder.WriteStudiesToXmlFolders(
        output_studies,
        output_ddi_dir,
        data_filepath=output_ddi_data_file,
        output_zip_file=output_ddi_zip_file,
        pretty=True,
        verbose=True)


def TestAntislaveryPetitions():
  '''TestAntislaveryPetitions

  Runs an automated test of the ParseAntislaveryPetitions function.

  Results are printed to stdout.
  '''
  testdata_dir = os.path.join(os.path.dirname(__file__), 'testdata')
  test_input_file = os.path.join(testdata_dir, 'input_testdata.tsv')
  test_truth_file = os.path.join(testdata_dir, 'xmlformatter_testdata.tsv')
  input_rows = tsvfile.ReadDicts(test_input_file)
  truth_rows = tsvfile.ReadDicts(test_truth_file)
  result_studies = ParseAntislaveryPetitions(input_rows)
  result_rows = [x.OutputAsDict() for x in result_studies]
  truth_by_citation = tsvfile.GroupByUnique(truth_rows, 'Publication Citation')
  result_by_citation = tsvfile.GroupByUnique(result_rows, 
      'Publication Citation')
  print 'Running %d tests...' % len(result_rows)
  for citation in result_by_citation:
    print ''
    print citation
    assert((citation in truth_by_citation))
    result_row = result_by_citation[citation]
    truth_row = truth_by_citation[citation]
    hit_keys = set()
    for key in sorted(result_row.keys()):
      hit_keys.add(key)
      if key in truth_row and result_row[key] == truth_row[key]:
        print '  %s ... OK' % key
      else:
        print '---%s---\nCurrent:\n%s\nExpected:\n%s' % (
            key, result_row[key], 
            (truth_row[key] if key in truth_row else 'MISSING!'))
      assert(key in truth_row and result_row[key] == truth_row[key])
    miss_keys = set(truth_row.keys()) - hit_keys
    for key in miss_keys:
      miss_value = truth_row[key].strip()
      if len(miss_value) > 0:
        print 'Missing key-value "%s" -> "%s"' % (key, truth_row[key])
      assert(len(miss_value) == 0)
    print 'Passed'
  print ''
  used_cols, unused_cols = ColumnCoverage(input_rows, result_studies, False)
  print 'Covered %d/%d input columns.' % (
      len(used_cols), len(used_cols)+len(unused_cols))
  if unused_cols:
    print 'Unused input columns:\n  %s' % (
        '\n  '.join(sorted(list(unused_cols))))
  print ''
  print 'Passed all %d tests.' % len(result_rows)



if __name__ == '__main__':
  # Define command-line options.
  parser = optparse.OptionParser()
  parser.add_option('--test', nargs=0, default=False,
      help='Run built-in tests of this module instead of parsing input.')
  parser.add_option('--input_tsv', help='Input tab-delimited file to parse.')
  parser.add_option('--print_column_coverage', nargs=0, default=False,
      help='Print column coverage after parsing input.')
  parser.add_option('--output_tsv', 
      help='Output a tab-delimited file of parsed results.')
  parser.add_option('--output_ddi_dir',
      help='Write DDI XML output files of parsed results to this directory.')
  parser.add_option('--output_ddi_zip_file',
      help='Create a zip archive of --output_ddi_dir.')
  parser.add_option('--output_ddi_data_file',
      help='Include a copy of this file with every output in --output_ddi_dir')
  parser.add_option('--contact_email', default=None,
      help='Contact email address.')
  parser.add_option('--author', 
      help='Author for the Dataverse.')
  parser.add_option('--extra_keyword_column',
      help='Specify an extra column to use for keywords, can be repeated.',
      action='append')
  # Parse the command-line options.
  options, args = parser.parse_args()
  options = vars(options)
  # Running with no flags will print help.
  if len(sys.argv) == 1:
    prefix='`python %s' % sys.argv[0]
    print '\n### How to use this file: ###\n'
    print 'Use --input_tsv and --output_* command-line options to parse a dataset, or:'
    print prefix+' --help` for details of command-line options'
    print prefix+' --test` to run automated tests'
    print prefix+'` to show this message'
    print ''
    sys.exit(0)
  # Set boolean values for boolean option flags.
  for key in ['test', 'print_column_coverage']:
    if key in options and options[key] is (): options[key] = True
  # If the user specified test, run a test and then exit.
  if options['test']:
    TestAntislaveryPetitions()
    sys.exit(0)
  # Otherwise we will run the main function.
  del options['test']
  # Check that the flags are valid.
  if not options['input_tsv']:
    raise ValueError('Must specify --input_tsv or --test')
  if options['output_ddi_zip_file'] and not options['output_ddi_dir']:
    raise ValueError(
        'Must specify --output_ddi_dir to use --output_ddi_zip_file.')
  if options['output_ddi_data_file'] and not options['output_ddi_dir']:
    raise ValueError(
        'Must specify --output_ddi_dir to use --output_ddi_data_file.')
  if not options['output_ddi_dir'] and not options['output_tsv']:
    print 'WARNING: No outputs specified. Use --output_ddi_dir, output_ddi_zip_file, and/or --output_tsv to write parsed output.'
  if options['output_ddi_dir'] and os.path.exists(options['output_ddi_dir']):
    raise ValueError(
        "Output directory specified by --output_ddi_dir already exists. Delete it by running `rm -r '%s'` or choose a different output directory." % options['output_ddi_dir'])
  if (options['output_ddi_zip_file'] and
      os.path.exists(options['output_ddi_zip_file'])):
    raise ValueError(
        "Output file specified by --output_ddi_zip_file already exists. Delete it by running `rm '%s'` or choose a different output filename." % options['output_ddi_zip_file'])
  if options['input_tsv'] and not os.path.isfile(options['input_tsv']):
    raise ValueError('Filename "%s" from --input_tsv is not a file. Please check your spelling and try again.' % options['input_tsv'])
  if not options['author']:
    raise ValueError('Must specify --author.')
  print 'Run with options: %s' % options
  # Run the main function.
  RunMain(**options)


