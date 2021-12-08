import json
import os
from flask import Flask, request

class NONSENSE:
    """
    Name-Only Nonfunctional Software defined networking (SDN) for End-to-end Networked Science at the Exascale 
    """
    def __init__(self):
        self.dummy_link = "127.0.0.1"

    def allocate_links(self, *args, **kwargs):
        return

    def get_links(self, *args, **kwargs):
        return self.dummy_link, self.dummy_link

    def update_links(self):
        return

    def free_links(self, *args, **kwargs):
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

    def keys(self):
        return self.__content.keys()

    def update(self, new_dict):
        self.__content.update(new_dict)

    def pop(self, key):
        val = self.__content.pop(key)
        return val
    
    def delete(self, key):
        self.pop(key)

    def write(self):
        with open(self.hardcopy, "w") as f_out:
            json.dump(self.__content, f_out)

dmm_cache = Cache(clear_on_init=True)
nonsense = NONSENSE()

app = Flask(__name__)

@app.route("/sense", methods=["POST", "GET"])
def sense():
    if request.method == "POST":
        to_cache = {}
        for priority, prepared_jobs in request.json.items():
            to_cache[priority] = {}
            for rse_pair_id, transfer_data in prepared_jobs.items():
                additional_transfer_data = {
                    "transferred_bytes": 0,
                    "waiting_transfers": transfer_data["total_transfers"],
                    "active_transfers": 0,
                    "finished_transfers": 0
                }
                transfer_data.update(additional_transfer_data)
                to_cache[priority][rse_pair_id] = transfer_data

        dmm_cache.update(to_cache)
        dmm_cache.write()
        return ("", 204)
    elif request.method == "GET":
        priority = request.json.get("priority")
        rse_pair_id = request.json.get("rse_pair_id")
        submitted_transfers = request.json.get("submitted_transfers")
        # Fetch transfer metadata
        transfer_data = dmm_cache[priority][rse_pair_id]
        # Update counters
        transfer_data["waiting_transfers"] -= submitted_transfers
        transfer_data["active_transfers"] += submitted_transfers
        # Get dummy SENSE links
        nonsense.allocate_links(transfer_data)
        src_link, dst_link = nonsense.get_links(priority, rse_pair_id)
        transfer_data["sense_map"] = {
            transfer_data["source_rse_id"]: src_link,
            transfer_data["dest_rse_id"]: dst_link,
        }

        dmm_cache[priority][rse_pair_id].update(transfer_data)
        dmm_cache.write()
        return transfer_data["sense_map"]
    else:
        return ("", 404)

@app.route("/free", methods=["POST"])
def free():
    for priority, updated_jobs in request.json.items():
        active_jobs = dmm_cache[priority]
        for rse_pair_id, updated_data in updated_jobs.items():
            transfer_data = active_jobs[rse_pair_id]
            transfer_data["transferred_bytes"] += updated_data["transferred_bytes"]
            transfer_data["active_transfers"] -= updated_data["finished_transfers"]
            transfer_data["finished_transfers"] += updated_data["finished_transfers"]
            if transfer_data["finished_transfers"] == transfer_data["total_transfers"]:
                nonsense.free_links(priority, rse_pair_id)
                active_jobs.pop(rse_pair_id)
        if active_jobs == {}:
            dmm_cache.delete(priority)
            dmm_cache.write()
        else:
            dmm_cache[priority] = active_jobs
            dmm_cache.write()

    return ("", 204)
