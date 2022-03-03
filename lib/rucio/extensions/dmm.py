"""
SENSE Optimizer Prototype
"""

import logging
from multiprocessing.connection import Client
from rucio.core.rse import get_rse_name

cache = {}

ADDRESS = ("localhost", 5000)
AUTHKEY = b"secret password"

def sense_finisher(rule_id, replicas):
    """
    Parse replicas and update SENSE on how many jobs (per source+dest RSE pair) have 
    finished via DMM

    :param rule_id:     Rucio rule ID
    :param replicas:    Individual replicas produced by now-finished transfers
    """
    finisher_report = {
        "rule_id": rule_id,
        "n_transfers_finished": 0,
        "n_bytes_transferred": 0
    }
    for replica in replicas:
        finisher_reports[rule_id]["n_transfers_finished"] += 1
        finisher_reports[rule_id]["n_bytes_transferred"] += replica["bytes"]

    with Client(ADDRESS, authkey=AUTHKEY) as client:
        client.send(("FINISHER", finisher_reports))

def sense_updater(results_dict):
    print(results_dict)

def sense_preparer(requests_with_sources):
    """
    Parse RequestWithSources objects collected by the preparer daemon and communicate 
    relevant info to SENSE via DMM

    :param requests_with_sources:    List of rucio.transfer.RequestWithSource objects
    """
    prepared_rules = {}
    for rws in requests_with_sources:
        if rws.rule_id not in prepared_rules.keys():
            prepared_rules[rws.rule_id] = {
                "src_rse_name": rws.sources[0].rse.name, # FIXME: can we always take the first one?
                "dst_rse_name": get_rse_name(rws.dest_rse.id),
                "attr": {
                    "request_ids": [],
                    "priority": rws.attributes["priority"],
                    "n_transfers_total": 0,
                    "n_bytes_total": 0
                }
            }
        prepared_rules[rws.rule_id]["attr"]["request_ids"].append(rws.request_id)
        prepared_rules[rws.rule_id]["attr"]["n_transfers_total"] += 1
        prepared_rules[rws.rule_id]["attr"]["n_bytes_total"] += rws.byte_count

    with Client(ADDRESS, authkey=AUTHKEY) as client:
        client.send(("PREPARER", prepared_rules))

def sense_optimizer(grouped_jobs):
    """
    Replace source RSE hostname with SENSE link

    :param grouped_jobs:             Transfers grouped in bulk (see rucio.daemons.conveyor.common)
    """
    global cache
    # Count submissions and sort by rule id
    submitter_reports = {}
    for external_host in grouped_jobs:
        for job in grouped_jobs[external_host]:
            for file_data in job["files"]:
                rule_id = file_data["rule_id"]
                if rule_id not in submitter_reports.keys():
                    submitter_reports[rule_id] = 0
                submitter_reports[rule_id] += 1
    # Do SENSE link replacement
    for external_host in grouped_jobs:
        for job in grouped_jobs[external_host]:
            for file_data in job["files"]:
                rule_id = file_data["rule_id"]
                # Retrieve SENSE mapping
                if rule_id not in cache.keys():
                    __update_cache_with_sense_optimization(
                        rule_id,
                        submitter_reports[rule_id]
                    )
                sense_map = cache[rule_id]
                # Update source
                (src_name, src_url, src_id, src_retries) = file_data["sources"][0]
                src_hostname = __get_hostname(src_url)
                src_sense_url = src_url.replace(src_hostname, sense_map[src_name], 1)
                file_data["sources"][0] = (src_name, src_sense_url, src_id, src_retries)
                # Update destination
                dst_name = file_data["metadata"]["dst_rse"]
                dst_url = file_data["destinations"][0]
                dst_hostname = __get_hostname(dst_url)
                dst_sense_url = dst_url.replace(dst_hostname, sense_map[dst_name], 1)
                file_data["destinations"] = [dst_sense_url]

def __get_hostname(uri):
    # Assumes the url is something like "root://hostname//path"
    # TODO: Need to make more universal for other url formats.
    return uri.split("//")[1].split(":")[0]

def __update_cache_with_sense_optimization(rule_id, n_transfers_submitted):
    """ Fetch and cache SENSE mappings via DMM """
    global cache
    with Client(ADDRESS, authkey=AUTHKEY) as client:
        submitter_report = {
            "rule_id": rule_id,
            "n_transfers_submitted": n_transfers_submitted
        }
        client.send(("SUBMITTER", submitter_report))
        response = client.recv()

    if rule_id not in cache.keys():
        cache[rule_id] = response
    else:
        cache[rule_id].update(response)
