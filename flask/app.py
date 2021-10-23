import json
import os
from flask import Flask, request

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
    cache.update(request.json)
    return

@app.route("/sense")
def sense():
    rule_data = cache[request.args.get("rule_id")]
    total_byte_count = rule_Data["total_byte_count"]
    src_rses, dest_rses = [], []
    for f in rule_data["files"]:
        dest_rses.append(f["dest_rse"])
        src_rses += f["sources"]
    # TODO: replace the dummy code below with some smarter prototype ipv6 allocation
    # Dummy ipv6 replacement
    hostnames = src_rses + dest_rses
    return ",".join(["127.0.0.1" for host in hostnames.split(",")]) 

@app.route("/free")
def free():
    # TODO: add code to free allocated ips when recieve message of successful / failed transfer
    try:
        cache.delete(request.args.get("rule_id"))
    except KeyError as e:
        # TODO: add some kind of responsible error handling here
        return
    return
