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
# +------+   1   +------+
# |      |<----->|      |
# | XRD1 |       | XRD2 |
# |      |   +-->|      |
# +------+   |   +------+
#    ^       |
#    | 1     | 1
#    v       |
# +------+   |   +------+
# |      |<--+   |      |
# | XRD3 |       | XRD4 |
# |      |<----->|      |
# +------+   2   +------+

# First, create the RSEs
rucio-admin rse add XRD1
rucio-admin rse add XRD2
rucio-admin rse add XRD3
rucio-admin rse add XRD4

# Add the protocol definitions for the storage servers
rucio-admin rse add-protocol --hostname xrd1 --scheme root --prefix //rucio --port 1094 --impl rucio.rse.protocols.xrootd.Default --domain-json '{"wan": {"read": 1, "write": 1, "delete": 1, "third_party_copy": 1}, "lan": {"read": 1, "write": 1, "delete": 1}}' XRD1
rucio-admin rse add-protocol --hostname xrd2 --scheme root --prefix //rucio --port 1095 --impl rucio.rse.protocols.xrootd.Default --domain-json '{"wan": {"read": 1, "write": 1, "delete": 1, "third_party_copy": 1}, "lan": {"read": 1, "write": 1, "delete": 1}}' XRD2
rucio-admin rse add-protocol --hostname xrd3 --scheme root --prefix //rucio --port 1096 --impl rucio.rse.protocols.xrootd.Default --domain-json '{"wan": {"read": 1, "write": 1, "delete": 1, "third_party_copy": 1}, "lan": {"read": 1, "write": 1, "delete": 1}}' XRD3
rucio-admin rse add-protocol --hostname xrd4 --scheme root --prefix //rucio --port 1097 --impl rucio.rse.protocols.xrootd.Default --domain-json '{"wan": {"read": 1, "write": 1, "delete": 1, "third_party_copy": 1}, "lan": {"read": 1, "write": 1, "delete": 1}}' XRD4

# Set test_container_xrd attribute for xrd containers
rucio-admin rse set-attribute --rse XRD1 --key test_container_xrd --value True
rucio-admin rse set-attribute --rse XRD2 --key test_container_xrd --value True
rucio-admin rse set-attribute --rse XRD3 --key test_container_xrd --value True
rucio-admin rse set-attribute --rse XRD4 --key test_container_xrd --value True

# Workaround, xrootd.py#connect returns with Auth Failed due to execution of the command in subprocess
XrdSecPROTOCOL=gsi XRD_REQUESTTIMEOUT=10 xrdfs xrd1:1094 query config xrd1:1094
XrdSecPROTOCOL=gsi XRD_REQUESTTIMEOUT=10 xrdfs xrd2:1095 query config xrd2:1095
XrdSecPROTOCOL=gsi XRD_REQUESTTIMEOUT=10 xrdfs xrd3:1096 query config xrd3:1096
XrdSecPROTOCOL=gsi XRD_REQUESTTIMEOUT=10 xrdfs xrd3:1096 query config xrd4:1097

# Enable FTS
rucio-admin rse set-attribute --rse XRD1 --key fts --value https://fts:8446
rucio-admin rse set-attribute --rse XRD2 --key fts --value https://fts:8446
rucio-admin rse set-attribute --rse XRD3 --key fts --value https://fts:8446
rucio-admin rse set-attribute --rse XRD4 --key fts --value https://fts:8446

# Enable multihop transfers via XRD3
rucio-admin rse set-attribute --rse XRD3 --key available_for_multihop --value True

# Connect the RSEs
rucio-admin rse add-distance --distance 1 --ranking 1 XRD1 XRD2
rucio-admin rse add-distance --distance 1 --ranking 1 XRD1 XRD3
rucio-admin rse add-distance --distance 1 --ranking 1 XRD2 XRD1
rucio-admin rse add-distance --distance 1 --ranking 1 XRD2 XRD3
rucio-admin rse add-distance --distance 1 --ranking 1 XRD3 XRD1
rucio-admin rse add-distance --distance 1 --ranking 1 XRD3 XRD2
rucio-admin rse add-distance --distance 2 --ranking 2 XRD3 XRD4
rucio-admin rse add-distance --distance 2 --ranking 2 XRD4 XRD3

# Indefinite limits for root
rucio-admin account set-limits root XRD1 -1
rucio-admin account set-limits root XRD2 -1
rucio-admin account set-limits root XRD3 -1
rucio-admin account set-limits root XRD4 -1

# Create a default scope for testing
rucio-admin scope add --account root --scope test

# Delegate credentials to FTS
/usr/bin/python2.7 /usr/bin/fts-rest-delegate -vf -s https://fts:8446 -H 9999

# Set throttler limits
XRD3_RSE_ID="$(rucio-admin rse info XRD3 | grep 'rse_id' | awk '{print $2}')"

#cat > temp.py << EOF
#from rucio.core.rse import set_rse_transfer_limits
#set_rse_transfer_limits('$XRD3_RSE_ID', 'User Subscriptions', max_transfers=1)
#EOF
#python temp.py; rm temp.py

rucio-admin config set --section throttler --option "'User Subscriptions,$XRD3_RSE_ID'" --value 1
rucio-admin config set --section throttler --option 'mode' --value 'DEST_PER_ACT'

a=$RANDOM
b=$RANDOM
c=$RANDOM
d=$RANDOM
e=$RANDOM
f=$RANDOM

# Create initial transfer testing data
dd if=/dev/urandom of=file$a bs=1M count=1
dd if=/dev/urandom of=file$b bs=1M count=1
dd if=/dev/urandom of=file$c bs=1M count=1
dd if=/dev/urandom of=file$d bs=1M count=1
dd if=/dev/urandom of=file$e bs=1M count=1
dd if=/dev/urandom of=file$f bs=1M count=1

rucio upload --rse XRD1 --scope test file$a
rucio upload --rse XRD1 --scope test file$b
rucio upload --rse XRD1 --scope test file$c
rucio upload --rse XRD1 --scope test file$d
rucio upload --rse XRD1 --scope test file$e
rucio upload --rse XRD1 --scope test file$f

rucio add-dataset test:dataset$a
rucio attach test:dataset$a test:file$a test:file$b

rucio add-dataset test:dataset$b
rucio attach test:dataset$b test:file$c test:file$d

rucio add-dataset test:dataset$c
rucio attach test:dataset$c test:file$e test:file$f

rucio add-container test:container$d
rucio attach test:container$d test:dataset$a test:dataset$b test:dataset$c

rucio add-rule test:container$d 1 XRD3

## Create complication
#rucio add-dataset test:dataset3
#rucio attach test:dataset3 test:file4
