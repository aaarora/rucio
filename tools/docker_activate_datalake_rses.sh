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
# +------------+       +----------------------+
# |            |   1   |                      |
# | T2_US_UCSD |------>| DATALAKE_ORIGIN_2811 |
# |            |       |                      |
# +------------+       +----------------------+

# First, create the RSEs
rucio-admin rse add DATALAKE_ORIGIN_2811 # Destination 1
rucio-admin rse add T2_US_UCSD           # Source

# Add the protocol definitions for the Data Lake server
rucio-admin rse add-protocol --hostname k8s1-pb10.ultralight.org \
    --scheme https --prefix // --port 2811 \
    --impl rucio.rse.protocols.gfalv2.Default \
    --domain-json '{"wan": {"read": 1, "write": 1, "delete": 1, "third_party_copy": 1}, "lan": {"read": 1, "write": 1, "delete": 1}}' \
    DATALAKE_ORIGIN_2811

# Add the protocol definitions for the UCSD T2 server
rucio-admin rse add-protocol --hostname gftp-1.t2.ucsd.edu \
    --scheme https --prefix // --port 1094 \
    --impl rucio.rse.protocols.gfalv2.Default \
    --domain-json '{"wan": {"read": 1, "write": 0, "delete": 0, "third_party_copy": 1}, "lan": {"read": 1, "write": 0, "delete": 0}}' \
    T2_US_UCSD

# Set test_container_xrd attribute for xrd containers
rucio-admin rse set-attribute --rse DATALAKE_ORIGIN_2811 --key test_container_xrd --value True
rucio-admin rse set-attribute --rse T2_US_UCSD --key test_container_xrd --value True

# Enable FTS
rucio-admin rse set-attribute --rse DATALAKE_ORIGIN_2811 --key fts --value https://fts:8446
rucio-admin rse set-attribute --rse T2_US_UCSD --key fts --value https://fts:8446

# Enable multihop transfers via DATALAKE_ORIGIN_2811
rucio-admin rse set-attribute --rse DATALAKE_ORIGIN_2811 --key available_for_multihop --value True

# Connect the RSEs
rucio-admin rse add-distance --distance 1 --ranking 1 T2_US_UCSD DATALAKE_ORIGIN_2811

# Indefinite limits for root
rucio-admin account set-limits root DATALAKE_ORIGIN_2811 -1
rucio-admin account set-limits root T2_US_UCSD -1

# Delegate credentials to FTS
/usr/bin/python2.7 /usr/bin/fts-rest-delegate -vf -s https://fts:8446 -H 9999

# # Set throttler limits
# DEST_RSE_ID="$(rucio-admin rse info DATALAKE_ORIGIN_2811 | grep 'rse_id' | awk '{print $2}')"
# MAX_TRANSFERS=1

# cat > temp.py << EOF
# from rucio.core.rse import set_rse_transfer_limits
# set_rse_transfer_limits('$DEST_RSE_ID', 'User Subscriptions', max_transfers=$MAX_TRANSFERS)
# EOF
# python temp.py; rm temp.py

# rucio-admin config set --section throttler --option "'User Subscriptions,$DEST_RSE_ID'" --value 1
# rucio-admin config set --section throttler --option 'mode' --value 'DEST_PER_ACT'

# Make some random numbers (for various naming purposes)
a=$RANDOM
b=$RANDOM
c=$RANDOM
d=$RANDOM
e=$RANDOM

# Create initial transfer testing data
dd if=/dev/urandom of=file$a bs=1M count=1
dd if=/dev/urandom of=file$b bs=1M count=1

# Create a default scope for testing
rucio-admin scope add --account root --scope scope$e

rucio upload --rse DATALAKE_ORIGIN_2811 --scope scope$e file$a
rucio upload --rse DATALAKE_ORIGIN_2811 --scope scope$e file$b

rucio add-dataset scope$e:dataset$c
rucio attach scope$e:dataset$c scope$e:file$a scope$e:file$b

rucio add-container scope$e:container$d
rucio attach scope$e:container$d scope$e:dataset$c

