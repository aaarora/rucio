from flask import Flask, request

app = Flask(__name__)

@app.route('/sense')
def sense():
    hostnames = request.args.get('hostnames')
    total_file_size = request.args.get('total_file_size')
    rule_id = request.args.get('rule_id')
    # <store rule_id and ipv6, block allocated ips>
    return ",".join(['127.0.0.1' for host in hostnames.split(',')]) 

@app.route('/free')
def free()
    # free allocated ips when recieve message of successful / failed transfer
    pass

    
