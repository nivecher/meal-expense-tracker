from flask import Flask, render_template, request, redirect, url_for, flash, abort
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

class Restaurant(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    location = db.Column(db.String(100), nullable=True)
    description = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    expenses = db.relationship('Expense', backref='restaurant', lazy=True)

    @property
    def full_name(self):
        return f"{self.name}{' - ' + self.location if self.location else ''}"

    def __repr__(self):
        return self.full_name

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
    description = db.Column(db.String(200), nullable=True)
    meal = db.Column(db.String(50), nullable=True)
    restaurant_id = db.Column(db.Integer, db.ForeignKey('restaurant.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

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

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/')
@login_required
def index():
    # Get filter parameters
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    search = request.args.get('search', '').strip()
    meal = request.args.get('meal', '')
    
    # Get sorting parameters
    sort_by = request.args.get('sort', 'date')
    sort_order = request.args.get('order', 'desc')
    
    # Build the query
    query = Expense.query.filter_by(user_id=current_user.id)
    
    # Apply date filters
    if start_date:
        query = query.filter(Expense.date >= datetime.strptime(start_date, '%Y-%m-%d').date())
    if end_date:
        query = query.filter(Expense.date <= datetime.strptime(end_date, '%Y-%m-%d').date())
    
    # Apply meal filter
    if meal:
        query = query.filter(Expense.meal == meal)
    
    # Apply search filter
    if search:
        search_term = f"%{search}%"
        query = query.join(Restaurant).filter(
            db.or_(
                Restaurant.name.ilike(search_term),
                Restaurant.location.ilike(search_term),
                Expense.description.ilike(search_term)
            )
        )
    
    # Apply sorting
    if sort_by == 'date':
        query = query.order_by(Expense.date.desc() if sort_order == 'desc' else Expense.date.asc())
    elif sort_by == 'amount':
        query = query.order_by(Expense.amount.desc() if sort_order == 'desc' else Expense.amount.asc())
    elif sort_by == 'restaurant':
        query = query.join(Restaurant).order_by(
            Restaurant.name.desc() if sort_order == 'desc' else Restaurant.name.asc()
        )
    elif sort_by == 'meal':
        query = query.order_by(Expense.meal.desc() if sort_order == 'desc' else Expense.meal.asc())
    elif sort_by == 'description':
        query = query.order_by(Expense.description.desc() if sort_order == 'desc' else Expense.description.asc())
    
    expenses = query.all()
    total_amount = sum(expense.amount for expense in expenses)
    
    return render_template('index.html', 
                         expenses=expenses, 
                         total_amount=total_amount,
                         sort_by=sort_by,
                         sort_order=sort_order)

@app.route('/restaurants')
@login_required
def restaurants():
    restaurants = Restaurant.query.order_by(Restaurant.name, Restaurant.location).all()
    return render_template('restaurants.html', restaurants=restaurants)

@app.route('/add_restaurant', methods=['GET', 'POST'])
@login_required
def add_restaurant():
    if request.method == 'POST':
        name = request.form['name'].strip()
        location = request.form.get('location', '').strip()
        description = request.form.get('description', '').strip()

        if not name:
            flash('Restaurant name is required', 'danger')
            return redirect(url_for('add_restaurant'))

        # Check if restaurant already exists
        existing = Restaurant.query.filter_by(name=name, location=location).first()
        if existing:
            flash('This restaurant location already exists', 'danger')
            return redirect(url_for('add_restaurant'))

        restaurant = Restaurant(
            name=name,
            location=location if location else None,
            description=description if description else None
        )
        db.session.add(restaurant)
        db.session.commit()
        flash('Restaurant added successfully!', 'success')
        return redirect(url_for('restaurants'))

    return render_template('add_restaurant.html')

@app.route('/edit_restaurant/<int:restaurant_id>', methods=['GET', 'POST'])
@login_required
def edit_restaurant(restaurant_id):
    restaurant = Restaurant.query.get_or_404(restaurant_id)
    
    if request.method == 'POST':
        name = request.form['name'].strip()
        location = request.form.get('location', '').strip()
        description = request.form.get('description', '').strip()

        if not name:
            flash('Restaurant name is required', 'danger')
            return redirect(url_for('edit_restaurant', restaurant_id=restaurant_id))

        # Check if the new name/location combination already exists
        existing = Restaurant.query.filter_by(name=name, location=location).first()
        if existing and existing.id != restaurant_id:
            flash('This restaurant location already exists', 'danger')
            return redirect(url_for('edit_restaurant', restaurant_id=restaurant_id))

        restaurant.name = name
        restaurant.location = location if location else None
        restaurant.description = description if description else None
        db.session.commit()
        flash('Restaurant updated successfully!', 'success')
        return redirect(url_for('restaurants'))

    return render_template('edit_restaurant.html', restaurant=restaurant)

@app.route('/add_expense', methods=['GET', 'POST'])
@login_required
def add_expense():
    if request.method == 'POST':
        try:
            amount = float(request.form['amount'])
            if amount <= 0:
                flash('Amount must be greater than 0', 'danger')
                return redirect(url_for('add_expense'))
                
            description = request.form.get('description', '').strip()
            meal = request.form.get('meal', '')
            restaurant_id = request.form.get('restaurant_id', type=int)
            
            if not restaurant_id:
                flash('Restaurant is required', 'danger')
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
                meal=meal,
                restaurant_id=restaurant_id,
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
    
    restaurants = Restaurant.query.order_by(Restaurant.name, Restaurant.location).all()
    today = datetime.now().strftime('%Y-%m-%d')
    min_date = (datetime.now() - timedelta(days=365)).strftime('%Y-%m-%d')  # 1 year ago
    return render_template('add_expense.html', today=today, min_date=min_date, restaurants=restaurants)

@app.route('/edit_expense/<int:expense_id>', methods=['GET', 'POST'])
@login_required
def edit_expense(expense_id):
    expense = Expense.query.get_or_404(expense_id)
    if expense.user_id != current_user.id:
        abort(403)
    
    if request.method == 'POST':
        expense.date = datetime.strptime(request.form['date'], '%Y-%m-%d').date()
        expense.amount = float(request.form['amount'])
        expense.meal = request.form['meal']
        expense.restaurant_id = int(request.form['restaurant_id'])
        expense.description = request.form['description']
        
        db.session.commit()
        flash('Expense updated successfully!', 'success')
        return redirect(url_for('index'))
    
    restaurants = Restaurant.query.order_by(Restaurant.name, Restaurant.location).all()
    return render_template('edit_expense.html', expense=expense, restaurants=restaurants)

@app.route('/delete_expense/<int:expense_id>', methods=['POST'])
@login_required
def delete_expense(expense_id):
    expense = Expense.query.get_or_404(expense_id)
    if expense.user_id != current_user.id:
        abort(403)
    
    db.session.delete(expense)
    db.session.commit()
    flash('Expense deleted successfully!', 'success')
    return redirect(url_for('index'))

@app.route('/delete_restaurant/<int:restaurant_id>', methods=['POST'])
@login_required
def delete_restaurant(restaurant_id):
    restaurant = Restaurant.query.get_or_404(restaurant_id)
    
    # Check if restaurant has any expenses
    if Expense.query.filter_by(restaurant_id=restaurant.id).first():
        flash('Cannot delete restaurant with existing expenses!', 'danger')
        return redirect(url_for('restaurants'))
    
    db.session.delete(restaurant)
    db.session.commit()
    flash('Restaurant deleted successfully!', 'success')
    return redirect(url_for('restaurants'))

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

if __name__ == '__main__':
    app.run(debug=True) 