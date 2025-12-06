# models.py
from extensions import db

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)

    def __repr__(self):
        return f"<User {self.username}>"

class MaterialRequest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    material_name = db.Column(db.String(150), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    requested_by = db.Column(db.String(150), nullable=False)
    request_date = db.Column(db.DateTime, default=db.func.current_timestamp())

    def __repr__(self):
        return f"<MaterialRequest {self.material_name}>"
