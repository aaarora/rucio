import json
import os
from flask import Flask, request

class NONSENSE:
    """
    Name-Only Nonfunctional Software defined networking (SDN) for End-to-end Networked Science at the Exascale 
    """
    def __init__(self):
        self.dummy_link = "127.0.0.1"

    def allocate_links(self, priority, rse_pair_ids):
        return

    def get_links(self, priority, rse_pair_id):
        return self.dummy_link, self.dummy_link

    def update_links(self):
        return

    def free_links(self, priority, rse_pair_id):
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
nonsense = NONSENSE()

app = Flask(__name__)

@app.route("/sense", methods=["POST", "GET"])
def sense():
    if request.method == "POST":
        sense_maps = {}
        for priority, prepared_jobs in request.json.items():
            nonsense.allocate_links(
                priority,
                prepared_jobs.keys()
            )
            # Populate SENSE mapping
            sense_map = {}
            for rse_pair_id, transfer_data in prepared_jobs.items():
                # Get dummy SENSE links
                src_link, dst_link = nonsense.get_links(priority, rse_pair_id)
                # Update SENSE mapping
                sense_map[rse_pair_id] = {
                    transfer_data["source_rse_id"]: src_link,
                    transfer_data["dest_rse_id"]: dst_link,
                    "total_byte_count": transfer_data["total_byte_count"],
                    "total_transfers": transfer_data["total_transfers"],
                    "finished_transfers": 0
                }
            # Save SENSE mapping
            if priority in sense_maps.keys():
                sense_maps[priority].update(sense_map)
            else:
                sense_maps[priority] = sense_map

        dmm_cache.update(sense_maps)
        return ("", 204)
    elif request.method == "GET":
        priority = request.json.get("priority")
        rse_pair_id = request.json.get("rse_pair_id")
        return dmm_cache[priority][rse_pair_id]
    else:
        return ("", 404)

@app.route("/free", methods=["POST"])
def free():
    for priority, updated_jobs in request.json.items():
        sense_map = dmm_cache[priority]
        for rse_pair_id, finished_transfers in updated_jobs.items():
            sense_map[rse_pair_id]["finished_transfers"] += finished_transfers
            if sense_map[rse_pair_id]["finished_transfers"] == sense_map[rse_pair_id]["total_transfers"]:
                nonsense.free_links(priority, rse_pair_id)
                sense_map.pop(rse_pair_id)
        if sense_map == {}:
            dmm_cache.delete(priority)
        else:
            dmm_cache[priority] = sense_map

    return ("", 204)
