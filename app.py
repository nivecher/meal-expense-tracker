from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash, check_password_hash
import os
import click

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///meals.db'
db = SQLAlchemy(app)

@app.cli.command('init-db')
def init_db_command():
    """Initialize the database."""
    db.create_all()
    click.echo('Initialized the database.')

# Initialize database on startup
with app.app_context():
    db.create_all()

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(120), nullable=False)
    expenses = db.relationship('Expense', backref='user', lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Expense(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.DateTime, nullable=False)
    amount = db.Column(db.Float, nullable=False)
    description = db.Column(db.String(200), nullable=False)
    category = db.Column(db.String(50), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/')
def index():
    if current_user.is_authenticated:
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        
        query = Expense.query.filter_by(user_id=current_user.id)
        
        if start_date:
            start = datetime.strptime(start_date, '%Y-%m-%d')
            query = query.filter(Expense.date >= start)
        
        if end_date:
            end = datetime.strptime(end_date, '%Y-%m-%d')
            query = query.filter(Expense.date <= end)
        
        expenses = query.order_by(Expense.date.desc()).all()
        total_amount = sum(expense.amount for expense in expenses)
        
        return render_template('index.html', expenses=expenses, total_amount=total_amount)
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password):
            login_user(user)
            flash('Logged in successfully!', 'success')
            return redirect(url_for('index'))
        else:
            flash('Invalid username or password', 'danger')
    
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Logged out successfully!', 'success')
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        if User.query.filter_by(username=username).first():
            flash('Username already exists', 'danger')
            return redirect(url_for('register'))
        
        user = User(username=username)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        
        flash('Registration successful! Please login.', 'success')
        return redirect(url_for('login'))
    
    return render_template('register.html')

@app.route('/add_expense', methods=['GET', 'POST'])
@login_required
def add_expense():
    if request.method == 'POST':
        try:
            amount = float(request.form['amount'])
            if amount <= 0:
                flash('Amount must be greater than 0', 'danger')
                return redirect(url_for('add_expense'))
                
            description = request.form['description'].strip()
            if len(description) < 3:
                flash('Description must be at least 3 characters long', 'danger')
                return redirect(url_for('add_expense'))
                
            category = request.form['category']
            if not category:
                flash('Please select a category', 'danger')
                return redirect(url_for('add_expense'))
                
            date_str = request.form['date']
            date = datetime.strptime(date_str, '%Y-%m-%d')
            today = datetime.now().date()
            min_date = today - timedelta(days=365)  # 1 year ago
            
            if date.date() > today:
                flash('Date cannot be in the future', 'danger')
                return redirect(url_for('add_expense'))
                
            if date.date() < min_date:
                flash('Date cannot be more than 1 year ago', 'danger')
                return redirect(url_for('add_expense'))
            
            expense = Expense(
                amount=amount,
                description=description,
                category=category,
                date=date,
                user_id=current_user.id
            )
            
            db.session.add(expense)
            db.session.commit()
            flash('Expense added successfully!', 'success')
            return redirect(url_for('index'))
            
        except ValueError:
            flash('Invalid input data', 'danger')
            return redirect(url_for('add_expense'))
    
    today = datetime.now().strftime('%Y-%m-%d')
    min_date = (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d')  # 1 year ago
    return render_template('add_expense.html', today=today, min_date=min_date)

@app.route('/edit_expense/<int:expense_id>', methods=['GET', 'POST'])
@login_required
def edit_expense(expense_id):
    expense = Expense.query.get_or_404(expense_id)
    
    # Ensure the expense belongs to the current user
    if expense.user_id != current_user.id:
        flash('You do not have permission to edit this expense', 'danger')
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        try:
            amount = float(request.form['amount'])
            if amount <= 0:
                flash('Amount must be greater than 0', 'danger')
                return redirect(url_for('edit_expense', expense_id=expense_id))
                
            description = request.form['description'].strip()
            if len(description) < 3:
                flash('Description must be at least 3 characters long', 'danger')
                return redirect(url_for('edit_expense', expense_id=expense_id))
                
            category = request.form['category']
            if not category:
                flash('Please select a category', 'danger')
                return redirect(url_for('edit_expense', expense_id=expense_id))
                
            date_str = request.form['date']
            date = datetime.strptime(date_str, '%Y-%m-%d')
            today = datetime.now().date()
            min_date = today - timedelta(days=365)
            
            if date.date() > today:
                flash('Date cannot be in the future', 'danger')
                return redirect(url_for('edit_expense', expense_id=expense_id))
                
            if date.date() < min_date:
                flash('Date cannot be more than 1 year ago', 'danger')
                return redirect(url_for('edit_expense', expense_id=expense_id))
            
            expense.amount = amount
            expense.description = description
            expense.category = category
            expense.date = date
            
            db.session.commit()
            flash('Expense updated successfully!', 'success')
            return redirect(url_for('index'))
            
        except ValueError:
            flash('Invalid input data', 'danger')
            return redirect(url_for('edit_expense', expense_id=expense_id))
    
    today = datetime.now().strftime('%Y-%m-%d')
    min_date = (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d')
    return render_template('edit_expense.html', expense=expense, today=today, min_date=min_date)

if __name__ == '__main__':
    app.run(debug=True) 