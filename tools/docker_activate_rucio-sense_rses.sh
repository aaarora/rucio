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
# +---------+       +---------+
# |         |   1   |         |
# | T2_US_SDSC |<----->| T2_US_Caltech_Test |
# |         |       |         |
# +---------+       +---------+

# First, create the RSEs
rucio-admin rse add T2_US_SDSC
rucio-admin rse add T2_US_Caltech_Test

# Add the protocol definitions for the storage servers
rucio-admin rse add-protocol \
    --hostname [2001:48d0:3001:113::300] \
    --scheme https \
    --prefix // \
    --port 1096 \
    --impl rucio.rse.protocols.gfalv2.Default \
    --domain-json '{"wan": {"read": 1, "write": 1, "delete": 1, "third_party_copy": 1}, "lan": {"read": 1, "write": 1, "delete": 1}}' \
    T2_US_SDSC
rucio-admin rse add-protocol \
    --hostname sense-origin-03.ultralight.org \
    --scheme https \
    --prefix //store/temp \
    --port 1096 \
    --impl rucio.rse.protocols.gfalv2.Default \
    --domain-json '{"wan": {"read": 1, "write": 1, "delete": 1, "third_party_copy": 1}, "lan": {"read": 1, "write": 1, "delete": 1}}' \
    T2_US_Caltech_Test

# Set test_container_xrd attribute for xrd containers
rucio-admin rse set-attribute --rse T2_US_SDSC --key test_container_xrd --value True
rucio-admin rse set-attribute --rse T2_US_Caltech_Test --key test_container_xrd --value True

# Enable FTS
rucio-admin rse set-attribute --rse T2_US_SDSC --key fts --value https://fts:8446
rucio-admin rse set-attribute --rse T2_US_Caltech_Test --key fts --value https://fts:8446

# Enable multihop transfers via T2_US_Caltech_Test
rucio-admin rse set-attribute --rse T2_US_Caltech_Test --key available_for_multihop --value True

# Connect the RSEs
rucio-admin rse add-distance --distance 1 --ranking 1 T2_US_SDSC T2_US_Caltech_Test

# Indefinite limits for root
rucio-admin account set-limits root T2_US_SDSC -1
rucio-admin account set-limits root T2_US_Caltech_Test -1

# Create a default scope for testing
rucio-admin scope add --account root --scope cms

# Delegate credentials to FTS
/usr/bin/python2.7 /usr/bin/fts-rest-delegate -vf -s https://fts:8446 -H 9999

# Set throttler limits
DEST_RSE_ID="$(rucio-admin rse info T2_US_Caltech_Test | grep 'rse_id' | awk '{print $2}')"

cat > temp.py << EOF
from rucio.core.rse import set_rse_transfer_limits
set_rse_transfer_limits('$DEST_RSE_ID', 'User Subscriptions', max_transfers=1)
EOF
python temp.py; rm temp.py

rucio-admin config set --section throttler --option "'User Subscriptions,$DEST_RSE_ID'" --value 1
rucio-admin config set --section throttler --option 'mode' --value 'DEST_PER_ACT'

a=$RANDOM
b=$RANDOM
c=$RANDOM
d=$RANDOM

# Create initial transfer testing data
dd if=/dev/urandom of=file$a bs=1M count=1
dd if=/dev/urandom of=file$b bs=1M count=1

rucio -vvv upload --rse T2_US_SDSC --scope cms file$a
rucio -vvv upload --rse T2_US_SDSC --scope cms file$b

rucio add-dataset cms:dataset$a
rucio attach cms:dataset$a cms:file$a cms:file$b

rucio add-container cms:container$c
rucio attach cms:container$c cms:dataset$a

rucio add-rule cms:container$c 1 T2_US_Caltech_Test
