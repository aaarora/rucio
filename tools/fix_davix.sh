#!/bin/bash

# Fix yum python wrappers...
sed -i "1s/.*/#!\/usr\/bin\/python2/" /usr/bin/yum
sed -i "1s/.*/#!\/usr\/bin\/python2/" /usr/libexec/urlgrabber-ext-down

yum install -y wget

mkdir -p mihai

BASE_URL="https://storage-ci.web.cern.ch/storage-ci/davix/DMC-1291/el7/x86_64"
RPM_FILES="
davix-0.8.0.5.8451c7c-1.el7.cern.x86_64.rpm
davix-debuginfo-0.8.0.5.8451c7c-1.el7.cern.x86_64.rpm
davix-devel-0.8.0.5.8451c7c-1.el7.cern.x86_64.rpm
davix-doc-0.8.0.5.8451c7c-1.el7.cern.noarch.rpm
davix-libs-0.8.0.5.8451c7c-1.el7.cern.x86_64.rpm
davix-tests-0.8.0.5.8451c7c-1.el7.cern.x86_64.rpm
"

cd mihai
for RPM_FILE in $RPM_FILES; do
    wget "$BASE_URL/$RPM_FILE"
    yum install -y ./$RPM_FILE
done
cd ..
