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
# | XRD_SRC |<----->| XRD_DST |
# |         |       |         |
# +---------+       +---------+

# First, create the RSEs
rucio-admin rse add XRD_SRC
rucio-admin rse add XRD_DST

# Add the protocol definitions for the storage servers
rucio-admin rse add-protocol --hostname [2607:f720:1720:e00e:ec4:7aff:febb:c04e] --scheme https --prefix // --port 2094 --impl rucio.rse.protocols.gfalv2.Default --domain-json '{"wan": {"read": 1, "write": 1, "delete": 1, "third_party_copy": 1}, "lan": {"read": 1, "write": 1, "delete": 1}}' XRD_SRC
rucio-admin rse add-protocol --hostname [2607:f720:1720:e00e:ec4:7aff:febb:c04f] --scheme https --prefix // --port 2095 --impl rucio.rse.protocols.gfalv2.Default --domain-json '{"wan": {"read": 1, "write": 1, "delete": 1, "third_party_copy": 1}, "lan": {"read": 1, "write": 1, "delete": 1}}' XRD_DST

# Set test_container_xrd attribute for xrd containers
rucio-admin rse set-attribute --rse XRD_SRC --key test_container_xrd --value True
rucio-admin rse set-attribute --rse XRD_DST --key test_container_xrd --value True

# Enable FTS
rucio-admin rse set-attribute --rse XRD_SRC --key fts --value https://fts:8446
rucio-admin rse set-attribute --rse XRD_DST --key fts --value https://fts:8446

# Enable multihop transfers via XRD_DST
rucio-admin rse set-attribute --rse XRD_DST --key available_for_multihop --value True

# Connect the RSEs
rucio-admin rse add-distance --distance 1 --ranking 1 XRD_SRC XRD_DST

# Indefinite limits for root
rucio-admin account set-limits root XRD_SRC -1
rucio-admin account set-limits root XRD_DST -1

# Create a default scope for testing
rucio-admin scope add --account root --scope test

# Delegate credentials to FTS
/usr/bin/python2.7 /usr/bin/fts-rest-delegate -vf -s https://fts:8446 -H 9999

# Set throttler limits
DEST_RSE_ID="$(rucio-admin rse info XRD_DST | grep 'rse_id' | awk '{print $2}')"

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

rucio -vvv upload --rse XRD_SRC --scope test file$a
rucio -vvv upload --rse XRD_SRC --scope test file$b

rucio add-dataset test:dataset$a
rucio attach test:dataset$a test:file$a test:file$b

rucio add-container test:container$c
rucio attach test:container$c test:dataset$a

rucio add-rule test:container$c 1 XRD_DST
