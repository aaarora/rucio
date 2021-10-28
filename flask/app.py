import json
import os
from flask import Flask, request

class NONSENSE:
    """
    Name-Only Nonfunctional Software defined networking (SDN) for End-to-end Networked Science at the Exascale 
    """
    def __init__(self):
        self.dummy_link = "127.0.0.1"

    def get_links(self, rule_id, src_ids, dst_id, total_byte_count, priority):
        return [self.dummy_link for _ in src_ids], self.dummy_link

    def update_links(self):
        return

    def free_links(self, rse_id):
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
        jobs = request.json
        for rule_id, job in jobs.items():
            jobs[rule_id]["sense_ipv6_map"] = {}
            for file_data in job["files"]:
                # Dummy ipv6 allocation
                src_links, dst_link = sense.get_links(
                    rule_id,
                    file_data["source_rse_ids"],
                    file_data["dest_rse_id"],
                    job["total_byte_count"],
                    job["priority"]
                )
                jobs[rule_id]["sense_ipv6_map"].update(
                    dict(zip(file_data["source_rse_ids"], src_links))
                )
                jobs[rule_id]["sense_ipv6_map"][file_data["dest_rse_id"]] = dst_link

        dmm_cache.update(jobs)
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
    rule_id = request.args.get("rule_id")
    if rule_id in dmm_cache.keys():
        sense.free_links(rule_id)
        dmm_cache.delete(rule_id)
    return ("", 204)
