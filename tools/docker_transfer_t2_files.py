from rucio.client import Client

client = Client()

client.add_replicas(
    "T2_US_UCSD", 
    [
        {
            "scope": "cms", 
            "name": "/store/mc/RunIISummer20UL17NanoAODv9/TTJets_TuneCP5_13TeV-amcatnloFXFX-pythia8/NANOAODSIM/106X_mc2017_realistic_v9-v1/280000/13A49B24-F430-6642-B7A2-36E4FE7C1FE4.root", 
            "bytes": 2921259
        }
    ]
)

client.update_rse("T2_US_UCSD", {"lfn2pfn_algorithm": "cmstfc"})
