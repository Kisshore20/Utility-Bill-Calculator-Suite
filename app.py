from flask import Flask, request, jsonify, render_template, redirect, url_for, session, flash
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash
from itsdangerous import URLSafeTimedSerializer, SignatureExpired, BadSignature

# Optional OAuth support (authlib may not be installed in all environments)
try:
    from authlib.integrations.flask_client import OAuth
    _HAS_AUTHLIB = True
except Exception:
    OAuth = None
    _HAS_AUTHLIB = False
import json, sqlite3, os
from datetime import datetime, timedelta
from functools import wraps

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "utility-suite-secret-2025")
CORS(app)

# ─── Google OAuth Config ────────────────────────────────────────────────────────
app.config['GOOGLE_CLIENT_ID']     = os.environ.get("GOOGLE_CLIENT_ID", "YOUR_GOOGLE_CLIENT_ID")
app.config['GOOGLE_CLIENT_SECRET'] = os.environ.get("GOOGLE_CLIENT_SECRET", "YOUR_GOOGLE_CLIENT_SECRET")

# Initialize OAuth only if authlib is available; otherwise disable OAuth routes gracefully
if _HAS_AUTHLIB and OAuth is not None:
    oauth = OAuth(app)
    google = oauth.register(
        name='google',
        client_id=app.config['GOOGLE_CLIENT_ID'],
        client_secret=app.config['GOOGLE_CLIENT_SECRET'],
        server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
        client_kwargs={'scope': 'openid email profile'},
    )
else:
    oauth = None
    google = None

# ─── Token serializer for password reset ───────────────────────────────────────
serializer = URLSafeTimedSerializer(app.secret_key)

# ─── Database Setup ─────────────────────────────────────────────────────────────
def get_db():
    conn = sqlite3.connect('history.db')
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    c = conn.cursor()

    # History table
    c.execute('''CREATE TABLE IF NOT EXISTS history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        bill_type TEXT NOT NULL,
        amount REAL NOT NULL,
        details TEXT NOT NULL,
        user_id INTEGER,
        status TEXT DEFAULT 'UNPAID',
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
    )''')

    # Users table
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password TEXT,
        role TEXT DEFAULT 'user',
        google_id TEXT,
        reset_token TEXT,
        last_login DATETIME,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )''')

    # Rate overrides table — admin can edit slabs here
    c.execute('''CREATE TABLE IF NOT EXISTS rate_overrides (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        bill_type TEXT NOT NULL,
        key_name TEXT NOT NULL,
        value TEXT NOT NULL,
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(bill_type, key_name)
    )''')

    # Seed default admin account (admin@utility.com / Admin@123)
    admin_exists = c.execute("SELECT id FROM users WHERE email='admin@utility.com'").fetchone()
    if not admin_exists:
        c.execute("INSERT INTO users (name, email, password, role) VALUES (?, ?, ?, ?)",
                  ("Admin", "admin@utility.com", generate_password_hash("Admin@123"), "admin"))

    conn.commit()
    conn.close()

init_db()

# Migrate schema if running against an older database
conn = get_db()
columns = [c[1] for c in conn.execute("PRAGMA table_info(users)").fetchall()]
conn.close()
if 'last_login' not in columns:
    conn = get_db()
    conn.execute("ALTER TABLE users ADD COLUMN last_login DATETIME")
    conn.commit()
    conn.close()

conn = get_db()
history_columns = [c[1] for c in conn.execute("PRAGMA table_info(history)").fetchall()]
conn.close()
if 'user_id' not in history_columns:
    conn = get_db()
    conn.execute("ALTER TABLE history ADD COLUMN user_id INTEGER")
    conn.commit()
    conn.close()
if 'status' not in history_columns:
    conn = get_db()
    conn.execute("ALTER TABLE history ADD COLUMN status TEXT DEFAULT 'UNPAID'")
    conn.commit()
    conn.close()

# ─── Rate Helpers ────────────────────────────────────────────────────────────────
def get_override(bill_type, key_name, default):
    conn = get_db()
    row = conn.execute(
        "SELECT value FROM rate_overrides WHERE bill_type=? AND key_name=?",
        (bill_type, key_name)
    ).fetchone()
    conn.close()
    if row:
        try: return json.loads(row['value'])
        except: return row['value']
    return default

def set_override(bill_type, key_name, value):
    conn = get_db()
    conn.execute('''INSERT INTO rate_overrides (bill_type, key_name, value, updated_at)
                    VALUES (?, ?, ?, ?)
                    ON CONFLICT(bill_type, key_name) DO UPDATE SET value=excluded.value, updated_at=excluded.updated_at''',
                 (bill_type, key_name, json.dumps(value), datetime.now()))
    conn.commit()
    conn.close()

# ─── Rate tables used by both calculator and admin ─────────────────────────────────
ELECTRICITY_RATE_TABLES = {
    "Tamil Nadu": {
        "domestic": [
            (100, 0), (200, 1.50), (300, 3.00), (400, 4.00), (500, 5.00), (float('inf'), 6.00)
        ]
    },
    "Karnataka":      {"domestic": [(30,3.15),(100,5.45),(200,6.00),(500,7.10),(float('inf'),7.85)]},
    "Maharashtra":    {"domestic": [(100,3.46),(300,7.05),(500,8.50),(float('inf'),10.00)]},
    "Delhi":          {"domestic": [(200,3.00),(400,4.50),(800,6.50),(1200,7.00),(float('inf'),8.00)]},
    "Uttar Pradesh":  {"domestic": [(100,3.35),(200,5.50),(300,6.00),(500,6.50),(float('inf'),7.00)]},
    "Gujarat":        {"domestic": [(50,3.20),(100,3.95),(200,4.80),(400,5.90),(float('inf'),7.30)]},
    "Rajasthan":      {"domestic": [(100,3.00),(200,5.00),(300,6.20),(500,6.80),(float('inf'),7.95)]},
    "Punjab":         {"domestic": [(100,4.10),(300,5.50),(500,6.50),(float('inf'),7.50)]},
    "Haryana":        {"domestic": [(50,2.20),(100,4.50),(250,5.25),(500,6.50),(float('inf'),7.10)]},
    "Bihar":          {"domestic": [(100,5.25),(200,5.75),(300,6.50),(500,7.25),(float('inf'),8.00)]},
    "West Bengal":    {"domestic": [(100,5.00),(200,5.50),(300,6.00),(500,6.80),(float('inf'),7.80)]},
    "Assam":          {"domestic": [(60,1.50),(120,3.50),(240,5.00),(500,6.50),(float('inf'),7.50)]},
    "Telangana":      {"domestic": [(100,2.00),(200,3.50),(300,5.00),(400,7.00),(float('inf'),8.00)]},
    "Madhya Pradesh": {"domestic": [(30,3.35),(100,4.80),(200,5.95),(400,7.00),(float('inf'),7.90)]},
    "Chhattisgarh":   {"domestic": [(100,4.10),(200,4.80),(300,5.60),(500,6.20),(float('inf'),6.50)]},
    "Jharkhand":      {"domestic": [(100,3.25),(200,4.00),(300,5.20),(500,6.00),(float('inf'),6.75)]},
    "Odisha":         {"domestic": [(50,3.00),(200,4.50),(400,5.50),(float('inf'),5.75)]},
    "Kerala":         {"domestic": [(40,2.90),(80,3.50),(140,4.90),(180,6.90),(250,7.45),(float('inf'),8.00)]},
    "Default":        {"domestic": [(100,3.00),(300,5.00),(500,7.00),(float('inf'),9.00)]},
}

def _normalize_slab(raw):
    normalized = []
    for item in raw:
        if isinstance(item, dict):
            limit = item.get('limit')
            rate = item.get('rate')
        elif isinstance(item, (list, tuple)) and len(item) >= 2:
            limit, rate = item[0], item[1]
        else:
            continue
        if isinstance(limit, str) and limit in ('∞', 'inf', 'INF'):
            limit = float('inf')
        elif limit is None:
            limit = float('inf')
        try:
            limit = float(limit)
        except Exception:
            limit = float('inf')
        try:
            rate = float(rate)
        except Exception:
            continue
        normalized.append((limit, rate))
    return normalized


def _serialize_slab(slab_list):
    return [
        {"limit": "∞" if limit == float('inf') else (int(limit) if limit == int(limit) else limit), "rate": rate}
        for limit, rate in slab_list
    ]


def _get_electricity_slabs(state, consumer_type):
    override = get_override('electricity_slabs', f'{state}::{consumer_type}', None)
    if override is not None:
        try:
            return _normalize_slab(override)
        except Exception:
            pass
    default = ELECTRICITY_RATE_TABLES.get(state, ELECTRICITY_RATE_TABLES['Default']).get(
        consumer_type, ELECTRICITY_RATE_TABLES['Default']['domestic']
    )
    return _normalize_slab(default)


# ─── Auth Decorators ─────────────────────────────────────────────────────────────
def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login_page'))
        return f(*args, **kwargs)
    return decorated

def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login_page'))
        if session.get('role') != 'admin':
            return jsonify({"error": "Admin access required"}), 403
        return f(*args, **kwargs)
    return decorated

# ═══════════════════════════════════════════════════════════════════════════════
#  PAGE ROUTES
# ═══════════════════════════════════════════════════════════════════════════════
@app.route("/")
def home():
    return render_template("home.html")

@app.route("/login")
def login_page():
    if 'user_id' in session:
        return redirect(url_for('index'))
    return render_template("login.html")

@app.route("/calculator")
@login_required
def index():
    return render_template("index.html")

@app.route("/admin")
@admin_required
def admin_panel():
    return render_template("admin.html")

# ═══════════════════════════════════════════════════════════════════════════════
#  AUTH ROUTES
# ═══════════════════════════════════════════════════════════════════════════════
@app.route("/api/auth/register", methods=["POST"])
def register():
    data = request.json
    name     = data.get("name", "").strip()
    email    = data.get("email", "").strip().lower()
    password = data.get("password", "")

    if not all([name, email, password]):
        return jsonify({"error": "All fields required"}), 400
    if len(password) < 6:
        return jsonify({"error": "Password must be at least 6 characters"}), 400

    conn = get_db()
    existing = conn.execute("SELECT id FROM users WHERE email=?", (email,)).fetchone()
    if existing:
        conn.close()
        return jsonify({"error": "Email already registered"}), 409

    conn.execute("INSERT INTO users (name, email, password) VALUES (?, ?, ?)",
                 (name, email, generate_password_hash(password)))
    conn.commit()
    user = conn.execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()
    conn.close()

    session['user_id'] = user['id']
    session['name']    = user['name']
    session['role']    = user['role']
    return jsonify({"status": "ok", "name": user['name'], "role": user['role']}), 201


@app.route("/api/auth/login", methods=["POST"])
def login():
    data     = request.json
    email    = data.get("email", "").strip().lower()
    password = data.get("password", "")

    conn = get_db()
    user = conn.execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()
    conn.close()

    if not user or not user['password'] or not check_password_hash(user['password'], password):
        return jsonify({"error": "Invalid email or password"}), 401

    session['user_id'] = user['id']
    session['name']    = user['name']
    session['role']    = user['role']
    conn = get_db()
    conn.execute("UPDATE users SET last_login=? WHERE id=?", (datetime.now(), user['id']))
    conn.commit()
    conn.close()
    return jsonify({"status": "ok", "name": user['name'], "role": user['role']})


@app.route("/api/auth/logout")
@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for('login_page'))


@app.route("/api/auth/me")
def me():
    if 'user_id' not in session:
        return jsonify({"logged_in": False})
    return jsonify({"logged_in": True, "name": session.get('name'), "role": session.get('role')})


# ─── Google OAuth ────────────────────────────────────────────────────────────
@app.route("/auth/google")
def google_login():
    if not google:
        flash('Google OAuth is not available on this server.')
        return redirect(url_for('login_page'))
    redirect_uri = url_for('google_callback', _external=True)
    return google.authorize_redirect(redirect_uri)

@app.route("/auth/google/callback")
def google_callback():
    try:
        if not google:
            return redirect(url_for('login_page') + '?error=oauth_unavailable')
        token = google.authorize_access_token()
        user_info = token.get('userinfo')
        if not user_info:
            import requests as rq
            user_info = rq.get('https://www.googleapis.com/oauth2/v3/userinfo',
                                headers={'Authorization': f"Bearer {token['access_token']}"}).json()

        email     = user_info['email'].lower()
        name      = user_info.get('name', email.split('@')[0])
        google_id = user_info['sub']

        conn = get_db()
        user = conn.execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()
        if user:
            conn.execute("UPDATE users SET google_id=? WHERE id=?", (google_id, user['id']))
            conn.commit()
        else:
            conn.execute("INSERT INTO users (name, email, google_id) VALUES (?, ?, ?)",
                         (name, email, google_id))
            conn.commit()
            user = conn.execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()
        conn.close()

        session['user_id'] = user['id']
        session['name']    = user['name']
        session['role']    = user['role']
        conn = get_db()
        conn.execute("UPDATE users SET last_login=? WHERE id=?", (datetime.now(), user['id']))
        conn.commit()
        conn.close()
        return redirect(url_for('index'))
    except Exception as e:
        return redirect(url_for('login_page') + '?error=google_failed')


# ─── Forgot / Reset Password ─────────────────────────────────────────────────
@app.route("/api/auth/forgot-password", methods=["POST"])
def forgot_password():
    email = request.json.get("email", "").strip().lower()
    conn = get_db()
    user = conn.execute("SELECT id FROM users WHERE email=?", (email,)).fetchone()
    if not user:
        conn.close()
        # Don't reveal if email exists
        return jsonify({"status": "ok", "message": "If that email exists, a reset link was sent."})

    token = serializer.dumps(email, salt='pw-reset')
    conn.execute("UPDATE users SET reset_token=? WHERE email=?", (token, email))
    conn.commit()
    conn.close()

    reset_url = url_for('reset_password_page', token=token, _external=True)
    # In production, send via email. For demo, return the link.
    return jsonify({
        "status": "ok",
        "message": "Reset link generated.",
        "reset_url": reset_url   # REMOVE THIS in production; use email instead
    })


@app.route("/reset-password/<token>")
def reset_password_page(token):
    try:
        serializer.loads(token, salt='pw-reset', max_age=3600)
    except (SignatureExpired, BadSignature):
        return render_template("login.html", reset_error="Reset link expired or invalid.")
    return render_template("login.html", reset_token=token)


@app.route("/api/auth/reset-password", methods=["POST"])
def reset_password():
    data     = request.json
    token    = data.get("token")
    password = data.get("password", "")

    try:
        email = serializer.loads(token, salt='pw-reset', max_age=3600)
    except (SignatureExpired, BadSignature):
        return jsonify({"error": "Reset link expired or invalid"}), 400

    if len(password) < 6:
        return jsonify({"error": "Password must be at least 6 characters"}), 400

    conn = get_db()
    conn.execute("UPDATE users SET password=?, reset_token=NULL WHERE email=?",
                 (generate_password_hash(password), email))
    conn.commit()
    conn.close()
    return jsonify({"status": "ok", "message": "Password updated. Please log in."})


# ═══════════════════════════════════════════════════════════════════════════════
#  ADMIN — RATE MANAGEMENT
# ═══════════════════════════════════════════════════════════════════════════════
@app.route("/api/admin/rates", methods=["GET"])
@admin_required
def get_rates():
    """Return all current rate settings (defaults merged with overrides) and full electricity tables."""
    conn = get_db()
    rows = conn.execute("SELECT bill_type, key_name, value FROM rate_overrides").fetchall()
    conn.close()
    overrides = {f"{r['bill_type']}::{r['key_name']}": json.loads(r['value']) for r in rows}
    return jsonify({
        "overrides": overrides,
        "defaults": _default_rates_summary(),
        "electricity_rates": _electricity_rate_tables()
    })


@app.route("/api/admin/rates", methods=["POST"])
@admin_required
def update_rates():
    """Admin posts {bill_type, key_name, value} to override a rate."""
    data      = request.json
    bill_type = data.get("bill_type")
    key_name  = data.get("key_name")
    value     = data.get("value")

    if not all([bill_type, key_name, value is not None]):
        return jsonify({"error": "bill_type, key_name, value are required"}), 400

    set_override(bill_type, key_name, value)
    return jsonify({"status": "ok", "message": f"{bill_type}/{key_name} updated"})


@app.route("/api/admin/users", methods=["GET"])
@admin_required
def list_users():
    conn = get_db()
    users = conn.execute("SELECT id, name, email, role, created_at, last_login FROM users ORDER BY created_at DESC").fetchall()
    conn.close()
    return jsonify([dict(u) for u in users])


@app.route("/api/admin/users/<int:uid>/role", methods=["POST"])
@admin_required
def change_role(uid):
    role = request.json.get("role", "user")
    if role not in ("user", "admin"):
        return jsonify({"error": "Invalid role"}), 400
    conn = get_db()
    conn.execute("UPDATE users SET role=? WHERE id=?", (role, uid))
    conn.commit()
    conn.close()
    return jsonify({"status": "ok"})


def _default_rates_summary():
    return {
        "electricity": {
            "fixed_charge_domestic": 50,
            "fixed_charge_commercial": 150,
            "electricity_duty_pct": 5,
            "TN_free_units": 100
        },
        "water": {
            "sewerage_pct": 60,
            "service_charge": 30
        },
        "gas": {
            "domestic_14kg_base": 903.00,
            "domestic_14kg_subsidy": 200.00,
            "domestic_5kg_base": 400.00,
            "domestic_5kg_subsidy": 75.00,
            "commercial_19kg_base": 1785.00,
            "delivery_charge": 50
        },
        "internet": {
            "gst_pct": 18,
            "discount_6months_pct": 5,
            "discount_12months_pct": 10
        }
    }


def _electricity_rate_tables():
    return {
        state: {
            "domestic": [
                {"limit": int(limit) if limit != float('inf') else "∞", "rate": rate}
                for limit, rate in details["domestic"]
            ]
        }
        for state, details in ELECTRICITY_RATE_TABLES.items()
    }


# ═══════════════════════════════════════════════════════════════════════════════
#  BILL CALCULATORS (with dynamic overrides)
# ═══════════════════════════════════════════════════════════════════════════════
def calculate_electricity(units, state="Tamil Nadu", consumer_type="domestic"):
    slabs_data = ELECTRICITY_RATE_TABLES.get(state, ELECTRICITY_RATE_TABLES["Default"]).get(
        consumer_type, ELECTRICITY_RATE_TABLES["Default"]["domestic"]
    )
    bill, prev_limit, breakdown = 0.0, 0, []

    for limit, rate in slabs_data:
        if units <= prev_limit: break
        taxable = min(units, limit) - prev_limit
        charge = taxable * rate
        breakdown.append({"range": f"{prev_limit+1}–{int(limit) if limit!=float('inf') else '∞'}",
                          "units": taxable, "rate": rate, "charge": round(charge, 2)})
        bill += charge
        prev_limit = limit

    fixed_charge = get_override("electricity", "fixed_charge_domestic" if consumer_type=="domestic" else "fixed_charge_commercial",
                                50 if consumer_type=="domestic" else 150)
    duty_pct = get_override("electricity", "electricity_duty_pct", 5)
    electricity_duty = round(bill * (duty_pct / 100), 2)
    total = round(bill + fixed_charge + electricity_duty, 2)

    return {"units": units, "state": state, "consumer_type": consumer_type,
            "energy_charge": round(bill,2), "fixed_charge": fixed_charge,
            "electricity_duty": electricity_duty, "total": total,
            "breakdown": breakdown, "due_date": _due_date()}


def calculate_water(kiloliters, city="Coimbatore", connection_type="residential"):
    rates = {
        "Coimbatore": {"residential": [(10,5),(20,8),(30,12),(float('inf'),18)],
                       "commercial":  [(10,15),(20,22),(float('inf'),30)]},
        "Chennai":    {"residential": [(10,4),(20,7),(30,11),(float('inf'),16)],
                       "commercial":  [(10,12),(20,20),(float('inf'),28)]},
        "Bangalore":  {"residential": [(8,6),(25,10),(float('inf'),20)],
                       "commercial":  [(10,18),(float('inf'),32)]},
        "Default":    {"residential": [(10,5),(25,10),(float('inf'),15)],
                       "commercial":  [(10,15),(float('inf'),25)]},
    }
    slabs_data = rates.get(city, rates["Default"]).get(connection_type, rates["Default"]["residential"])
    bill, prev, breakdown = 0.0, 0, []
    for limit, rate in slabs_data:
        if kiloliters <= prev: break
        kl = min(kiloliters, limit) - prev
        charge = kl * rate
        breakdown.append({"range": f"{prev+1}–{int(limit) if limit!=float('inf') else '∞'} KL",
                          "kiloliters": kl, "rate": rate, "charge": round(charge,2)})
        bill += charge
        prev = limit

    sewerage_pct = get_override("water", "sewerage_pct", 60)
    service_charge = get_override("water", "service_charge", 30)
    sewerage = round(bill * (sewerage_pct / 100), 2)
    total = round(bill + sewerage + service_charge, 2)

    return {"kiloliters": kiloliters, "city": city, "connection_type": connection_type,
            "water_charge": round(bill,2), "sewerage_charge": sewerage,
            "service_charge": service_charge, "total": total,
            "breakdown": breakdown, "due_date": _due_date()}


def calculate_gas(cylinders, cylinder_type="domestic_14kg"):
    defaults = {
        "domestic_14kg":   {"base": 903.00, "subsidy": 200.00, "label": "Domestic 14.2 kg"},
        "domestic_5kg":    {"base": 400.00, "subsidy": 75.00,  "label": "Domestic 5 kg"},
        "commercial_19kg": {"base": 1785.00,"subsidy": 0,      "label": "Commercial 19 kg"},
    }
    info = defaults.get(cylinder_type, defaults["domestic_14kg"])
    base_per    = get_override("gas", f"{cylinder_type}_base",    info["base"])
    subsidy_per = get_override("gas", f"{cylinder_type}_subsidy", info["subsidy"])
    delivery    = get_override("gas", "delivery_charge", 50) if cylinders > 0 else 0

    base_cost = round(cylinders * base_per, 2)
    subsidy   = round(cylinders * subsidy_per, 2)
    total     = round(base_cost - subsidy + delivery, 2)

    return {"cylinders": cylinders, "cylinder_type": cylinder_type,
            "cylinder_label": info["label"], "base_price_per": base_per,
            "subsidy_per": subsidy_per, "base_cost": base_cost,
            "subsidy": subsidy, "delivery_charge": delivery,
            "total": total, "due_date": _due_date()}


def calculate_internet(plan, provider="BSNL", months=1):
    plans = {
        "BSNL":       {"Basic 50Mbps":{"monthly":449,"data":"Unlimited","speed":"50 Mbps"},
                       "Standard 100Mbps":{"monthly":699,"data":"Unlimited","speed":"100 Mbps"},
                       "Premium 200Mbps":{"monthly":999,"data":"Unlimited","speed":"200 Mbps"}},
        "Jio Fiber":  {"Bronze 30Mbps":{"monthly":399,"data":"3.3 TB","speed":"30 Mbps"},
                       "Silver 100Mbps":{"monthly":699,"data":"Unlimited","speed":"100 Mbps"},
                       "Gold 300Mbps":{"monthly":999,"data":"Unlimited","speed":"300 Mbps"},
                       "Platinum 1Gbps":{"monthly":1499,"data":"Unlimited","speed":"1 Gbps"}},
        "ACT Fibernet":{"Basic 75Mbps":{"monthly":529,"data":"1 TB","speed":"75 Mbps"},
                        "Plus 150Mbps":{"monthly":799,"data":"Unlimited","speed":"150 Mbps"},
                        "Pro 300Mbps":{"monthly":1099,"data":"Unlimited","speed":"300 Mbps"}},
    }
    info = plans.get(provider, plans["BSNL"]).get(plan)
    if not info: return {"error": "Plan not found"}

    gst_pct = get_override("internet", "gst_pct", 18)
    d6  = get_override("internet", "discount_6months_pct", 5)
    d12 = get_override("internet", "discount_12months_pct", 10)

    base = info["monthly"] * months
    gst  = round(base * (gst_pct / 100), 2)
    total = round(base + gst, 2)
    discount = 0
    if months >= 12: discount = round(base * (d12/100), 2)
    elif months >= 6: discount = round(base * (d6/100), 2)
    final = round(total - discount, 2)

    return {"provider": provider, "plan": plan, "speed": info["speed"], "data": info["data"],
            "monthly_rate": info["monthly"], "months": months, "base_cost": base,
            "gst": gst, "discount": discount, "total": final, "due_date": _due_date()}


def _due_date():
    return (datetime.now() + timedelta(days=15)).strftime("%d %b %Y")


# ═══════════════════════════════════════════════════════════════════════════════
#  CALCULATOR API ROUTES
# ═══════════════════════════════════════════════════════════════════════════════
@app.route("/api/electricity", methods=["POST"])
@login_required
def electricity():
    d = request.json
    return jsonify(calculate_electricity(float(d.get("units",0)), d.get("state","Tamil Nadu"), d.get("consumer_type","domestic")))

@app.route("/api/water", methods=["POST"])
@login_required
def water():
    d = request.json
    return jsonify(calculate_water(float(d.get("kiloliters",0)), d.get("city","Coimbatore"), d.get("connection_type","residential")))

@app.route("/api/gas", methods=["POST"])
@login_required
def gas():
    d = request.json
    return jsonify(calculate_gas(int(d.get("cylinders",1)), d.get("cylinder_type","domestic_14kg")))

@app.route("/api/internet", methods=["POST"])
@login_required
def internet():
    d = request.json
    return jsonify(calculate_internet(d.get("plan","Basic 50Mbps"), d.get("provider","BSNL"), int(d.get("months",1))))

@app.route("/api/plans", methods=["GET"])
def plans():
    plan_map = {
        "BSNL":        ["Basic 50Mbps","Standard 100Mbps","Premium 200Mbps"],
        "Jio Fiber":   ["Bronze 30Mbps","Silver 100Mbps","Gold 300Mbps","Platinum 1Gbps"],
        "ACT Fibernet":["Basic 75Mbps","Plus 150Mbps","Pro 300Mbps"],
    }
    return jsonify(plan_map.get(request.args.get("provider","BSNL"), []))

@app.route("/api/history", methods=["GET"])
@login_required
def get_history():
    conn = get_db()
    uid = session['user_id']
    role = session.get('role')
    if role == 'admin':
        rows = conn.execute(
            """SELECT h.*, u.email AS user_email, u.name AS user_name
               FROM history h
               LEFT JOIN users u ON u.id = h.user_id
               ORDER BY h.timestamp DESC"""
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT h.*, NULL AS user_email, NULL AS user_name FROM history h WHERE h.user_id=? ORDER BY h.timestamp DESC",
            (uid,)
        ).fetchall()
    conn.close()
    history = []
    for r in rows:
        record = dict(r)
        record['details'] = json.loads(r['details'])
        history.append(record)
    return jsonify(history)

@app.route("/api/history", methods=["POST"])
@login_required
def add_history():
    d = request.json
    conn = get_db()
    status = d.get("status", "UNPAID")
    conn.execute("INSERT INTO history (bill_type, amount, details, user_id, status) VALUES (?,?,?,?,?)",
                 (d.get("bill_type"), d.get("amount"), json.dumps(d.get("details",{})), session['user_id'], status))
    conn.commit()
    
    # Get last inserted id to return to client
    cur = conn.cursor()
    hid = cur.execute("SELECT last_insert_rowid()").fetchone()[0]
    conn.close()
    return jsonify({"status": "success", "id": hid}), 201

@app.route("/api/history/<int:hid>/pay", methods=["POST"])
@login_required
def pay_history(hid):
    d = request.json or {}
    payment_method = d.get("payment_method", "card")
    biller = d.get("biller", "Unknown Utility Board")
    
    conn = get_db()
    uid = session['user_id']
    role = session.get('role')
    
    if role == 'admin':
        row = conn.execute("SELECT * FROM history WHERE id=?", (hid,)).fetchone()
    else:
        row = conn.execute("SELECT * FROM history WHERE id=? AND user_id=?", (hid, uid)).fetchone()
        
    if not row:
        conn.close()
        return jsonify({"error": "Bill record not found"}), 404
        
    record = dict(row)
    details = json.loads(record['details'])
    
    # Generate mock transaction reference
    import random
    import string
    txn_id = "TXN" + "".join(random.choices(string.digits, k=10))
    
    details['payment'] = {
        "status": "PAID",
        "method": payment_method,
        "txn_id": txn_id,
        "timestamp": datetime.now().isoformat(),
        "biller": biller
    }
    
    conn.execute(
        "UPDATE history SET status='PAID', details=? WHERE id=?",
        (json.dumps(details), hid)
    )
    conn.commit()
    conn.close()
    
    return jsonify({
        "status": "success",
        "message": f"Payment of ₹{record['amount']} successful!",
        "txn_id": txn_id,
        "biller": biller
    })


if __name__ == "__main__":
    app.run(debug=True, port=5000)