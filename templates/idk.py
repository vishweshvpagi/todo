import bcrypt
from pymongo import MongoClient

client = MongoClient("mongodb://localhost:27017/")
db = client.todo_db  
users_collection = db.users  

# Clear previous users (optional)
users_collection.delete_many({})

# User credentials
username = "admin"
password = "password123"

# Hash password
hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

# Store in MongoDB
users_collection.insert_one({
    "username": username,
    "password": hashed_password.decode('utf-8')  # Store as a string
})

print("Admin user created successfully!")
