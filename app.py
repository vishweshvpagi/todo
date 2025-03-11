from flask import Flask, render_template, request, redirect, session
from pymongo import MongoClient
import bcrypt
from bson.objectid import ObjectId
from datetime import datetime, timedelta

app = Flask(__name__)
app.secret_key = "secret_key"  # Required for session management
try:
    client = MongoClient("mongodb://localhost:27017/")
    db = client.todo_db  
    users_collection = db.users  
    tasks_collection = db.tasks  

    # Check if the connection is successful
    print("Connected to MongoDB successfully!")

except Exception as e:
    print(f"Error connecting to MongoDB: {e}")

@app.route('/')
def home():
    # Redirect to the task list if user is logged in, otherwise to login page
    if "user" in session:
        return redirect('/tasks')
    else:
        return redirect('/login')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password'].encode('utf-8')

        user = users_collection.find_one({"username": username})
        
        if user and bcrypt.checkpw(password, user['password'].encode('utf-8')):
            session['user'] = username  # Store user session
            return redirect('/tasks')
        else:
            return "Invalid Username or Password"

    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect('/login')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password'].encode('utf-8')

        # Check if user already exists
        existing_user = users_collection.find_one({"username": username})
        if existing_user:
            return "Username already exists! Try a different one."

        # Hash the password before storing
        hashed_password = bcrypt.hashpw(password, bcrypt.gensalt())

        # Insert new user into MongoDB
        users_collection.insert_one({
            "username": username,
            "password": hashed_password.decode('utf-8')
        })

        return redirect('/login')  # Redirect to login after successful registration

    return render_template('register.html')

@app.route('/tasks')
def index():
    # Check if user is logged in
    if "user" not in session:
        return redirect('/login')
    
    # Get all tasks for the current user
    username = session['user']
    tasks = tasks_collection.find({"username": username})
    tasks_list = list(tasks)
    
    return render_template('index.html', tasks=tasks_list, filter='all', current_date=datetime.now().strftime('%Y-%m-%d'))

@app.route('/pending')
def pending_tasks():
    if "user" in session:
        username = session['user']
        tasks = tasks_collection.find({"username": username, "completed": False})
        tasks_list = list(tasks)
        return render_template('index.html', tasks=tasks_list, filter='pending', current_date=datetime.now().strftime('%Y-%m-%d'))
    return redirect('/login')

@app.route('/completed')
def completed_tasks():
    if "user" in session:
        username = session['user']
        tasks = tasks_collection.find({"username": username, "completed": True})
        tasks_list = list(tasks)
        return render_template('index.html', tasks=tasks_list, filter='completed', current_date=datetime.now().strftime('%Y-%m-%d'))
    return redirect('/login')

@app.route('/overdue')
def overdue_tasks():
    if "user" in session:
        username = session['user']
        today = datetime.now().strftime('%Y-%m-%d')
        tasks = tasks_collection.find({
            "username": username,
            "completed": False,
            "due_date": {"$lt": today, "$ne": ""}
        })
        tasks_list = list(tasks)
        return render_template('index.html', tasks=tasks_list, filter='overdue', current_date=datetime.now().strftime('%Y-%m-%d'))
    return redirect('/login')

@app.route('/today')
def today_tasks():
    if "user" in session:
        username = session['user']
        today = datetime.now().strftime('%Y-%m-%d')
        tasks = tasks_collection.find({
            "username": username,
            "due_date": today
        })
        tasks_list = list(tasks)
        return render_template('index.html', tasks=tasks_list, filter='today', current_date=today)
    return redirect('/login')

@app.route('/upcoming')
def upcoming_tasks():
    if "user" in session:
        username = session['user']
        today = datetime.now().strftime('%Y-%m-%d')
        tomorrow = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
        week_later = (datetime.now() + timedelta(days=7)).strftime('%Y-%m-%d')
        
        tasks = tasks_collection.find({
            "username": username,
            "completed": False,
            "due_date": {"$gt": today, "$lte": week_later}
        })
        tasks_list = list(tasks)
        return render_template('index.html', tasks=tasks_list, filter='upcoming', current_date=today)
    return redirect('/login')

@app.route('/mark-pending/<task_id>')
def mark_pending(task_id):
    if "user" in session:
        tasks_collection.update_one({"_id": ObjectId(task_id)}, {"$set": {"completed": False}})
        return redirect('/tasks')
    return redirect('/login')

@app.route('/add', methods=['POST'])
def add_task():
    if "user" in session:
        username = session['user']
        task = request.form.get('task')
        priority = request.form.get('priority')
        due_date = request.form.get('due_date')
        description = request.form.get('description', '')

        if task:
            tasks_collection.insert_one({
                "username": username,
                "task": task,
                "completed": False,
                "priority": priority,
                "due_date": due_date,
                "description": description,
                "created_at": datetime.now().strftime('%Y-%m-%d')
            })
        return redirect('/tasks')
    return redirect('/login')

@app.route('/delete/<task_id>')
def delete_task(task_id):
    if "user" in session:
        tasks_collection.delete_one({"_id": ObjectId(task_id)})
        return redirect('/tasks')
    return redirect('/login')

@app.route('/complete/<task_id>')
def complete_task(task_id):
    if "user" in session:
        tasks_collection.update_one({"_id": ObjectId(task_id)}, {"$set": {"completed": True}})
        return redirect('/tasks')
    return redirect('/login')

@app.route('/edit/<task_id>', methods=['GET', 'POST'])
def edit_task(task_id):
    if "user" in session:
        task = tasks_collection.find_one({"_id": ObjectId(task_id)})

        if request.method == 'POST':
            updated_task = request.form.get('task')
            updated_priority = request.form.get('priority')
            updated_due_date = request.form.get('due_date')
            updated_description = request.form.get('description')
            completed_status = True if request.form.get('completed') == 'on' else False

            tasks_collection.update_one(
                {"_id": ObjectId(task_id)},
                {"$set": {
                    "task": updated_task,
                    "priority": updated_priority,
                    "due_date": updated_due_date,
                    "description": updated_description,
                    "completed": completed_status
                }}
            )
            return redirect('/tasks')

        return render_template('edit.html', task=task)
    
    return redirect('/login')

if __name__ == '__main__':
    app.run(debug=True)