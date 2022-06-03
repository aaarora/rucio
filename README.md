# Hacked Rucio for Rucio-SENSE tests

## General

1. Edit `etc/certs/generate.sh` and add a secure password:
```diff
#!/bin/bash
- export PASSPHRASE=123456
+ export PASSPHRASE=verysecurepassword
```

2. Create certs (be sure to install them on any XRootD clusters involved)
```
cd etc/certs
sh generate.sh
cd -
```

3. Clone DMM and follow all set-up [instructions](https://github.com/jkguiang/rucio-sense-dmm/blob/main/README.md)
```
git clone https://github.com/jkguiang/rucio-sense-dmm
```

4. Spool up containers
```
docker-compose --file etc/docker/dev/docker-compose-storage-host-network-custom-certs.yml up -d
```

5. Update `davix` and `gfal2` on the FTS container:
```
docker exec -it dev_fts_1 /bin/bash
yum install -y davix gfal2
exit
```

## Rucio

1. Set up Rucio (updates `davix` and installs `sense-o-api` automatically)
```
docker exec -it dev_rucio_1 /bin/bash
./tools/run_tests_docker.sh -i
```

2. Set up RSEs (after making any necessary changes)
```
./tools/docker_activate_rucio-sense_rses.sh
```

3. Keep this running

## DMM

1. Set up DMM
```
docker exec -it dev_rucio_1 /bin/bash
cd rucio-sense-dmm
cp .sense-o-auth.yaml ~/
export PYTHONPATH=${PWD}/src:$PYTHONPATH
```

2. Start DMM
```
./bin/dmm --loglevel DEBUG
```

3. Keep this running

## Run tests

Run Rucio daemons one-by-one and watch DMM logs
```
./bin/rucio-conveyor-preparer --run-once --sense
./bin/rucio-conveyor-throttler --run-once
./bin/rucio-conveyor-submitter --run-once --sense
./bin/rucio-conveyor-poller --run-once
./bin/rucio-conveyor-preparer --run-once --sense
```
