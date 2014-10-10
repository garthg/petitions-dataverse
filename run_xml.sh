# run_xml.sh -- Example invocation of antislaverypetitions.py.
# 
# Copyright 2014 Garth Griffin
# Distributed under the GNU GPL v3. For full terms see the file LICENSE.
#
# This file is part of AntislaveryPetitionsDataverse.
# 
# AntislaveryPetitionsDataverse is free software: you can redistribute it
# and/or modify it under the terms of the GNU General Public License as
# published by the Free Software Foundation, either version 3 of the License,
# or (at your option) any later version.
# 
# AntislaveryPetitionsDataverse is distributed in the hope that it will be
# useful, but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General
# Public License for more details.
# 
# You should have received a copy of the GNU General Public License along with
# AntislaveryPetitionsDataverse.  If not, see <http://www.gnu.org/licenses/>.
# _____________________________________________________________________________
#
# Author: Garth Griffin
# Date: August 11, 2014
#
# This script shows an example invocation of antislaverypetitions.py parsing
# module.
#
# It takes one argument, which is the suffix to use for the output files.
#
if [ $# -lt 1 ]; then echo "usage: $0 <OUTPUT_LABEL>";  exit 11; fi
cd `dirname $0`
suffix="$1"
outfile="antislaverypetitions_$suffix"
indir="input_2014-07-29"
cmd="\
  python antislaverypetitions.py \
  --input_tsv=$indir/petitions.tsv \
  --output_tsv=testout.tsv \
  --output_ddi_dir=antislaverypetitions_$suffix \
  --output_ddi_zip_file=antislaverypetitions_$suffix.zip \
  --output_ddi_data_file=$indir/petitions.xlsx \
  "
echo "$cmd"
eval "$cmd"
