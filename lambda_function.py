import json
import boto3
import nltk
from nltk.sentiment import SentimentIntensityAnalyzer
from collections import defaultdict

# Download NLTK data (only if not already downloaded)
nltk.download('vader_lexicon', quiet=True)

# Initialize Sentiment Analyzer
sia = SentimentIntensityAnalyzer()

# DynamoDB tables
dynamodb = boto3.resource('dynamodb')
wishlist_table = dynamodb.Table('WishlistItem-dk4dwql2pvg4bf26dclmo2z3z4-dev')
cart_table = dynamodb.Table('CartItem-dk4dwql2pvg4bf26dclmo2z3z4-dev')
orders_table = dynamodb.Table('Order-dk4dwql2pvg4bf26dclmo2z3z4-dev')
review_table = dynamodb.Table('Review-dk4dwql2pvg4bf26dclmo2z3z4-dev')

# ---------- Sentiment Analysis ----------

def clean_text(text):
    return text.strip().lower()

def analyze_sentiment(text):
    cleaned = clean_text(text)
    score = sia.polarity_scores(cleaned)['compound']
    return score

def get_sentiment_scores():
    response = review_table.scan()
    items = response.get('Items', [])

    product_sentiments = defaultdict(list)
    for item in items:
        pid = item.get('productId')
        review = item.get('review', '')
        if pid and review:
            score = analyze_sentiment(review)
            product_sentiments[pid].append(score)

    avg_sentiment = {
        pid: sum(scores) / len(scores)
        for pid, scores in product_sentiments.items() if scores
    }
    return avg_sentiment

# ---------- Interaction Scoring ----------

def get_interaction_scores():
    scores = defaultdict(float)

    tables_with_weights = {
        'wishlist': (wishlist_table, 1.0),
        'cart': (cart_table, 1.5),
        'orders': (orders_table, 2.0)
    }

    for _, (table, weight) in tables_with_weights.items():
        response = table.scan()
        items = response.get('Items', [])
        for item in items:
            pid = item.get('productId')
            if pid:
                scores[pid] += weight

    return scores

# ---------- Combine Scores ----------

def combine_scores(interaction_scores, sentiment_scores):
    combined = defaultdict(float)

    for pid in interaction_scores:
        combined[pid] += interaction_scores[pid]
        if pid in sentiment_scores:
            combined[pid] += sentiment_scores[pid] * 2.0  # Boost sentiment

    for pid in sentiment_scores:
        if pid not in combined:
            combined[pid] += sentiment_scores[pid] * 2.0

    return combined

# ---------- Lambda Entry Point ----------

def lambda_handler(event=None, context=None):
    try:
        sentiment_scores = get_sentiment_scores()
        interaction_scores = get_interaction_scores()
        final_scores = combine_scores(interaction_scores, sentiment_scores)

        if not final_scores:
            return {
                'statusCode': 404,
                'body': json.dumps("No sufficient data for recommendations.")
            }

        # Lower threshold and return more products
        MIN_SCORE = 0.1
        sorted_scores = sorted(final_scores.items(), key=lambda x: x[1], reverse=True)
        top_products = [item for item in sorted_scores if item[1] >= MIN_SCORE][:20]

        return {
            'statusCode': 200,
            'body': json.dumps({
                "RecommendedProducts": [
                    {"productId": pid, "score": round(score, 2)} for pid, score in top_products
                ]
            }, indent=4)
        }

    except Exception as e:
        return {
            'statusCode': 500,
            'body': json.dumps(f"Error: {str(e)}")
        }

# ---------- For Local Testing ----------

if __name__ == "__main__":
    result = lambda_handler()
    print(result["body"])

# ---------- Flask API compatible function ----------

def get_recommendations():
    try:
        sentiment_scores = get_sentiment_scores()
        interaction_scores = get_interaction_scores()
        final_scores = combine_scores(interaction_scores, sentiment_scores)

        if not final_scores:
            return {
                "RecommendedProducts": [],
                "message": "No sufficient data for recommendations."
            }

        MIN_SCORE = 0.1
        sorted_scores = sorted(final_scores.items(), key=lambda x: x[1], reverse=True)
        top_products = [item for item in sorted_scores if item[1] >= MIN_SCORE][:20]

        return {
            "RecommendedProducts": [
                {"productId": pid, "score": round(score, 2)} for pid, score in top_products
            ]
        }

    except Exception as e:
        return {"error": str(e)}
