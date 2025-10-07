from flask import Flask, render_template, request, redirect, session, url_for, flash
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'  # Change this to a random secret in production
app.permanent_session_lifetime = 65 * 24 * 60 * 60  # 65 days in seconds

HEALTH_TASKS = [
	{'id': 'drink_water', 'name': 'Drink 8 glasses of water'},
	{'id': 'walk', 'name': 'Walk 10,000 steps'},
	{'id': 'sleep', 'name': 'Sleep at least 7 hours'},
	{'id': 'meditate', 'name': 'Meditate for 10 minutes'},
	{'id': 'fruit', 'name': 'Eat a fruit'},
]

def get_today():
	return datetime.now().strftime('%Y-%m-%d')

def ensure_session():
    today = get_today()
    last_date = session.get('last_date')
    if last_date != today:
        if last_date and (datetime.strptime(today, '%Y-%m-%d') - datetime.strptime(last_date, '%Y-%m-%d')).days > 1:
            session['streak'] = 0
        session['tasks'] = {task['id']: False for task in HEALTH_TASKS}
        session['last_date'] = today
        session['completed_today'] = False
    if 'streak' not in session:
        session['streak'] = 0
    if 'tasks' not in session:
        session['tasks'] = {task['id']: False for task in HEALTH_TASKS}
    if 'last_date' not in session:
        session['last_date'] = get_today()
    if 'completed_today' not in session:
        session['completed_today'] = False

def reset_tasks_if_needed():
    today = get_today()
    last_date = session.get('last_date')
    if last_date != today:
        session['tasks'] = {task['id']: False for task in HEALTH_TASKS}
        session['last_date'] = today
        session['completed_today'] = False

def user_info_required():
	return 'user' in session and session['user'].get('name') and session['user'].get('age')

@app.route('/')
def landing():
	if 'user' in session and session['user'].get('name') and session['user'].get('age'):
		return redirect(url_for('streak'))
	return render_template('landing.html')

@app.route('/tasks', methods=['GET'])
def tasks():
	if not user_info_required():
		return redirect(url_for('user'))
	ensure_session()
	reset_tasks_if_needed()
	tasks = []
	for task in HEALTH_TASKS:
		tasks.append({
			'id': task['id'],
			'name': task['name'],
			'done': session['tasks'].get(task['id'], False)
		})
	return render_template('index.html', tasks=tasks, streak=session['streak'])

@app.route('/update', methods=['POST'])
def update():
	if not user_info_required():
		return redirect(url_for('user'))
	ensure_session()
	reset_tasks_if_needed()
	task_id = request.form.get('task')
	if task_id and task_id in session['tasks']:
		# Only allow marking as complete, not un-completing
		if not session['tasks'][task_id]:
			session['tasks'][task_id] = True
	if all(session['tasks'].values()):
		if not session.get('completed_today'):
			session['streak'] += 1
			session['completed_today'] = True
	else:
		session['completed_today'] = False
	return redirect(url_for('tasks'))

@app.route('/streak')
def streak():
	if not user_info_required():
		return redirect(url_for('user'))
	ensure_session()
	reset_tasks_if_needed()
	return render_template('streak.html', streak=session['streak'])
@app.route('/user', methods=['GET', 'POST'])
def user():
	if request.method == 'POST':
		if 'clear' in request.form:
			# User confirmed clear data
			session.clear()
			return redirect(url_for('user'))
		name = request.form.get('name', '').strip()
		age = request.form.get('age', '').strip()
		gender = request.form.get('gender', '').strip()
		goal = request.form.get('goal', '').strip()
		if not name or not age:
			return render_template('user.html', error='Name and age are required.')
		session['user'] = {'name': name, 'age': age, 'gender': gender, 'goal': goal}
		return redirect(url_for('tasks'))
	userinfo = session.get('user')
	return render_template('user.html', user=userinfo)

@app.route('/benefits')
def benefits():
	return render_template('benefits.html')

@app.before_request
def make_session_permanent():
    session.permanent = True

if __name__ == '__main__':
	app.run(debug=True)
