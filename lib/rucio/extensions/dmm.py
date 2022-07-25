"""
SENSE Optimizer Prototype
"""

import logging
from multiprocessing.connection import Client
from rucio.core.rse import get_rse_name

ADDRESS = ("localhost", 5000)
AUTHKEY = b"secret password"

def sense_finisher(rule_id, replicas):
    """
    Parse replicas and update SENSE on how many jobs (per source+dest RSE pair) have 
    finished via DMM

    :param rule_id:     Rucio rule ID
    :param replicas:    Individual replicas produced by now-finished transfers
    """
    finisher_reports = {}
    for replica in replicas:
        src_name = get_rse_name(replica["source_rse_id"])
        dst_name = get_rse_name(replica["dest_rse_id"])
        rse_pair_id = __get_rse_pair_id(src_name, dst_name) # FIXME: probably wrong
        if rse_pair_id not in finisher_reports.keys():
            finisher_reports[rse_pair_id] = {
                "n_transfers_finished": 0,
                "n_bytes_transferred": 0,
                "external_ids": []
            }
        finisher_reports[rse_pair_id]["n_transfers_finished"] += 1
        finisher_reports[rse_pair_id]["n_bytes_transferred"] += replica["bytes"]
        finisher_reports[rse_pair_id]["external_ids"].append(replica["external_id"])

    with Client(ADDRESS, authkey=AUTHKEY) as client:
        client.send(("FINISHER", {rule_id: finisher_reports}))

def sense_updater(*args, **kwargs):
    return

def sense_preparer(requests_with_sources):
    """
    Parse RequestWithSources objects collected by the preparer daemon and communicate 
    relevant info to SENSE via DMM

    :param requests_with_sources:    List of rucio.transfer.RequestWithSource objects
    """
    prepared_rules = {}
    for rws in requests_with_sources:
        # Check if rule has been accounted for
        if rws.rule_id not in prepared_rules.keys():
            prepared_rules[rws.rule_id] = {}
        # Check if RSE pair has been accounted for
        src_name = rws.sources[0].rse.name # FIXME: can we always take the first one?
        dst_name = get_rse_name(rws.dest_rse.id)
        rse_pair_id = __get_rse_pair_id(src_name, dst_name)
        if rse_pair_id not in prepared_rules[rws.rule_id].keys():
            prepared_rules[rws.rule_id][rse_pair_id] = {
                "transfer_ids": [],
                "priority": rws.attributes["priority"],
                "n_transfers_total": 0,
                "n_bytes_total": 0
            }
        # Update request attributes
        prepared_rules[rws.rule_id][rse_pair_id]["transfer_ids"].append(rws.request_id)
        prepared_rules[rws.rule_id][rse_pair_id]["n_transfers_total"] += 1
        prepared_rules[rws.rule_id][rse_pair_id]["n_bytes_total"] += rws.byte_count

    with Client(ADDRESS, authkey=AUTHKEY) as client:
        client.send(("PREPARER", prepared_rules))

def sense_optimizer(grouped_jobs):
    """
    Replace source RSE hostname with SENSE link

    :param grouped_jobs:             Transfers grouped in bulk (see rucio.daemons.conveyor.common)
    """
    global cache
    # Count submissions and sort by rule ID and RSE pair ID
    submitter_reports = {}
    for external_host in grouped_jobs:
        for job in grouped_jobs[external_host]:
            # Parse all file transfers
            for file_data in job["files"]:
                # Get rule ID
                rule_id = file_data["rule_id"]
                if rule_id not in submitter_reports.keys():
                    submitter_reports[rule_id] = {}
                # Get RSE pair ID
                src_name = file_data["metadata"]["src_rse"]
                dst_name = file_data["metadata"]["dst_rse"]
                rse_pair_id = __get_rse_pair_id(src_name, dst_name)
                # Count transfers
                if rse_pair_id not in submitter_reports[rule_id].keys():
                    submitter_reports[rule_id][rse_pair_id] = {
                        "priority": file_data["priority"],
                        "n_transfers_submitted": 0
                    }
                submitter_reports[rule_id][rse_pair_id]["n_transfers_submitted"] += 1
    # Get SENSE mapping
    with Client(ADDRESS, authkey=AUTHKEY) as client:
        client.send(("SUBMITTER", submitter_reports))
        sense_map = client.recv()
    # Do SENSE link replacement
    for external_host in grouped_jobs:
        for job in grouped_jobs[external_host]:
            for file_data in job["files"]:
                ipv6_map = sense_map[rule_id][rse_pair_id]
                # Update source
                (src_name, src_url, src_id, src_retries) = file_data["sources"][0]
                src_hostname = __get_host_port(src_url)
                src_sense_url = src_url.replace(src_hostname, ipv6_map[src_name], 1)
                file_data["sources"][0] = (src_name, src_sense_url, src_id, src_retries)
                # Update destination
                dst_url = file_data["destinations"][0]
                dst_hostname = __get_host_port(dst_url)
                dst_sense_url = dst_url.replace(dst_hostname, ipv6_map[dst_name], 1)
                file_data["destinations"] = [dst_sense_url]

def __get_rse_pair_id(src_rse_name, dst_rse_name):
    return f"{src_rse_name}&{dst_rse_name}"

def __get_host_port(url):
    # Assumes the url is something like "protocol://hostname//path"
    # TODO: Need to make more universal for other url formats.
    return url.split("/")[2]
