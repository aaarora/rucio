import json
import os
from flask import Flask, request, jsonify

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

cache = Cache(clear_on_init=True)

app = Flask(__name__)

@app.route("/prep", methods=["GET", "POST"])
def prep():
    jobs = request.json
    print(jobs)
    for rule_id, job in jobs.items():
        total_byte_count = job["total_byte_count"]
        # Dummy ipv6 allocation
        jobs[rule_id]["sense_ipv6_map"] = {}
        for file_data in job["files"]:
            jobs[rule_id]["sense_ipv6_map"].update({s: "127.0.0.1" for s in file_data["source_rse_ids"]})
            jobs[rule_id]["sense_ipv6_map"][file_data["dest_rse_id"]] = "127.0.0.1"

    cache.update(jobs)
    return ("", 204)

@app.route("/sense")
def sense():
    return cache[request.args.get("rule_id")]["sense_ipv6_map"]

@app.route("/free")
def free():
    # TODO: add code to free allocated ips when recieve message of successful / failed transfer
    # TODO: add error handling for key not in cache; currently does nothing if key not in cache
    rule_id = request.args.get("rule_id")
    if rule_id in cache.keys():
        cache.delete(rule_id)
    return ("", 204)
