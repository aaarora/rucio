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

    for external_host in grouped_jobs:
        for job in grouped_jobs[external_host]:
            for jfile in job['files']:
                updated_sources = []
                # update sources with relevant ipv6
                for source in jfile['sources']:
                    source_rse_host = _get_hostname(source[1])
                    source_ = list(source)
                    source_[1] = source_[1].replace(source_rse_host, _resolve_ipv6(source_rse_host), 1)
                    updated_sources.append(tuple(source_))
                jfile['sources'] = updated_sources

                # update destination with relevant ipv6
                updated_destinations = []
                for dest in jfile['destinations']:
                    dest_rse_host = _get_hostname(dest[1])
                    dest_ = list(dest)
                    dest_[1] = dest_[1].replace(dest_rse_host, _resolve_ipv6(dest_rse_host), 1)
                    updated_destination.append(tuple(dest_))
                jfile['destinations'] = updated_destinations


#TODO add list of protocol prefixes
def _get_hostname(source_uri):
    return source_uri.split('//')[1].split(':')[0]

#TODO add pseudo DNS name server db
def _resolve_ipv6(hostname):
    ipv6 = requests.get(f'http://flask:5000/{hostname}').text
    logging.info('Replaced %s for IPv6 %s', hostname, ipv6) 
    return ipv6
