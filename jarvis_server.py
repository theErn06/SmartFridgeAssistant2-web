import os
import json
import re
import requests
import datetime
from flask import Flask, request, jsonify, make_response
from flask_cors import CORS
from datetime import datetime, timedelta

app = Flask(__name__)

# Disable automatic CORS to use our manual strict headers
# (This prevents double-header conflicts)
CORS(app, resources={r"/*": {"origins": "*"}})

# ================= STRICT MOBILE CORS FIX =================
@app.after_request
def after_request(response):
    # Mobile browsers hate wildcard '*' for Headers. We must be specific.
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
    return response
# ==========================================================

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
MEMORY_FILE = os.path.join(SCRIPT_DIR, "fridge2_5.json")
OLLAMA_URL = "http://localhost:11434/api/chat"
MODEL_NAME = "jarvis"

SHELF_LIFE_RULES = {
    "protein": 4, "seafood": 7, "dairy": 10, "vegetables": 7, 
    "fruits": 7, "grains": 14, "pantry": 365, "processed": 7, "non-food": 0
}

def convert_word_to_num(text):
    word_to_num = { "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10 }
    text = text.lower()
    for word, num in word_to_num.items():
        text = re.sub(r'\b' + word + r'\b', str(num), text)
    return text

def clean_item_name(name):
    name = name.lower().strip()
    name = re.sub(r'^\s*(?:pieces?|bags?|packs?|cartons?|bottles?|cans?|units?|cups?|kg?|g?|lbs?)\s+of\s+', '', name, flags=re.IGNORECASE)
    return name.strip()

def load_fridge():
    if not os.path.exists(MEMORY_FILE): return {}
    try:
        with open(MEMORY_FILE, "r") as f: return json.load(f)
    except: return {}

def save_fridge(fridge):
    with open(MEMORY_FILE, "w") as f: json.dump(fridge, f, indent=2)

def calculate_expiry(category):
    days = SHELF_LIFE_RULES.get(category.lower(), 7)
    if days == 0: return "N/A"
    return (datetime.now() + timedelta(days=days)).strftime("%Y/%m/%d")

def get_batch_status(expiry):
    if not expiry or expiry == "N/A": return "N/A"
    try:
        today = datetime.now().date()
        exp = datetime.strptime(expiry, "%Y/%m/%d").date()
        days_left = (exp - today).days
        if days_left < 0: return "Expired"
        elif days_left <= 2: return "Expired Soon"
        else: return "Good to Eat"
    except: return "N/A"

def update_fridge(item, delta, unit="pieces", category=None):
    item = clean_item_name(item)
    fridge = load_fridge()
    if item not in fridge:
        final_category = category if category else "general"
        fridge[item] = {"item_name": item, "unit": unit, "category": final_category, "batches": []}
    else:
        final_category = fridge[item].get("category", "general")
    entry = fridge[item]
    if delta > 0:
        new_expiry = calculate_expiry(final_category)
        merged = False
        for batch in entry["batches"]:
            if batch.get("expiry") == new_expiry:
                batch["qty"] += delta
                batch["status"] = get_batch_status(new_expiry)
                merged = True
                break
        if not merged:
            entry["batches"].append({"qty": delta, "expiry": new_expiry, "status": get_batch_status(new_expiry)})
    elif delta < 0:
        remove_qty = -delta
        entry["batches"].sort(key=lambda b: b["expiry"] if b["expiry"] != "N/A" else "9999/99/99")
        keep_batches = []
        for batch in entry["batches"]:
            if remove_qty > 0:
                if batch["qty"] > remove_qty:
                    batch["qty"] -= remove_qty
                    remove_qty = 0
                    keep_batches.append(batch)
                else:
                    remove_qty -= batch["qty"]
            else:
                keep_batches.append(batch)
        entry["batches"] = keep_batches
        if not entry["batches"]: fridge.pop(item, None)
    save_fridge(fridge)

def get_fridge_text():
    fridge = load_fridge()
    if not fridge: return "The fridge is empty."
    lines = []
    for item, data in fridge.items():
        total = sum(b.get("qty", 0) for b in data.get("batches", []))
        lines.append(f"{data['item_name']} | {total} {data['unit']}")
    return "; ".join(lines)

def get_item_count(item):
    item = clean_item_name(item)
    fridge = load_fridge()
    if item in fridge:
        total = sum(b.get("qty", 0) for b in fridge[item].get("batches", []))
        return f"You have {total} {fridge[item]['unit']} of {item}."
    return f"You don't have any {item}."

def parse_regex_fallback(text):
    text = text.lower()
    actions = []
    add_match = re.search(r"(add|buy|get|insert)\s+(\d+)\s+(.*)", text)
    if add_match:
        qty = int(add_match.group(2))
        item = clean_item_name(add_match.group(3).strip())
        if item.endswith("s"): item = item[:-1] 
        actions.append({"action": "add", "item": item, "qty": qty})
        return actions
    remove_match = re.search(r"(remove|eat|delete|take)\s+(\d+)\s+(.*)", text)
    if remove_match:
        qty = int(remove_match.group(2))
        item = clean_item_name(remove_match.group(3).strip())
        if item.endswith("s"): item = item[:-1]
        actions.append({"action": "remove", "item": item, "qty": qty})
        return actions
    return []

def ask_ollama(user_text, context):
    prompt = f"You are a JSON generator. Fridge: {context}. User: {user_text}. Return ONLY: [{{\"action\": \"add\"|\"remove\", \"item\": \"name\", \"qty\": number}}]"
    try:
        resp = requests.post(OLLAMA_URL, json={"model": MODEL_NAME, "messages": [{"role": "user", "content": prompt}]}, timeout=5)
        content = resp.json()["message"]["content"]
        match = re.search(r"(\[.*\])", content.replace("```json", "").replace("```", "").strip(), re.DOTALL)
        if match: return json.loads(match.group(1))
    except: pass
    return []

# ================= ENDPOINTS =================

@app.route('/', methods=['GET'])
def home():
    return jsonify({"status": "Online", "message": "Jarvis is ready."})

# Explicitly handle OPTIONS request
@app.route('/chat', methods=['OPTIONS'])
def handle_options():
    response = make_response()
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
    return response

@app.route('/chat', methods=['POST'])
def chat():
    try:
        data = request.json
        raw_text = data.get("message", "")
        print(f"WEB USER: {raw_text}")
        
        user_text = convert_word_to_num(raw_text)
        fridge_ctx = get_fridge_text()
        actions = ask_ollama(user_text, fridge_ctx)
        if not actions: actions = parse_regex_fallback(user_text)

        response_text = ""
        if not actions:
            if "list" in user_text.lower(): response_text = f"Inventory: {fridge_ctx}"
            else: response_text = "I didn't quite catch that."
        
        for a in actions:
            action = a.get("action")
            item = clean_item_name(a.get("item"))
            qty = a.get("count") or a.get("qty") or 1
            if action in ["add", "at"]:
                update_fridge(item, qty, category=None)
                response_text = f"Added {qty} {item}."
            elif action == "remove":
                update_fridge(item, -qty)
                response_text = f"Removed {qty} {item}."
            elif action == "lookup":
                response_text = get_item_count(item)
            elif action == "list":
                response_text = f"Inventory: {fridge_ctx}"

        return jsonify({"response": response_text})

    except Exception as e:
        print(f"ERROR: {e}")
        return jsonify({"response": "System error."}), 500

if __name__ == '__main__':
    # 0.0.0.0 is CRITICAL for mobile access
    app.run(host='0.0.0.0', port=5000)
