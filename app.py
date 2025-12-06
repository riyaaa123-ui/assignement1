# app.py
from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from functools import wraps
from datetime import datetime

# ---------------- App Setup ----------------
app = Flask(__name__)
app.config.from_object("config")
app.secret_key = app.config.get("SECRET_KEY", "change_this_secret")
db = SQLAlchemy(app)

# ---------------- Models ----------------
class User(db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)   # plaintext demo
    role = db.Column(db.String(50), nullable=False)
    department = db.Column(db.String(50))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class MaterialRequest(db.Model):
    __tablename__ = "material_requests"
    id = db.Column(db.Integer, primary_key=True)
    plant = db.Column(db.String(100), nullable=False)
    department_raised = db.Column(db.String(50), nullable=False)
    item_name = db.Column(db.String(200), nullable=False)
    material_description = db.Column(db.Text)
    unit_of_measurement = db.Column(db.String(50))
    material_group = db.Column(db.String(50))
    material_type = db.Column(db.String(50))
    status = db.Column(db.String(50), default="Pending")
    raised_by = db.Column(db.String(120), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Workflow + audit fields
    hod_approved = db.Column(db.Boolean, default=False)
    hod_approved_by = db.Column(db.String(120))
    hod_approved_at = db.Column(db.DateTime)

    dept_hod_approved = db.Column(db.Boolean, default=False)
    dept_hod_approved_by = db.Column(db.String(120))
    dept_hod_approved_at = db.Column(db.DateTime)

    store_approved = db.Column(db.Boolean, default=False)
    store_approved_by = db.Column(db.String(120))
    store_approved_at = db.Column(db.DateTime)

    gst_approved = db.Column(db.Boolean, default=False)
    gst_approved_by = db.Column(db.String(120))
    gst_approved_at = db.Column(db.DateTime)

    purchase_approved = db.Column(db.Boolean, default=False)
    purchase_approved_by = db.Column(db.String(120))
    purchase_approved_at = db.Column(db.DateTime)

    it_approved = db.Column(db.Boolean, default=False)
    it_approved_by = db.Column(db.String(120))
    it_approved_at = db.Column(db.DateTime)


# ---------------- Auth Decorator ----------------
def login_required(role=None):
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            if "user_id" not in session:
                flash("Please log in first.", "warning")
                return redirect(url_for("login", next=request.path))
            if role and session.get("role") not in [role, "Admin"]:
                flash("Access denied.", "danger")
                return redirect(url_for("dashboard"))
            return fn(*args, **kwargs)
        return wrapper
    return decorator


# ---------------- Helper: Current step ----------------
def current_step(req):
    if not req.hod_approved: return "HOD"
    if not req.dept_hod_approved: return "DEPTHOD"
    if not req.store_approved: return "STORE"
    if not req.gst_approved: return "GST"
    if not req.purchase_approved: return "PURCHASE"
    if not req.it_approved: return "IT"
    return None

app.jinja_env.globals.update(current_step=current_step)


# ---------------- Front Page ----------------
@app.route("/home")
def home():
    return render_template("index.html", page_title="Material Workflow System")


@app.route("/")
def root():
    if "user_id" in session:
        return redirect(url_for("dashboard"))
    return redirect(url_for("home"))


# ---------------- Login ----------------
@app.route("/login", methods=["GET", "POST"])
def login():
    next_url = request.args.get("next") or url_for("dashboard")
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        user = User.query.filter_by(username=username, password=password).first()

        if user:
            session["user_id"] = user.id
            session["user_name"] = user.username
            session["role"] = user.role
            return redirect(next_url)

        flash("Invalid credentials", "danger")

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    flash("Logged out.", "info")
    return redirect(url_for("login"))


# ---------------- Dashboard ----------------
@app.route("/dashboard")
@login_required()
def dashboard():

    role = session.get("role")
    username = session.get("user_name")

    query = MaterialRequest.query

    # ROLE-BASED VISIBILITY
    if role == "User":
        query = query.filter_by(raised_by=username)

    elif role == "HOD":
        query = query.filter(MaterialRequest.hod_approved == False)

    elif role == "Dept HOD":
        query = query.filter(
            MaterialRequest.hod_approved == True,
            MaterialRequest.dept_hod_approved == False
        )

    elif role == "Store":
        query = query.filter(
            MaterialRequest.dept_hod_approved == True,
            MaterialRequest.store_approved == False
        )

    elif role == "GST":
        query = query.filter(
            MaterialRequest.store_approved == True,
            MaterialRequest.gst_approved == False
        )

    elif role == "Purchase":
        query = query.filter(
            MaterialRequest.gst_approved == True,
            MaterialRequest.purchase_approved == False
        )

    elif role == "IT":
        query = query.filter(
            MaterialRequest.purchase_approved == True,
            MaterialRequest.it_approved == False
        )

    # Admin sees everything
    requests = query.order_by(MaterialRequest.created_at.desc()).all()

    # Admin stats
    stats = None
    if role == "Admin":
        stats = {
            "Pending": MaterialRequest.query.filter_by(status="Pending").count(),
            "Store Verified": MaterialRequest.query.filter_by(status="Store Verified").count(),
            "Purchase Approved": MaterialRequest.query.filter_by(status="Purchase Approved").count(),
            "IT Approved": MaterialRequest.query.filter(MaterialRequest.it_approved == True).count(),
        }

    return render_template("dashboard.html", requests=requests, stats=stats)


# ---------------- New Request ----------------
@app.route("/new_request", methods=["GET", "POST"])
@login_required()
def new_request():
    if request.method == "POST":

        req = MaterialRequest(
            plant=request.form.get("plant"),
            department_raised=request.form.get("department_raised"),
            item_name=request.form.get("item_name"),
            material_description=request.form.get("material_description"),
            unit_of_measurement=request.form.get("unit_of_measurement"),
            material_group=request.form.get("material_group"),
            material_type=request.form.get("material_type"),
            raised_by=session.get("user_name")
        )

        db.session.add(req)
        db.session.commit()

        flash("Request created!", "success")
        return redirect(url_for("dashboard"))

    return render_template("new_request.html")


# ---------------- View Request ----------------
@app.route("/request/<int:rid>")
@login_required()
def view_request(rid):
    req = MaterialRequest.query.get_or_404(rid)
    return render_template("view_request.html", req=req)


# ---------------- Approvals ----------------
@app.route("/approve/<int:rid>/<string:step>", methods=["POST"])
@login_required()
def approve(rid, step):

    req = MaterialRequest.query.get_or_404(rid)
    role = session.get("role")
    username = session.get("user_name")
    step = step.upper()
    needed = current_step(req)

    # Must match required step
    if step != needed:
        flash(f"Required step: {needed}", "danger")
        return redirect(url_for("view_request", rid=rid))

    # Role permissions
    permissions = {
        "HOD": ["HOD", "Admin"],
        "DEPTHOD": ["Dept HOD", "Admin"],
        "STORE": ["Store", "Admin"],
        "GST": ["GST", "Admin"],
        "PURCHASE": ["Purchase", "Admin"],
        "IT": ["IT", "Admin"]
    }

    if role not in permissions.get(step, []):
        flash("Not allowed.", "danger")
        return redirect(url_for("view_request", rid=rid))

    now = datetime.utcnow()

    # APPROVAL LOGIC
    if step == "HOD":
        req.hod_approved = True
        req.hod_approved_by = username
        req.hod_approved_at = now
        req.status = "HOD Approved"

    elif step == "DEPTHOD":
        req.dept_hod_approved = True
        req.dept_hod_approved_by = username
        req.dept_hod_approved_at = now
        req.status = "Dept HOD Approved"

    elif step == "STORE":
        req.store_approved = True
        req.store_approved_by = username
        req.store_approved_at = now
        req.status = "Store Verified"

    elif step == "GST":
        req.gst_approved = True
        req.gst_approved_by = username
        req.gst_approved_at = now
        req.status = "GST Approved"

    elif step == "PURCHASE":
        req.purchase_approved = True
        req.purchase_approved_by = username
        req.purchase_approved_at = now

        # AUTO IT approval
        req.it_approved = True
        req.it_approved_by = "system"
        req.it_approved_at = now
        req.status = "Complete"

    db.session.commit()
    flash(f"{step} Approved!", "success")
    return redirect(url_for("dashboard"))


# ---------------- Reject ----------------
@app.route("/reject/<int:rid>", methods=["POST"])
@login_required()
def reject(rid):
    req = MaterialRequest.query.get_or_404(rid)
    req.status = "Rejected"
    db.session.commit()
    flash("Rejected.", "warning")
    return redirect(url_for("dashboard"))


# ---------------- Admin - All Requests ----------------
@app.route("/requests")
@login_required(role="Admin")
def list_requests():
    requests = MaterialRequest.query.order_by(MaterialRequest.created_at.desc()).all()
    return render_template("requests.html", requests=requests)


# ---------------- Create Demo Users ----------------
def create_test_users():
    demo = [
        ("admin", "admin123", "Admin"),
        ("hod", "hod123", "HOD"),
        ("mech_hod", "mech123", "Dept HOD"),
        ("store", "store123", "Store"),
        ("gst", "gst123", "GST"),
        ("purchase", "pur123", "Purchase"),
        ("it", "it123", "IT"),
        ("user", "user123", "User")
    ]
    for u, p, r in demo:
        if not User.query.filter_by(username=u).first():
            db.session.add(User(username=u, password=p, role=r))
    db.session.commit()


# ---------------- Run ----------------
if __name__ == "__main__":
    with app.app_context():
        db.create_all()
        create_test_users()
    app.run(debug=True)
