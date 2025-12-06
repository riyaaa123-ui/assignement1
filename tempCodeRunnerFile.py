from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

# ---------------- App Setup ----------------
app = Flask(__name__)
app.config['SECRET_KEY'] = '123456'
app.config['SQLALCHEMY_DATABASE_URI'] = "sqlite:///workflow.db"  # simple SQLite DB
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# ---------------- Database Model ----------------
class MaterialRequest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    department = db.Column(db.String(50), nullable=False)
    requester = db.Column(db.String(100), nullable=False)
    material_name = db.Column(db.String(100), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    status = db.Column(db.String(20), default="Pending")
    date_created = db.Column(db.DateTime, default=datetime.now)
    remarks = db.Column(db.String(200))

# ---------------- Routes ----------------
@app.route('/')
def dashboard():
    requests = MaterialRequest.query.order_by(MaterialRequest.date_created.desc()).all()
    return render_template('dashboard.html', requests=requests)

@app.route('/new_request', methods=['GET', 'POST'])
def new_request():
    if request.method == 'POST':
        req = MaterialRequest(
            department=request.form['department'],
            requester=request.form['requester'],
            material_name=request.form['material_name'],
            quantity=request.form['quantity']
        )
        db.session.add(req)
        db.session.commit()
        flash("Request submitted successfully!", "success")
        return redirect(url_for('dashboard'))

    return render_template('new_request.html')

# ---------------- Run App ----------------
if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)
