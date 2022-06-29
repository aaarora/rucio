# Pass files across the following (existing) topology:
# +------------+       +--------------------+
# |            |   1   |                    |
# | T2_US_SDSC |<----->| T2_US_Caltech_Test |
# |            |       |                    |
# +------------+       +--------------------+
#
# NOTE: Must run tools/docker_activate_rucio-sense_rses.sh first!

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
