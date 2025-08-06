from flask import Flask, render_template, jsonify
import json
import os

app = Flask(__name__)

@app.route('/')
def index():
    return "TextEmpire Map Server is running!"

@app.route('/map_webapp.html')
def map_webapp():
    with open('map_webapp.html', 'r', encoding='utf-8') as f:
        return f.read()

@app.route('/api/countries')
def get_countries():
    # در واقعیت این داده‌ها از دیتابیس ربات دریافت می‌شود
    countries = [
        {"name": "ایران", "lat": 32.4279, "lng": 53.6880, "user": "712413375726", "relation": 0},
        {"name": "فرانسه", "lat": 46.2276, "lng": 2.2137, "user": "123456789", "relation": 60},
        {"name": "آلمان", "lat": 51.1657, "lng": 10.4515, "user": "987654321", "relation": -30},
        {"name": "برزیل", "lat": -14.2350, "lng": -51.9253, "user": "555666777", "relation": 20}
    ]
    return jsonify(countries)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False) 