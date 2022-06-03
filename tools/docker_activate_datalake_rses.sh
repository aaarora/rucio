#!/bin/bash
# Copyright 2019 CERN for the benefit of the ATLAS collaboration.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# Authors:
# - Mario Lassnig <mario.lassnig@cern.ch>, 2019
# - Radu Carpa <radu.carpa@cern.ch>, 2021

# Create the following topology:
# +------------+       +----------------------------+
# |            |   1   |                            |
# | T2_US_UCSD |------>| T2_US_DATALAKE_ORIGIN_2811 |
# |            |       |                            |
# +------------+       +----------------------------+

# First, create the RSEs
rucio-admin rse add T2_US_DATALAKE_ORIGIN_2811 # Destination 1
rucio-admin rse add T2_US_UCSD                 # Source

# Add the protocol definitions for the Data Lake server
rucio-admin rse add-protocol --hostname k8s1-pb10.ultralight.org \
    --scheme https --prefix // --port 2811 \
    --impl rucio.rse.protocols.gfalv2.Default \
    --domain-json '{"wan": {"read": 1, "write": 1, "delete": 1, "third_party_copy": 1}, "lan": {"read": 1, "write": 1, "delete": 1}}' \
    T2_US_DATALAKE_ORIGIN_2811

# Add the protocol definitions for the UCSD T2 server
rucio-admin rse add-protocol --hostname gftp-1.t2.ucsd.edu \
    --scheme https --prefix // --port 1094 \
    --impl rucio.rse.protocols.gfalv2.Default \
    --domain-json '{"wan": {"read": 1, "write": 0, "delete": 0, "third_party_copy": 1}, "lan": {"read": 1, "write": 0, "delete": 0}}' \
    T2_US_UCSD

rucio-admin rse set-attribute --rse T2_US_UCSD --key lfn2pfn_algorithm --value cmstfc

# Set test_container_xrd attribute for xrd containers
rucio-admin rse set-attribute --rse T2_US_DATALAKE_ORIGIN_2811 --key test_container_xrd --value True
rucio-admin rse set-attribute --rse T2_US_UCSD --key test_container_xrd --value True

# Enable FTS
rucio-admin rse set-attribute --rse T2_US_DATALAKE_ORIGIN_2811 --key fts --value https://fts:8446
rucio-admin rse set-attribute --rse T2_US_UCSD --key fts --value https://fts:8446

# Enable multihop transfers via T2_US_DATALAKE_ORIGIN_2811
rucio-admin rse set-attribute --rse T2_US_DATALAKE_ORIGIN_2811 --key available_for_multihop --value True

# Connect the RSEs
rucio-admin rse add-distance --distance 1 --ranking 1 T2_US_UCSD T2_US_DATALAKE_ORIGIN_2811

# Indefinite limits for root
rucio-admin account set-limits root T2_US_DATALAKE_ORIGIN_2811 -1
rucio-admin account set-limits root T2_US_UCSD -1

# Delegate credentials to FTS
/usr/bin/python2.7 /usr/bin/fts-rest-delegate -vf -s https://fts:8446 -H 9999

# # Set throttler limits
# DEST_RSE_ID="$(rucio-admin rse info T2_US_DATALAKE_ORIGIN_2811 | grep 'rse_id' | awk '{print $2}')"
# MAX_TRANSFERS=1

# cat > temp.py << EOF
# from rucio.core.rse import set_rse_transfer_limits
# set_rse_transfer_limits('$DEST_RSE_ID', 'User Subscriptions', max_transfers=$MAX_TRANSFERS)
# EOF
# python temp.py; rm temp.py

# rucio-admin config set --section throttler --option "'User Subscriptions,$DEST_RSE_ID'" --value 1
# rucio-admin config set --section throttler --option 'mode' --value 'DEST_PER_ACT'

rucio-admin scope add --account root --scope cms

python tools/docker_transfer_t2_files.py

rucio add-rule cms:/store/mc/RunIISummer20UL17NanoAODv9/TTJets_TuneCP5_13TeV-amcatnloFXFX-pythia8/NANOAODSIM/106X_mc2017_realistic_v9-v1/280000/13A49B24-F430-6642-B7A2-36E4FE7C1FE4.root 1 T2_US_DATALAKE_ORIGIN_2811
