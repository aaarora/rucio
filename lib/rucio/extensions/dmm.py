"""
SENSE Optimizer Prototype
"""

import requests
import logging

cache = {}

def sense_preparer(
    requests_with_sources, 
    metadata_keys=["request_id", "byte_count", "name", "sources", "dest_rse"]
):
    # Collect requested transfers
    jobs = {}
    for req in requests_with_sources:
        rule_id = str(req.rule_id)
        metadata = {k: str(req.__dict__[k]) for k in metadata_keys}
        # Initialize new rule ID entry
        if rule_id not in jobs.keys():
            jobs[rule_id] = {"files": [], "total_byte_count": 0}
        # Append to rule ID entry
        jobs[rule_id]["files"].append(metadata)
        jobs[rule_id]["total_byte_count"] += req.byte_count

    # Communicate transfer sizes to DMM
    for rule_id, rule_data in jobs.items():
        response = requests.post("http://flask:5000/prep", json=rule_data)

def sense_optimizer(grouped_jobs):
    """
    Replace source RSE hostname with IPv6 corresponding to chosen SENSE link

    :param grouped_jobs:                Transfers grouped in bulk (see rucio.daemons.conveyor.common)                
    """
    for external_host in grouped_jobs:
        total_file_size = _get_total_file_size(grouped_jobs)
        for job in grouped_jobs[external_host]:
            for job_file in job["files"]:
                # update source and destination with relevant ipv6
                # _update_cache_with_sense_optimization(job_file, total_file_size=total_file_size, cache=cache)
                _update_cache_with_sense_optimization(job_file["rule_id"])
                updated_sources = []
                for source in job_file["sources"]:
                    source_rse_host = _get_hostname(source[1])
                    source_ = list(source)
                    source_[1] = source_[1].replace(source_rse_host, cache[source_rse_host], 1)
                    updated_sources.append(tuple(source_))
                job_file["sources"] = updated_sources

                for dest in job_file["destinations"]:
                    dest_rse_host = _get_hostname(dest)
                    job_file["destinations"][0] = dest.replace(dest_rse_host, cache[dest_rse_host], 1)

def free_links(rule_id):
    requests.post(f"http://flask:5000/free?rule_id={rule_id}")

# Inefficient. Can integrate this within rcuio.daemons.conveyor.common.bulk_group_transfer
def _get_total_file_size(grouped_jobs):
    total_file_size = 0
    for external_host in grouped_jobs:
        for job in grouped_jobs[external_host]:
            for job_file in job["files"]:
                total_file_size += job_file["filesize"]
    return total_file_size

# Assuming the url is something like "root://hostname//path". Need to make more universal for other url formats.
def _get_hostname(uri):
    return uri.split("//")[1].split(":")[0]

# replacing sense with psudo dns server in flask (image in main dir)
# def _update_cache_with_sense_optimization(job_file, total_file_size, cache):
def _update_cache_with_sense_optimization(rule_id):
    global cache
    # hostnames = []
    # updated_sources = []
    # for source in job_file["sources"]:
    #     source_rse_host = _get_hostname(source[1])
    #     hostnames.append(source_rse_host)
    # dest_rse_host = _get_hostname(job_file["destinations"][0])
    # hostnames.append(dest_rse_host)
    # # remove duplicates
    # hostnames = list(set(hostnames))
    # for host in hostnames:
    #     if host in cache:
    #         hostnames.remove(host)
    # hostnames_comma_seperated = ",".join(hostnames)
    # ipv6 = requests.get(f"http://flask:5000/sense?hostnames={hostnames_comma_seperated}&total_file_size={total_file_size}&rule_id={job_file["rule_id"]}").text.split(",")
    response = requests.get(f"http://flask:5000/sense?rule_id={rule_id}")
    dest_ipv6s = response.text.split(",")
    cache.update(dict(zip(hostnames, ipv6)))
