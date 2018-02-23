'''dataversewrapper.py

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
import dataverse


# These can be inferred from dataversecmd.py "info" command, but that only
# works on a dataverse that has a small number of datasets.
EDIT_URI_BASE = 'https://dataverse.harvard.edu/dvn/api/data-deposit/v1.1/swordv2/edit/study/'
EDIT_MEDIA_URI_BASE = 'https://dataverse.harvard.edu/dvn/api/data-deposit/v1.1/swordv2/edit-media/study/'

def WrapDataset(container_dataverse, doi, _id):
  dataset = dataverse.Dataset(
      dataverse=container_dataverse, 
      edit_uri = EDIT_URI_BASE+doi,
      edit_media_uri = EDIT_MEDIA_URI_BASE+doi,
      title='draft title',
      )
  dataset._id = _id  # Otherwise this enumerates the parent dataverse.
  dataset.get_entry(refresh=True)  # Force populate the _entry field.
  return dataset


