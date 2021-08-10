from flask import Flask

app = Flask(__name__)

@app.route('/<path:path>')
def hello(path):
    return '127.0.0.1'
