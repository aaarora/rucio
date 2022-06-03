#!/bin/bash
# Copyright 2017-2021 CERN
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
# - Thomas Beermann <thomas.beermann@cern.ch>, 2017-2018
# - Vincent Garonne <vincent.garonne@cern.ch>, 2018
# - Hannes Hansen <hannes.jakob.hansen@cern.ch>, 2018-2019
# - Mario Lassnig <mario.lassnig@cern.ch>, 2019-2020
# - Martin Barisits <martin.barisits@cern.ch>, 2019
# - Andrew Lister <andrew.lister@stfc.ac.uk>, 2019
# - Patrick Austin <patrick.austin@stfc.ac.uk>, 2020
# - Cedric Serfon <cedric.serfon@cern.ch>, 2020
# - Eli Chadwick <eli.chadwick@stfc.ac.uk>, 2020
# - Benedikt Ziemons <benedikt.ziemons@cern.ch>, 2020-2021

sh tools/fix_davix.sh
pip3 install sense-o-api==1.23

memcached -u root -d

function usage {
  echo "Usage: $0 [OPTION]..."
  echo 'Run Rucio test suite'
  echo ''
  echo '  -h    Show usage'
  echo '  -i    Do only the initialization'
  echo '  -r    Activate RSEs'
  echo '  -s    Run special tests for Dirac. Includes using BelleII schema'
  echo '  -t    Verbose output from pytest'
  echo '  -a    Skip alembic downgrade/upgrade test'
  echo '  -x    exit instantly on first error or failed test'
  echo '  -d    set up for US-CMS Data Lake tests (sets up Rucio-SENSE tests by default)'
  exit
}

datalake="false"
while getopts hirstaxd opt
do
  case "$opt" in
    h) usage;;
    i) init_only="true";;
    r) activate_rse="true";;
    s) special="true";;
    t) trace="true";;
    a) noalembic="true";;
    x) exitfirst="-x";;
    d) datalake="true";; # sets up for Rucio-SENSE test by default
  esac
done
export RUCIO_HOME=/opt/etc/test

# DEBUG
nl=$'\n'
sed -i "s/\[conveyor\]/\[conveyor\]""\\${nl}""use_preparer\ \=\ True/g" etc/rucio.cfg
if [[ "$datalake" == "true" ]]; then
    sed -i "s/schema\ \=\ atlas/schema\ \=\ cms/g" etc/rucio.cfg
    sed -i "s/permission\ \=\ atlas/permission\ \=\ cms/g" etc/rucio.cfg
    cp tools/lfn2pfn_algorithms/*.py /usr/local/lib/python3.6/site-packages/
    chmod 755 /usr/local/lib/python3.6/site-packages/cmstfc.py
fi

echo 'Clearing memcache'
echo flush_all > /dev/tcp/127.0.0.1/11211

echo 'Graceful restart of Apache'
httpd -k graceful

echo 'Cleaning old authentication tokens'
rm -rf /tmp/.rucio_*/

echo 'Cleaning local RSE directories'
rm -rf /tmp/rucio_rse/*

echo 'Removing old SQLite databases'
rm -f /tmp/rucio.db

if test ${special}; then
    if [ -f /opt/rucio/etc/rucio.cfg ]; then
        echo 'Remove rucio.cfg'
        rm /opt/rucio/etc/rucio.cfg
    fi
    echo 'Using the special config'
    ln -s /opt/rucio/etc/rucio.cfg.special /opt/rucio/etc/rucio.cfg
else
    if [ -f /opt/rucio/etc/rucio.cfg ]; then
        echo 'Using the standard config'
    else
        echo 'rucio.cfg not found. Will try to do a symlink'
        ln -s /opt/rucio/etc/rucio.cfg.default /opt/rucio/etc/rucio.cfg
    fi
fi

echo 'Resetting database tables'
tools/reset_database.py
if [ $? != 0 ]; then
    echo 'Failed to reset the database!'
    exit 1
fi

if [ -f /tmp/rucio.db ]; then
    echo 'Disable SQLite database access restriction'
    chmod 777 /tmp/rucio.db
fi

if test ${noalembic}; then
    echo "Skipping alembic migration"
else
    echo "Running full alembic migration"
    ALEMBIC_CONFIG="/opt/rucio/etc/alembic.ini" tools/alembic_migration.sh
    if [ $? != 0 ]; then
	echo 'Failed to run alembic migration!'
	exit 1
    fi
fi

#if [[ "$datalake" == "false" ]]; then # Run tests that rely on ATLAS lfn2pfn
#    echo 'Bootstrapping tests'
#    tools/bootstrap_tests.py
#    if [ $? != 0 ]; then
#        echo 'Failed to bootstrap!'
#        exit 1
#    fi
#
#    echo 'Sync rse_repository'
#    if test ${special}; then
#        tools/sync_rses.py etc/rse_repository.json.special
#        if [ $? != 0 ]; then
#            echo 'Failed to sync!'
#            exit 1
#        fi
#    else
#        tools/sync_rses.py
#        if [ $? != 0 ]; then
#            echo 'Failed to sync!'
#            exit 1
#        fi
#    fi
#
#    echo 'Sync metadata keys'
#    tools/sync_meta.py
#    if [ $? != 0 ]; then
#        echo 'Failed to sync!'
#        exit 1
#    fi
#fi

if test ${activate_rse}; then
    if [[ "$datalake" == "true" ]]; then
        echo 'Activating US-CMS Data Lake RSEs'
        tools/docker_activate_datalake_rses.sh
    else
        echo 'Activating Rucio-SENSE RSEs'
        tools/docker_activate_nrp_rses.sh
    fi
fi

if test ${init_only}; then
    exit
fi

if test ${special}; then
    echo 'Using the special config and only running test_dirac'
    tools/pytest.sh -v --tb=short ${exitfirst:-} test_dirac.py
else
    if test ${trace}; then
        echo 'Running tests in verbose mode'
        tools/pytest.sh -vvv ${exitfirst:-}
    else
        echo 'Running tests'
        tools/pytest.sh -v --tb=short ${exitfirst:-}
    fi
fi

exit $?
