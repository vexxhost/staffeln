from flask import Flask
from flask import jsonify
from flask import request


app = Flask(__name__)


@app.route('/')
def hello_world():
    return 'This is my first API call!'


@app.route('/post', methods=["POST"])
def testpost():
    input_json = request.get_json(force=True)
    dictToReturn = {'text': input_json['text']}
    return jsonify(dictToReturn)

def run(host, port, ssl_context):
    app.run(host=host, port=port, ssl_context=ssl_context)
