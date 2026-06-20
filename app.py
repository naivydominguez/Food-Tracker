import base64
import csv
import os
import re
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, flash, session
from openai import OpenAI

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dev-secret-key')

UPLOAD_FOLDER = 'uploads'
LOG_FILE = 'meal_log.csv'
DAILY_GOAL = 2000

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

PROMPT = """Analyze this food image and respond in exactly this format:

FOOD IDENTIFIED: [name of the food]

CALORIES:
- Total estimate: [X] calories per serving
- Serving size: [estimated serving size]
- Breakdown (if multiple items): [item: X cal, item: X cal, ...]

NUTRITION:
- Protein: [X]g
- Carbs: [X]g
- Fat: [X]g
- Fiber: [X]g
- Sodium: [X]mg

HEALTH INSIGHTS:
[2-3 sentences about this meal — is it high in sodium, good for muscle recovery, heavy on saturated fat, etc.]

HEALTHIER SWAPS:
- [Swap 1 with estimated calorie savings]
- [Swap 2 with estimated calorie savings]
- [Swap 3 with estimated calorie savings]"""


def analyze_image(image_path):
    client = OpenAI()
    ext = os.path.splitext(image_path)[1].lower()
    mime = "image/jpeg" if ext in ('.jpg', '.jpeg') else "image/png"
    with open(image_path, "rb") as f:
        image_data = base64.b64encode(f.read()).decode("utf-8")
    response = client.responses.create(
        model="gpt-5.5",
        input=[{
            "role": "user",
            "content": [
                {"type": "input_image", "image_url": f"data:{mime};base64,{image_data}"},
                {"type": "input_text", "text": PROMPT}
            ]
        }]
    )
    return response.output_text


def parse_analysis(text):
    food_match = re.search(r'FOOD IDENTIFIED:\s*(.+)', text)
    cal_match = re.search(r'Total estimate:\s*(\d+)', text)
    food_name = food_match.group(1).strip() if food_match else "Unknown"
    calories = int(cal_match.group(1)) if cal_match else 0
    return food_name, calories


def log_meal(food_name, calories):
    file_exists = os.path.exists(LOG_FILE)
    with open(LOG_FILE, 'a', newline='') as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(['timestamp', 'food', 'calories'])
        writer.writerow([datetime.now().isoformat(), food_name, calories])


def get_today_log():
    if not os.path.exists(LOG_FILE):
        return []
    today = datetime.now().date().isoformat()
    entries = []
    with open(LOG_FILE, newline='') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row['timestamp'].startswith(today):
                entries.append(row)
    return entries

@app.route('/delete', methods=['POST'])
def delete_meal():
    timestamp = request.form["timestamp"]

    rows = []

    with open(LOG_FILE, newline='') as f:
        reader = csv.DictReader(f)

        for row in reader:
            if row["timestamp"] != timestamp:
                rows.append(row)

    with open(LOG_FILE, "w", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["timestamp", "food", "calories"]
        )
        writer.writeheader()
        writer.writerows(rows)

    return redirect(url_for("index"))



## simple login method. No password needed unless we deploy. 
@app.route('/login', methods=['POST'])
def login():
    username = request.form['username'].strip().lower() 
    session['user'] = username

    logged_file = f'logs/{username}.csv'

    if not os.path.exists(logged_file): # even if a user doesnt exist (meaning the file is not stored in the 'logs' folder) we will create one
        with open(logged_file, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['timestamp', 'food', 'calories', 'protein', 'carbs', 'fat', 'fiber']) # what the csv file stores for each person
    return redirect(url_for('index')) # once user is logged in, we redirect them to the main page


## login page display
@app.route('/login')
def login_page():
    return render_template('login.html')


@app.route('/')
def index():
    if 'user' not in session:
        return redirect(url_for('login_page'))  # redirects user to log in if they dont exist yet in file
    entries = get_today_log()
    total = sum(int(e['calories']) for e in entries)
    return render_template('index.html', entries=entries, total=total, goal=DAILY_GOAL)

## connecting the different tabs
@app.route('/calendar')
def calendar():
    return render_template('calendar.html')

@app.route('/history')
def history():
    return render_template('history.html')

@app.route('/stats')
def stats():
    return render_template('stats.html')

@app.route('/scan', methods=['POST'])
def scan():
    if 'photo' not in request.files or request.files['photo'].filename == '':
        flash('Please select a photo.')
        return redirect(url_for('index'))

    file = request.files['photo']
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in ('.jpg', '.jpeg', '.png'):
        flash('Only JPG and PNG files are supported.')
        return redirect(url_for('index'))

    path = os.path.join(UPLOAD_FOLDER, 'temp' + ext)
    file.save(path)

    try:
        analysis = analyze_image(path)
        food_name, calories = parse_analysis(analysis)
        log_meal(food_name, calories)
    except Exception as e:
        flash(f'Analysis failed: {e}')
        return redirect(url_for('index'))
    finally:
        if os.path.exists(path):
            os.remove(path)

    entries = get_today_log()
    total = sum(int(e['calories']) for e in entries)
    return render_template('index.html', entries=entries, total=total, goal=DAILY_GOAL,
                           analysis=analysis, food_name=food_name, calories=calories)


if __name__ == '__main__':
    app.run(debug=True)
