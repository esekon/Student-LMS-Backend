from flask import Flask, render_template
from flask_login import LoginManager
from clerk import Clerk
from models import db, User

app = Flask(__name__)
app.secret_key = '53d2709f06191d182a5320ecc6c244acebb74d5ad00efb94922a3dc15b8309ba'  # Change this to a long random string

# Configure database URI (SQLite)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)

# Initialize Clerk
clerk = Clerk(app)

# Initialize database
db.init_app(app)

# Import routes and models
from routes import auth_routes

# Register blueprints
app.register_blueprint(auth_routes)

# Define user loader function for Flask-Login
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

if __name__ == '__main__':
    app.run(debug=True)
