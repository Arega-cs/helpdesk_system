from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
import os
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key_here'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['UPLOAD_FOLDER'] = 'static/uploads'

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(20), nullable=False)
    tickets = db.relationship('Ticket', backref='author', lazy=True)

class Ticket(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    pc_number = db.Column(db.String(50), nullable=False)
    issue_type = db.Column(db.String(20), default='Hardware')
    issue_description = db.Column(db.Text, nullable=False)
    image_file = db.Column(db.String(100), nullable=True)
    status = db.Column(db.String(20), default='Pending')
    response = db.Column(db.Text, default='ገና ምላሽ አልተሰጠም')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

@app.route('/', methods=['GET', 'POST'])
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        
        if user and check_password_hash(user.password, password):
            login_user(user)
            if user.role == 'technician':
                return redirect(url_for('tech_dashboard'))
            return redirect(url_for('user_dashboard'))
        flash('የተሳሳተ የተጠቃሚ ስም ወይም ፓስወርድ!')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = generate_password_hash(request.form.get('password'))
        role = request.form.get('role')
        
        new_user = User(username=username, password=password, role=role)
        db.session.add(new_user)
        db.session.commit()
        flash('አካውንትዎ በትክክል ተፈጥሯል! አሁን መግባት ይችላሉ።')
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/user_dashboard', methods=['GET', 'POST'])
@login_required
def user_dashboard():
    if request.method == 'POST':
        pc_number = request.form.get('pc_number')
        issue_type = request.form.get('issue_type')
        issue = request.form.get('issue')
        
        file = request.files.get('file')
        filename = None
        if file and file.filename != '':
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

        new_ticket = Ticket(
            pc_number=pc_number, 
            issue_type=issue_type, 
            issue_description=issue,
            image_file=filename,
            user_id=current_user.id
        )
        db.session.add(new_ticket)
        db.session.commit()
        flash('የጥገና ጥያቄዎ በተሳካ ሁኔታ ተላኳል!')
        return redirect(url_for('user_dashboard'))
    
    user_tickets = Ticket.query.filter_by(user_id=current_user.id).all()
    return render_template('user_dashboard.html', tickets=user_tickets)

@app.route('/tech_dashboard', methods=['GET', 'POST'])
@login_required
def tech_dashboard():
    if current_user.role != 'technician':
        return "ይህንን ገጽ የማየት ፈቃድ የለዎትም!", 403

    if request.method == 'POST':
        ticket_id = request.form.get('ticket_id')
        response_text = request.form.get('response')
        new_status = request.form.get('status')

        ticket = Ticket.query.get(ticket_id)
        if ticket:
            ticket.response = response_text
            ticket.status = new_status
            db.session.commit()
            flash('ምላሽዎ ተልኳል!')

    all_tickets = Ticket.query.all()
    return render_template('tech_dashboard.html', tickets=all_tickets)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)