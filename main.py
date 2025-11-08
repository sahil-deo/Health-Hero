from datetime import datetime, timedelta
import os
from flask import Flask, render_template, request, redirect, url_for, flash
from flask_login import (LoginManager, UserMixin, login_user,
                     logout_user, current_user, login_required)
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# --- App and DB Setup ---

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'your_secret_key_here')

# Set the database URI from environment variable
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', os.getenv('DATABASE_URI'))
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'


HEALTH_TASKS = [
    {'id': 'drink_water', 'name': 'Drink 8 glasses of water'},
    {'id': 'walk', 'name': 'Walk 10,000 steps'},
    {'id': 'sleep', 'name': 'Sleep at least 7 hours'},
    {'id': 'meditate', 'name': 'Meditate for 10 minutes'},
    {'id': 'fruit', 'name': 'Eat a fruit'},
]

# --- Models ---

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    name = db.Column(db.String(32))
    age = db.Column(db.Integer)
    gender = db.Column(db.String(20))
    goal = db.Column(db.String(64))
    streak = db.Column(db.Integer, default=0)
    last_date = db.Column(db.String(10), default=lambda: get_today())
    completed_today = db.Column(db.Boolean, default=False)
    last_login = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class UserTask(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    task_id = db.Column(db.String(50), nullable=False)
    date = db.Column(db.String(10), nullable=False)
    done = db.Column(db.Boolean, default=False)
    __table_args__ = (db.UniqueConstraint('user_id', 'task_id', 'date', name='_user_task_date_uc'),)


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# --- Helper Functions ---

def get_today():
    return datetime.now().strftime('%Y-%m-%d')

def reset_streak_and_tasks_if_needed(user):
    today = get_today()
    last_date_str = user.last_date
    if not last_date_str:
        user.last_date = today
        db.session.commit()
        return
    if last_date_str != today:
        try:
            last_date = datetime.strptime(last_date_str, '%Y-%m-%d')
            if (datetime.strptime(today, '%Y-%m-%d') - last_date).days > 1:
                user.streak = 0
        except (ValueError, TypeError):
            # If date format is invalid, reset to today
            user.last_date = today
        user.completed_today = False
        user.last_date = today
        db.session.commit()

# --- Routes ---

@app.before_request
def check_profile_completion():
    # List of endpoints that are allowed without a complete profile
    allowed_endpoints = ['user', 'login', 'signup', 'logout', 'static']
    if (current_user.is_authenticated and 
        current_user.username != 'admin' and 
        request.endpoint not in allowed_endpoints):
        if not current_user.name or not current_user.age:
            flash("Please complete your profile to continue.")
            return redirect(url_for('user'))


@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('tasks'))
    return redirect(url_for('login'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('tasks'))
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        # Admin login
        if username == 'admin' and password == 'password':
            admin_user = User.query.filter_by(username='admin').first()
            if not admin_user: # Create admin if not exists
                 admin_user = User(username='admin', name='Admin')
                 admin_user.set_password('password')
                 db.session.add(admin_user)
                 db.session.commit()
            login_user(admin_user)
            return redirect(url_for('admin'))

        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            login_user(user)
            user.last_login = datetime.utcnow()
            db.session.commit()
            return redirect(url_for('tasks'))
        else:
            flash('Invalid username or password')
    return render_template('login.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if current_user.is_authenticated:
        return redirect(url_for('tasks'))
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        name = request.form.get('name')
        age = request.form.get('age')

        if not all([username, password, name, age]):
            flash("All fields are required!")
            return redirect(url_for('signup'))

        try:
            age = int(age)
        except (ValueError, TypeError):
            flash("Age must be a valid number!")
            return redirect(url_for('signup'))

        if User.query.filter_by(username=username).first():
            flash('Username already exists')
            return redirect(url_for('signup'))

        new_user = User(username=username, name=name, age=age)
        new_user.set_password(password)
        db.session.add(new_user)
        db.session.commit()
        login_user(new_user)
        flash("Account created! Please fill out your optional details.")
        return redirect(url_for('user'))
    return render_template('signup.html')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/admin')
@login_required
def admin():
    if current_user.username != 'admin':
        return redirect(url_for('tasks'))

    users = User.query.filter(User.username != 'admin').all()
    
    total_users = len(users)
    avg_streak = db.session.query(db.func.avg(User.streak)).filter(User.username != 'admin').scalar() or 0
    avg_age = db.session.query(db.func.avg(User.age)).filter(User.username != 'admin').scalar() or 0
    
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    users_today = User.query.filter(User.last_login >= today_start, User.username != 'admin').count()

    week_ago = datetime.utcnow() - timedelta(days=7)
    users_weekly = User.query.filter(User.last_login >= week_ago, User.username != 'admin').count()
    
    stats = {
        'total_users': total_users,
        'avg_streak': round(avg_streak, 2),
        'avg_age': round(avg_age, 2) if avg_age else 0,
        'users_today': users_today,
        'users_weekly': users_weekly,
    }

    return render_template('admin.html', users=users, stats=stats)


@app.route('/tasks', methods=['GET'])
@login_required
def tasks():
    reset_streak_and_tasks_if_needed(current_user)
    today = get_today()
    
    user_tasks_today = UserTask.query.filter_by(user_id=current_user.id, date=today).all()
    completed_task_ids = {ut.task_id for ut in user_tasks_today if ut.done}

    tasks_to_render = []
    for task in HEALTH_TASKS:
        tasks_to_render.append({
            'id': task['id'],
            'name': task['name'],
            'done': task['id'] in completed_task_ids
        })
    return render_template('tasks.html', tasks=tasks_to_render, streak=current_user.streak)


@app.route('/update', methods=['POST'])
@login_required
def update():
    reset_streak_and_tasks_if_needed(current_user)
    task_id = request.form.get('task')
    today = get_today()

    if task_id:
        user_task = UserTask.query.filter_by(user_id=current_user.id, task_id=task_id, date=today).first()
        if not user_task:
            user_task = UserTask(user_id=current_user.id, task_id=task_id, date=today)
            db.session.add(user_task)
        
        if not user_task.done:
            user_task.done = True
            db.session.commit()

    # Check for streak update
    completed_tasks_count = UserTask.query.filter_by(user_id=current_user.id, date=today, done=True).count()
    if completed_tasks_count == len(HEALTH_TASKS) and not current_user.completed_today:
        current_user.streak += 1
        current_user.completed_today = True
        db.session.commit()

    return redirect(url_for('tasks'))

@app.route('/streak')
@login_required
def streak():
    reset_streak_and_tasks_if_needed(current_user)
    return render_template('streak.html', streak=current_user.streak)


@app.route('/user', methods=['GET', 'POST'])
@login_required
def user():
    if request.method == 'POST':
        if 'clear' in request.form:
            UserTask.query.filter_by(user_id=current_user.id).delete()
            db.session.delete(current_user)
            db.session.commit()
            logout_user()
            flash('Your account has been deleted.')
            return redirect(url_for('login'))
        
        current_user.name = request.form.get('name', '').strip()
        age_str = request.form.get('age', '').strip()
        current_user.gender = request.form.get('gender', '').strip()
        current_user.goal = request.form.get('goal', '').strip()

        if not current_user.name or not age_str:
            flash('Name and age are required.')
            return render_template('user.html', user=current_user)
        
        try:
            current_user.age = int(age_str)
        except (ValueError, TypeError):
            flash('Age must be a valid number.')
            return render_template('user.html', user=current_user)

        db.session.commit()
        flash('Your information has been updated.')
        return redirect(url_for('tasks'))
        
    return render_template('user.html', user=current_user)


@app.route('/benefits')
@login_required
def benefits():
    return render_template('benefits.html')

def init_db():
    with app.app_context():
        db.create_all()
        if not User.query.filter_by(username='admin').first():
            admin_user = User(username='admin', name='Admin')
            admin_user.set_password('password')
            db.session.add(admin_user)
            db.session.commit()
            print("Admin user created.")

if __name__ == '__main__':
    app.run(debug=True)