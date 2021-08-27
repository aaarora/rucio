"""
SENSE Optimizer Prototype
"""

import requests
import logging

def sense_optimizer(grouped_jobs):
    """
    Replace source RSE hostname with IPv6 corresponding to chosen SENSE link

    :param grouped_jobs:                Transfers grouped in bulk (see rucio.daemons.conveyor.common)                
    """
    cache = {}
    for external_host in grouped_jobs:
        total_file_size = _get_total_file_size(grouped_jobs)
        for job in grouped_jobs[external_host]:
            for job_file in job['files']:
                # update sources with relevant ipv6
                updated_sources = []
                for source in job_file['sources']:
                    source_rse_host = _get_hostname(source[1])
                    source_ = list(source)
                    source_[1] = source_[1].replace(source_rse_host, _resolve_ipv6(source_rse_host, total_file_size, cache), 1)
                    updated_sources.append(tuple(source_))
                job_file['sources'] = updated_sources

                # update destination with relevant ipv6
                for dest in job_file['destinations']:
                    dest_rse_host = _get_hostname(dest)
                    job_file['destinations'][0] = dest.replace(dest_rse_host, _resolve_ipv6(dest_rse_host, total_file_size, cache), 1)

# Inefficient. Can integrate this within rcuio.daemons.conveyor.common.bulk_group_transfer
def _get_total_file_size(grouped_jobs):
    total_file_size = 0
    for external_host in grouped_jobs:
        for job in grouped_jobs[external_host]:
            for job_file in job['files']:
                total_file_size += job_file['filesize']
    return total_file_size

#TODO add list of protocol prefixes
def _get_hostname(uri):
    return uri.split('//')[1].split(':')[0]

#TODO add pseudo DNS name server db
def _resolve_ipv6(hostname, total_file_size, cache):
    if hostname in cache:
       ipv6 = cache['hostname']
       logging.info('Found hostname in cached list... Replaced %s for IPv6 %s', hostname, ipv6)
       return ipv6
    ipv6 = requests.get(f'http://flask:5000/query?hostname={hostname}&total_file_size={total_file_size}').text
    cache.update({hostname:ipv6})
    logging.info('Replaced %s for IPv6 %s', hostname, ipv6) 
    return ipv6
