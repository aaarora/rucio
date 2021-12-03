"""
SENSE Optimizer Prototype
"""

import requests
import logging

cache = {}

def sense_finisher(rule_id, replicas):
    updated_jobs = {}
    for replica in replicas:
        rse_pair_id = __get_rse_pair_id(replica["source_rse_id"], replica["rse_id"])
        if rule_id not in updated_jobs.keys():
            updated_jobs[rule_id] = {}
        if rse_pair_id not in updated_jobs[rule_id].keys():
            updated_jobs[rule_id][rse_pair_id] = 1
        else:
            updated_jobs[rule_id][rse_pair_id] += 1

    requests.post("http://flask:5000/free", json=updated_jobs)

def sense_updater(results_dict):
    print(results_dict)

def sense_preparer(requests_with_sources):
    """
    Parse RequestWithSources objects collected by the preparer daemon and communicate relevant info to DMM

    :param requests_with_sources:    Individual file rse_pairs (see rucio.transfer.RequestWithSource)
    """
    # Collect requested rse_pairs
    prepared_jobs = {}
    for rws in requests_with_sources:
        # Collect file-level metadata
        src_id = rws.sources[0].rse.id # FIXME: can we indeed just take the first one?
        dst_id = rws.dest_rse.id
        # Update rule-level metadata
        rule_id = rws.rule_id
        if rule_id not in prepared_jobs.keys():
            # Initialize rule-level metadata
            prepared_jobs[rule_id] = {
                "rse_pairs": {}, 
                "total_byte_count": 0, 
                "priority": rws.attributes["priority"]
            }
        prepared_jobs[rule_id]["total_byte_count"] += rws.byte_count
        # Update transfer-level metadata
        rse_pair_id = __get_rse_pair_id(src_id, dst_id)
        if rse_pair_id not in prepared_jobs[rule_id]["rse_pairs"].keys():
            # Initialize tranfer-level metadata
            prepared_jobs[rule_id]["rse_pairs"][rse_pair_id] = {
                "source_rse_id": src_id,
                "dest_rse_id": dst_id,
                "n_transfers": 0,
                "byte_count": 0
            }
        prepared_jobs[rule_id]["rse_pairs"][rse_pair_id]["n_transfers"] += 1
        prepared_jobs[rule_id]["rse_pairs"][rse_pair_id]["byte_count"] += rws.byte_count

    # Communicate the collected information to DMM
    response = requests.post("http://flask:5000/cache", json=prepared_jobs)

def sense_optimizer(grouped_jobs):
    """
    Replace source RSE hostname with IPv6 corresponding to chosen SENSE link

    :param grouped_jobs:             Transfers grouped in bulk (see rucio.daemons.conveyor.common)
    """
    global cache
    for external_host in grouped_jobs:
        for job in grouped_jobs[external_host]:
            for file_data in job["files"]:
                rule_id = file_data["rule_id"]
                # Retrieve SENSE mapping
                if rule_id not in cache.keys():
                    __update_cache_with_sense_optimization(rule_id)
                sense_map = cache[rule_id]
                # Get transfer information
                dst_id = file_data["metadata"]["dest_rse_id"]
                src_id = file_data["metadata"]["src_rse_id"]
                rse_pair_id = __get_rse_pair_id(src_id, dst_id)
                # Update source
                (src_name, src_url, src_id, src_retries) = file_data["sources"][0]
                src_host = __get_hostname(src_url)
                src_sense_url = src_url.replace(src_host, sense_map[rse_pair_id][src_id], 1)
                file_data["sources"][0] = (src_name, src_sense_url, src_id, src_retries)
                # Update destination
                dst_url = file_data["destinations"][0]
                dst_host = __get_hostname(dst_url)
                dst_sense_url = dst_url.replace(dst_host, sense_map[rse_pair_id][dst_id], 1)
                file_data["destinations"] = [dst_sense_url]

def __get_rse_pair_id(src_rse_id, dst_rse_id):
    return f"{src_rse_id}&{dst_rse_id}"

def __get_hostname(uri):
    # Assumes the url is something like "root://hostname//path"
    # TODO: Need to make more universal for other url formats.
    return uri.split("//")[1].split(":")[0]

def __update_cache_with_sense_optimization(rule_id):
    # Replacing sense with psudo dns server in flask (image in main dir)
    global cache
    request_args = f"rule_id={rule_id}&metadata_key=sense_map" 
    response = requests.get(f"http://flask:5000/cache?{request_args}").json()
    cache.update({rule_id: response})
