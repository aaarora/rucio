"""
SENSE Optimizer Prototype
"""

import requests
import logging

cache = {}

def sense_preparer(requests_with_sources, extra_metadata=["request_id", "name"]):
    """
    Parse RequestWithSources objects collected by the preparer daemon and communicate relevant info to DMM

    :param requests_with_sources:    Individual file transfers (see rucio.transfer.RequestWithSource)
    """
    # Collect requested transfers
    jobs = {}
    for req in requests_with_sources:
        print(req.attributes)
        rule_id = str(req.rule_id)
        # Collect metadata
        metadata = {
            "source_rse_ids": [src.rse.id for src in req.sources],
            "dest_rse_id": req.dest_rse.id,
            "byte_count": req.byte_count,
            "priority": 0 # FIXME: add actual priority
        }
        for k in extra_metadata:
            metadata[k] = str(req.__dict__[k])
        # Update transfer entry (sourted by rule ID)
        if rule_id not in jobs.keys():
            jobs[rule_id] = {"files": [], "total_byte_count": 0}
        jobs[rule_id]["files"].append(metadata)
        jobs[rule_id]["total_byte_count"] += req.byte_count

    # Communicate the collected information to DMM
    response = requests.post("http://flask:5000/prep", json=jobs)

def sense_optimizer(grouped_jobs):
    """
    Replace source RSE hostname with IPv6 corresponding to chosen SENSE link

    :param grouped_jobs:             Transfers grouped in bulk (see rucio.daemons.conveyor.common)
    """
    for external_host in grouped_jobs:
        # total_file_size = _get_total_file_size(grouped_jobs)
        for job in grouped_jobs[external_host]:
            for file_data in job["files"]:
                # Update source and destination with relevant ipv6
                rule_id = file_data["rule_id"]
                if rule_id not in cache.keys():
                    __update_cache_with_sense_optimization(rule_id)
                sense_ipv6_map = cache[rule_id]
                # Update sources
                # TODO: rather than do this loop, find the final source! Any way to corroborate the singular
                #       rse id found in 'metadata' with one of many possible tuples in 'sources'? i.e. is it
                #       this the actual source used for the transfer?
                for i, (src_name, src_url, src_id, src_retries) in enumerate(file_data["sources"]):
                    src_host = __get_hostname(src_url)
                    src_sense_url = src_url.replace(src_host, cache[src_id], 1)
                    file_data["sources"][i] = (src_name, src_sense_url, src_id, src_retries)
                # Update destination
                dst_id = file_data["metadata"]["dest_rse_id"]
                dst_url = file_data["destinations"][0]
                dst_host = __get_hostname(dst_url)
                sense_url = url.replace(dst_host, cache[dst_id], 1)
                file_data["destinations"] = [sense_url]

def free_links(rule_id):
    requests.post(f"http://flask:5000/free?rule_id={rule_id}")

# Assuming the url is something like "root://hostname//path". Need to make more universal for other url formats.
def __get_hostname(uri):
    return uri.split("//")[1].split(":")[0]

# replacing sense with psudo dns server in flask (image in main dir)
# def _update_cache_with_sense_optimization(file_data, total_file_size, cache):
def __update_cache_with_sense_optimization(rule_id):
    global cache
    response = requests.get(f"http://flask:5000/sense?rule_id={rule_id}").json()
    cache.update({rule_id: response})
