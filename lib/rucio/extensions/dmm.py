"""
SENSE Optimizer Prototype
"""

import requests
import logging

cache = {}

def sense_finisher(replicas):
    """
    Parse replicas and update SENSE on how many jobs (per source+dest RSE pair) have finished via DMM

    :param replicas:    Individual replicas produced by now-finished transfers
    """
    updated_jobs = {}
    for replica in replicas:
        rse_pair_id = __get_rse_pair_id(replica["source_rse_id"], replica["dest_rse_id"])
        priority = __get_prio_code(replica["priority"])
        if priority not in updated_jobs.keys():
            updated_jobs[priority] = {}
        if rse_pair_id not in updated_jobs[priority].keys():
            updated_jobs[priority][rse_pair_id] = {
                "finished_transfers": 1,
                "transferred_bytes": replica["bytes"]
            }
        else:
            updated_jobs[priority][rse_pair_id]["finished_transfers"] += 1
            updated_jobs[priority][rse_pair_id]["transferred_bytes"] += replica["bytes"]

    requests.post("http://flask:5000/free", json=updated_jobs)

def sense_updater(results_dict):
    print(results_dict)

def sense_preparer(requests_with_sources):
    """
    Parse RequestWithSources objects collected by the preparer daemon and communicate relevant info to
    SENSE via DMM

    :param requests_with_sources:    Individual file rse_pairs (see rucio.transfer.RequestWithSource)
    """
    # Collect requested rse_pairs
    prepared_jobs = {}
    for rws in requests_with_sources:
        # Update priority-level metadata
        priority = __get_prio_code(rws.attributes["priority"])
        if priority not in prepared_jobs.keys():
            # Initialize priority-level metadata
            prepared_jobs[priority] = {}
        # Update transfer-level metadata
        src_id = rws.sources[0].rse.id # FIXME: can we indeed just take the first one?
        dst_id = rws.dest_rse.id
        rse_pair_id = __get_rse_pair_id(src_id, dst_id)
        if rse_pair_id not in prepared_jobs[priority].keys():
            # Initialize transfer-level metadata
            prepared_jobs[priority][rse_pair_id] = {
                "source_rse_id": src_id,
                "dest_rse_id": dst_id,
                "total_transfers": 0,
                "total_bytes": 0
            }
        prepared_jobs[priority][rse_pair_id]["total_transfers"] += 1
        prepared_jobs[priority][rse_pair_id]["total_bytes"] += rws.byte_count

    # Communicate the collected information to SENSE via DMM
    response = requests.post("http://flask:5000/sense", json=prepared_jobs)

def sense_optimizer(grouped_jobs):
    """
    Replace source RSE hostname with SENSE link

    :param grouped_jobs:             Transfers grouped in bulk (see rucio.daemons.conveyor.common)
    """
    global cache
    # Count submissions and sort by priority, rse pair
    submission_counts = {}
    for external_host in grouped_jobs:
        for job in grouped_jobs[external_host]:
            for file_data in job["files"]:
                # Get transfer information
                dst_id = file_data["metadata"]["dest_rse_id"]
                src_id = file_data["metadata"]["src_rse_id"]
                rse_pair_id = __get_rse_pair_id(src_id, dst_id)
                priority = __get_prio_code(file_data["priority"])
                if priority not in submission_counts.keys():
                    submission_counts[priority] = {}
                counts = submission_counts[priority]
                if rse_pair_id not in counts.keys():
                    counts[rse_pair_id] = 1
                else:
                    counts[rse_pair_id] += 1
                submission_counts[priority].update(counts)
    # Do SENSE link replacement
    for external_host in grouped_jobs:
        for job in grouped_jobs[external_host]:
            for file_data in job["files"]:
                # Get transfer information
                dst_id = file_data["metadata"]["dest_rse_id"]
                src_id = file_data["metadata"]["src_rse_id"]
                rse_pair_id = __get_rse_pair_id(src_id, dst_id)
                priority = __get_prio_code(file_data["priority"])
                # Retrieve SENSE mapping
                if priority not in cache.keys() or rse_pair_id not in cache[priority].keys():
                    __update_cache_with_sense_optimization(
                        priority, 
                        rse_pair_id, 
                        submission_counts[priority][rse_pair_id]
                    )
                sense_map = cache[priority][rse_pair_id]
                # Update source
                (src_name, src_url, src_id, src_retries) = file_data["sources"][0]
                src_host = __get_hostname(src_url)
                src_sense_url = src_url.replace(src_host, sense_map[src_id], 1)
                file_data["sources"][0] = (src_name, src_sense_url, src_id, src_retries)
                # Update destination
                dst_url = file_data["destinations"][0]
                dst_host = __get_hostname(dst_url)
                dst_sense_url = dst_url.replace(dst_host, sense_map[dst_id], 1)
                file_data["destinations"] = [dst_sense_url]

def __get_prio_code(priority):
    return f"PRIO_{priority}"

def __get_rse_pair_id(src_rse_id, dst_rse_id):
    return f"{src_rse_id}&{dst_rse_id}"

def __get_hostname(uri):
    # Assumes the url is something like "root://hostname//path"
    # TODO: Need to make more universal for other url formats.
    return uri.split("//")[1].split(":")[0]

def __update_cache_with_sense_optimization(priority, rse_pair_id, submitted_transfers):
    """ Fetch and cache SENSE mappings via DMM """
    global cache
    response = requests.get(
        "http://flask:5000/sense", 
        json={
            "priority": priority, 
            "rse_pair_id": rse_pair_id, 
            "submitted_transfers": submitted_transfers
        }
    )
    if priority not in cache.keys():
        cache[priority] = {rse_pair_id: response.json()}
    else:
        cache[priority].update({rse_pair_id: response.json()})
