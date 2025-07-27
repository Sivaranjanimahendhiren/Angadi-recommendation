from flask import Flask, jsonify
from flask_cors import CORS
from lambda_function import get_recommendations  # should fetch live data from DynamoDB

app = Flask(__name__)
CORS(app)

@app.route("/", methods=["GET"])
def home():
    return "✅ Flask API running. Visit /recommend for live product recommendations from DynamoDB."

@app.route("/recommend", methods=["GET"])
def recommend():
    try:
        # Always get fresh recommendations from DynamoDB
        recommendations = get_recommendations()
        return jsonify(recommendations)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(port=5001, debug=True)
