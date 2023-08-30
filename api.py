from flask import Flask, request, jsonify

app = Flask(__name__)

#For Flask so don't delete
if __name__ == '__main__':
    app.run(debug=True)