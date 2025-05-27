from flask import Flask, render_template, request, redirect, url_for, flash, abort, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash, check_password_hash
import os
import click
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.urandom(24)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///meal_expenses.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['GOOGLE_MAPS_API_KEY'] = os.getenv('GOOGLE_MAPS_API_KEY')
db = SQLAlchemy(app)

class Restaurant(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    address = db.Column(db.String(200), nullable=True)
    category = db.Column(db.String(50), nullable=True)  # Now using Google Places categories
    chain = db.Column(db.String(100), nullable=True)  # New field for restaurant chain
    description = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    expenses = db.relationship('Expense', backref='restaurant', lazy=True)

    @property
    def full_name(self):
        return f"{self.name}{' - ' + self.address if self.address else ''}"

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
    category = db.Column(db.String(50), nullable=True)
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
    search = request.args.get('search', '')
    meal = request.args.get('meal', '')
    category = request.args.get('category', '')
    start_date = request.args.get('start_date', '')
    end_date = request.args.get('end_date', '')
    sort_by = request.args.get('sort', 'date')
    sort_order = request.args.get('order', 'desc')
    
    # Base query
    query = Expense.query.filter_by(user_id=current_user.id)
    
    # Apply filters
    if search:
        query = query.join(Restaurant).filter(
            db.or_(
                Restaurant.name.ilike(f'%{search}%'),
                Restaurant.address.ilike(f'%{search}%'),
                Expense.description.ilike(f'%{search}%')
            )
        )
    if meal:
        query = query.filter(Expense.meal == meal)
    if category:
        query = query.filter(Expense.category == category)
    if start_date:
        query = query.filter(Expense.date >= datetime.strptime(start_date, '%Y-%m-%d'))
    if end_date:
        query = query.filter(Expense.date <= datetime.strptime(end_date, '%Y-%m-%d'))
    
    # Apply sorting
    if sort_by == 'date':
        query = query.order_by(Expense.date.desc() if sort_order == 'desc' else Expense.date.asc())
    elif sort_by == 'amount':
        query = query.order_by(Expense.amount.desc() if sort_order == 'desc' else Expense.amount.asc())
    elif sort_by == 'meal':
        query = query.order_by(Expense.meal.desc() if sort_order == 'desc' else Expense.meal.asc())
    elif sort_by == 'category':
        query = query.order_by(Expense.category.desc() if sort_order == 'desc' else Expense.category.asc())
    elif sort_by == 'restaurant':
        query = query.join(Restaurant).order_by(
            Restaurant.name.desc() if sort_order == 'desc' else Restaurant.name.asc()
        )
    
    expenses = query.all()
    
    # Calculate total amount
    total_amount = sum(expense.amount for expense in expenses) if expenses else 0.0
    
    # Get unique meal types and categories for filter dropdowns
    meal_types = db.session.query(Expense.meal).distinct().filter(Expense.meal != '').all()
    meal_types = [meal[0] for meal in meal_types]
    categories = db.session.query(Expense.category).distinct().filter(Expense.category != '').all()
    categories = [category[0] for category in categories]
    
    return render_template('index.html', 
                         expenses=expenses,
                         search=search,
                         meal=meal,
                         category=category,
                         start_date=start_date,
                         end_date=end_date,
                         sort_by=sort_by,
                         sort_order=sort_order,
                         meal_types=meal_types,
                         categories=categories,
                         total_amount=total_amount)

@app.route('/restaurants')
@login_required
def restaurants():
    restaurants = Restaurant.query.order_by(Restaurant.name, Restaurant.address).all()
    return render_template('restaurants.html', restaurants=restaurants)

@app.route('/add_restaurant', methods=['GET', 'POST'])
@login_required
def add_restaurant():
    if request.method == 'POST':
        name = request.form['name'].strip()
        address = request.form.get('address', '').strip()
        category = request.form.get('category', '').strip()
        chain = request.form.get('chain', '').strip()
        description = request.form.get('description', '').strip()

        if not name:
            flash('Restaurant name is required', 'danger')
            return redirect(url_for('add_restaurant'))

        # Check if restaurant already exists
        existing = Restaurant.query.filter_by(name=name, address=address).first()
        if existing:
            flash('This restaurant already exists', 'danger')
            return redirect(url_for('add_restaurant'))

        restaurant = Restaurant(
            name=name,
            address=address if address else None,
            category=category if category else None,
            chain=chain if chain else None,
            description=description if description else None
        )
        db.session.add(restaurant)
        db.session.commit()
        flash('Restaurant added successfully!', 'success')
        return redirect(url_for('restaurants'))

    return render_template('add_restaurant.html', config=app.config)

@app.route('/edit_restaurant/<int:restaurant_id>', methods=['GET', 'POST'])
@login_required
def edit_restaurant(restaurant_id):
    restaurant = Restaurant.query.get_or_404(restaurant_id)
    
    if request.method == 'POST':
        name = request.form['name'].strip()
        address = request.form.get('address', '').strip()
        category = request.form.get('category', '').strip()
        chain = request.form.get('chain', '').strip()
        description = request.form.get('description', '').strip()

        if not name:
            flash('Restaurant name is required', 'danger')
            return redirect(url_for('edit_restaurant', restaurant_id=restaurant_id))

        # Check if restaurant already exists (excluding current restaurant)
        existing = Restaurant.query.filter(
            Restaurant.name == name,
            Restaurant.address == address,
            Restaurant.id != restaurant_id
        ).first()
        
        if existing:
            flash('This restaurant already exists', 'danger')
            return redirect(url_for('edit_restaurant', restaurant_id=restaurant_id))

        restaurant.name = name
        restaurant.address = address if address else None
        restaurant.category = category if category else None
        restaurant.chain = chain if chain else None
        restaurant.description = description if description else None
        
        db.session.commit()
        flash('Restaurant updated successfully!', 'success')
        return redirect(url_for('restaurants'))

    return render_template('edit_restaurant.html', restaurant=restaurant, config=app.config)

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
            category = request.form.get('category', '')
            restaurant_id = request.form.get('restaurant_id', type=int)
            
            if not restaurant_id:
                flash('Restaurant is required', 'danger')
                return redirect(url_for('add_expense'))
            
            # Get restaurant's category if no category is specified
            if not category:
                restaurant = Restaurant.query.get(restaurant_id)
                if restaurant and restaurant.category:
                    category = restaurant.category
                
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
                category=category,
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
    
    restaurants = Restaurant.query.order_by(Restaurant.name, Restaurant.address).all()
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
        expense.category = request.form['category']
        expense.restaurant_id = int(request.form['restaurant_id'])
        expense.description = request.form['description']
        
        db.session.commit()
        flash('Expense updated successfully!', 'success')
        return redirect(url_for('index'))
    
    restaurants = Restaurant.query.order_by(Restaurant.name, Restaurant.address).all()
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

@app.route('/restaurant/<int:restaurant_id>')
@login_required
def restaurant_details(restaurant_id):
    restaurant = Restaurant.query.get_or_404(restaurant_id)
    
    # Get all expenses for this restaurant
    expenses = Expense.query.filter_by(
        restaurant_id=restaurant_id,
        user_id=current_user.id
    ).order_by(Expense.date.desc()).all()
    
    # Calculate summary statistics
    total_expenses = len(expenses)
    total_amount = sum(expense.amount for expense in expenses)
    avg_amount = total_amount / total_expenses if total_expenses > 0 else 0
    
    # Group expenses by meal type
    meal_stats = {}
    for expense in expenses:
        if expense.meal not in meal_stats:
            meal_stats[expense.meal] = {'count': 0, 'amount': 0}
        meal_stats[expense.meal]['count'] += 1
        meal_stats[expense.meal]['amount'] += expense.amount
    
    return render_template('restaurant_details.html',
                         restaurant=restaurant,
                         expenses=expenses,
                         total_expenses=total_expenses,
                         total_amount=total_amount,
                         avg_amount=avg_amount,
                         meal_stats=meal_stats)

if __name__ == '__main__':
    app.run(debug=True) 