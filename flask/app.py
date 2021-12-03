import json
import os
from flask import Flask, request

class NONSENSE:
    """
    Name-Only Nonfunctional Software defined networking (SDN) for End-to-end Networked Science at the Exascale 
    """
    def __init__(self):
        self.dummy_link = "127.0.0.1"

    def allocate_links(self, rule_id, rse_pair_ids, total_byte_count, priority):
        return

    def get_links(self, rule_id, rse_pair_id):
        return self.dummy_link, self.dummy_link

    def update_links(self):
        return

    def free_links(self, rule_id, rse_pair_id):
        return

class Cache:
    def __init__(self, hardcopy_name="dmm.cache.json", clear_on_init=False):
        self.__cwd = os.path.dirname(os.path.abspath(__file__))
        self.__content = {}
        self.hardcopy = f"{self.__cwd}/{hardcopy_name}"
        if os.path.isfile(self.hardcopy):
            with open(self.hardcopy, "rw") as f:
                if clear_on_init:
                    json.dump({}, f)
                else:
                    self.__content.update(json.load(f))

    def __str__(self):
        return json.dumps(self.__content, indent=4)

    def __getitem__(self, key):
        return self.__content[key]

    def __setitem__(self, key, value):
        self.__content[key] = value
        self.__update_hardcopy()

    def keys(self):
        return self.__content.keys()

    def update(self, new_dict):
        self.__content.update(new_dict)
        self.__update_hardcopy()

    def pop(self, key):
        val = self.__content.pop(key)
        self.__update_hardcopy()
        return val
    
    def delete(self, key):
        self.pop(key)

    def __update_hardcopy(self):
        with open(self.hardcopy, "w") as f_out:
            json.dump(self.__content, f_out)

dmm_cache = Cache(clear_on_init=True)
sense = NONSENSE()

app = Flask(__name__)

@app.route("/cache", methods=["GET", "POST"])
def cache():
    if request.method == "POST":
        prepared_jobs = request.json
        for rule_id, job in prepared_jobs.items():
            rse_pair_ids = [t_id.split("&") for t_id in job["rse_pairs"].keys()]
            sense.allocate_links(
                rule_id,
                rse_pair_ids,
                job["total_byte_count"],
                job["priority"]
            )
            # Populate SENSE mapping
            sense_map = {}
            for rse_pair_id, transfer_data in job["rse_pairs"].items():
                # Get dummy SENSE links
                src_link, dst_link = sense.get_links(rule_id, rse_pair_id)
                # Update SENSE mapping
                sense_map[rse_pair_id] = {
                    transfer_data["source_rse_id"]: src_link,
                    transfer_data["dest_rse_id"]: dst_link,
                    "total_transfers": transfer_data["n_transfers"],
                    "finished_transfers": 0
                }
            # Save SENSE mapping
            prepared_jobs[rule_id]["sense_map"] = sense_map

        dmm_cache.update(prepared_jobs)
        return ("", 204)
    else:
        rule_id = request.args.get("rule_id")
        metadata_key = request.args.get("metadata_key", "")
        if metadata_key == "":
            return dmm_cache[rule_id]
        else:
            return dmm_cache[rule_id][metadata_key]

@app.route("/free", methods=["POST"])
def free():
    updated_jobs = request.json
    for rule_id, job in updated_jobs.items():
        sense_map = dmm_cache[rule_id]["sense_map"]
        for rse_pair_id, finished_transfers in job.items():
            sense_map[rse_pair_id]["finished_transfers"] += finished_transfers
            if sense_map[rse_pair_id]["finished_transfers"] == sense_map[rse_pair_id]["total_transfers"]:
                sense.free_links(rule_id, rse_pair_id)
                sense_map.pop(rse_pair_id)
        if sense_map == {}:
            dmm_cache.delete(rule_id)
        else:
            dmm_cache[rule_id]["sense_map"] = sense_map

    return ("", 204)
