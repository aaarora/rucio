from flask import Flask, request

app = Flask(__name__)

@app.route('/query')
def query():
    hostname = request.args.get('hostname')
    total_file_size = request.args.get('total_file_size')
    return '127.0.0.1'
