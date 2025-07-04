from flask import Flask, render_template, request, redirect, url_for, flash, session
import sqlite3
import psycopg
from datetime import datetime, timedelta
import os
from urllib.parse import urlparse
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
import secrets
from collections import Counter

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')

# Database configuration - support both SQLite (local) and PostgreSQL (production)
DATABASE_URL = os.environ.get('DATABASE_URL')

def get_db_connection():
    """Get database connection - PostgreSQL in production, SQLite locally"""
    if DATABASE_URL:
        # Production - PostgreSQL with psycopg3
        return psycopg.connect(DATABASE_URL)
    else:
        # Local development - SQLite  
        return sqlite3.connect('clinic.db')

def init_db():
    """Initialize the database with required tables"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    if DATABASE_URL:
        # PostgreSQL syntax
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS patients (
                id SERIAL PRIMARY KEY,
                first_name VARCHAR(100) NOT NULL,
                last_name VARCHAR(100) NOT NULL,
                date_of_birth DATE NOT NULL,
                therapist_name VARCHAR(100) NOT NULL,
                therapist_id INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (therapist_id) REFERENCES therapists (id)
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS therapists (
                id SERIAL PRIMARY KEY,
                username VARCHAR(50) UNIQUE NOT NULL,
                email VARCHAR(100) UNIQUE NOT NULL,
                password_hash VARCHAR(255) NOT NULL,
                full_name VARCHAR(100) NOT NULL,
                is_active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
    else:
        # SQLite syntax
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS patients (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                first_name TEXT NOT NULL,
                last_name TEXT NOT NULL,
                date_of_birth DATE NOT NULL,
                therapist_name TEXT NOT NULL,
                therapist_id INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (therapist_id) REFERENCES therapists (id)
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS therapists (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                full_name TEXT NOT NULL,
                is_active BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
    
    conn.commit()
    
    # Create a default admin therapist if none exists
    cursor.execute('SELECT COUNT(*) FROM therapists')
    if DATABASE_URL:
        count = cursor.fetchone()[0]
    else:
        count = cursor.fetchone()[0]
    
    if count == 0:
        # Create default admin account
        admin_password = generate_password_hash('admin123')  # Change this in production!
        if DATABASE_URL:
            cursor.execute('''
                INSERT INTO therapists (username, email, password_hash, full_name)
                VALUES (%s, %s, %s, %s)
            ''', ('admin', 'admin@clinic.com', admin_password, 'Administrator'))
        else:
            cursor.execute('''
                INSERT INTO therapists (username, email, password_hash, full_name)
                VALUES (?, ?, ?, ?)
            ''', ('admin', 'admin@clinic.com', admin_password, 'Administrator'))
        
        conn.commit()
    
    conn.close()

def login_required(f):
    """Decorator to require login for certain routes"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'therapist_id' not in session:
            flash('Please log in to access this page.', 'error')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def get_current_therapist():
    """Get current logged-in therapist info"""
    if 'therapist_id' not in session:
        return None
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT id, username, email, full_name FROM therapists WHERE id = %s
    ''' if DATABASE_URL else '''
        SELECT id, username, email, full_name FROM therapists WHERE id = ?
    ''', (session['therapist_id'],))
    
    therapist = cursor.fetchone()
    conn.close()
    
    if therapist:
        return {
            'id': therapist[0],
            'username': therapist[1],
            'email': therapist[2],
            'full_name': therapist[3]
        }
    return None

def validate_form_data(data):
    """Validate form data and return errors if any"""
    errors = []
    
    # Check for empty fields
    if not data.get('first_name', '').strip():
        errors.append('First name is required')
    
    if not data.get('last_name', '').strip():
        errors.append('Last name is required')
    
    if not data.get('therapist_name', '').strip():
        errors.append('Therapist name is required')
    
    # Validate date of birth
    dob = data.get('date_of_birth', '').strip()
    if not dob:
        errors.append('Date of birth is required')
    else:
        try:
            birth_date = datetime.strptime(dob, '%Y-%m-%d')
            if birth_date.date() >= datetime.now().date():
                errors.append('Date of birth must be in the past')
        except ValueError:
            errors.append('Invalid date format')
    
    return errors

def format_datetime(dt):
    """Format datetime for display"""
    if isinstance(dt, str):
        try:
            # Try to parse if it's a string
            dt = datetime.fromisoformat(dt.replace('Z', '+00:00'))
        except:
            return dt

    if hasattr(dt, 'strftime'):
        return dt.strftime('%Y-%m-%d %H:%M')
    return str(dt)

def is_admin(therapist):
    # Adjust this logic if you use a different admin check
    return therapist.get('username', '') == 'admin'

# Authentication Routes
@app.route('/login')
def login():
    """Display login form"""
    return render_template('login.html')

@app.route('/login', methods=['POST'])
def login_post():
    """Process login form"""
    username = request.form.get('username', '').strip()
    password = request.form.get('password', '')
    
    if not username or not password:
        flash('Please enter both username and password.', 'error')
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT id, password_hash, full_name, is_active FROM therapists 
        WHERE username = %s
    ''' if DATABASE_URL else '''
        SELECT id, password_hash, full_name, is_active FROM therapists 
        WHERE username = ?
    ''', (username,))
    
    therapist = cursor.fetchone()
    conn.close()
    
    if therapist and check_password_hash(therapist[1], password):
        if not therapist[3]:  # Check if account is active
            flash('Your account has been deactivated. Please contact an administrator.', 'error')
            return redirect(url_for('login'))
        
        # Login successful
        session['therapist_id'] = therapist[0]
        session['therapist_name'] = therapist[2]
        flash(f'Welcome back, {therapist[2]}!', 'success')
        return redirect(url_for('dashboard'))
    else:
        flash('Invalid username or password.', 'error')
        return redirect(url_for('login'))

@app.route('/logout')
def logout():
    """Log out the current user"""
    session.clear()
    flash('You have been logged out successfully.', 'success')
    return redirect(url_for('index'))

@app.route('/dashboard')
@login_required
def dashboard():
    """Therapist dashboard showing their patients"""
    therapist = get_current_therapist()
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    if is_admin(therapist):
        # Admin: see all therapists and patients
        cursor.execute('SELECT id, username, full_name, email, is_active, created_at FROM therapists')
        therapists = cursor.fetchall()
        cursor.execute('SELECT id, first_name, last_name, date_of_birth, therapist_id, created_at FROM patients')
        patients = cursor.fetchall()
    else:
        # Regular therapist: see only their patients
        cursor.execute('SELECT id, first_name, last_name, date_of_birth, therapist_id, created_at FROM patients WHERE therapist_id = %s' if DATABASE_URL else 'SELECT id, first_name, last_name, date_of_birth, therapist_id, created_at FROM patients WHERE therapist_id = ?', (therapist['id'],))
        patients = cursor.fetchall()
        therapists = []

    # --- Analytics: Weekly and Monthly patient registrations ---
    patient_dates = [p[5] for p in patients if p[5]]
    # Parse dates
    parsed_dates = []
    for d in patient_dates:
        if isinstance(d, str):
            try:
                parsed_dates.append(datetime.fromisoformat(d.replace('Z', '+00:00')))
            except Exception:
                continue
        else:
            parsed_dates.append(d)
    # Weekly
    week_labels = []
    week_counts = []
    if parsed_dates:
        min_date = min(parsed_dates)
        max_date = max(parsed_dates)
        current = min_date - timedelta(days=min_date.weekday())
        while current <= max_date:
            label = current.strftime('Week of %Y-%m-%d')
            week_labels.append(label)
            count = sum(1 for d in parsed_dates if current <= d < current + timedelta(days=7))
            week_counts.append(count)
            current += timedelta(days=7)
    # Monthly
    month_labels = []
    month_counts = []
    if parsed_dates:
        months = sorted(set((d.year, d.month) for d in parsed_dates))
        for y, m in months:
            label = f"{y}-{m:02d}"
            month_labels.append(label)
            count = sum(1 for d in parsed_dates if d.year == y and d.month == m)
            month_counts.append(count)

    conn.close()
    return render_template(
        'dashboard.html',
        therapist=therapist,
        therapists=therapists,
        patients=patients,
        weekly_labels=week_labels,
        weekly_counts=week_counts,
        monthly_labels=month_labels,
        monthly_counts=month_counts,
        format_datetime=format_datetime
    )

# Patient Registration Routes
@app.route('/')
def index():
    """Display the patient form"""
    # Check if therapist is logged in to pre-fill therapist name
    therapist = get_current_therapist()
    return render_template('index.html', current_therapist=therapist)

@app.route('/submit', methods=['POST'])
def submit():
    """Process form submission and store in database"""
    # Validate form data
    errors = validate_form_data(request.form)
    
    if errors:
        for error in errors:
            flash(error, 'error')
        return redirect(url_for('index'))
    
    # Extract and clean form data
    first_name = request.form['first_name'].strip()
    last_name = request.form['last_name'].strip()
    date_of_birth = request.form['date_of_birth'].strip()
    therapist_name = request.form['therapist_name'].strip()
    
    # Get therapist_id if logged in
    therapist_id = session.get('therapist_id')
    
    try:
        # Store in database
        conn = get_db_connection()
        cursor = conn.cursor()
        
        if DATABASE_URL:
            # PostgreSQL - use RETURNING to get the ID
            cursor.execute('''
                INSERT INTO patients (first_name, last_name, date_of_birth, therapist_name, therapist_id)
                VALUES (%s, %s, %s, %s, %s) RETURNING id
            ''', (first_name, last_name, date_of_birth, therapist_name, therapist_id))
            patient_id = cursor.fetchone()[0]
        else:
            # SQLite - use lastrowid
            cursor.execute('''
                INSERT INTO patients (first_name, last_name, date_of_birth, therapist_name, therapist_id)
                VALUES (?, ?, ?, ?, ?)
            ''', (first_name, last_name, date_of_birth, therapist_name, therapist_id))
            patient_id = cursor.lastrowid
            
        conn.commit()
        conn.close()
        
        # Redirect based on whether therapist is logged in
        if therapist_id:
            flash('Patient registered successfully!', 'success')
            return redirect(url_for('dashboard'))
        else:
            return redirect(url_for('confirmation', patient_id=patient_id))
        
    except Exception as e:
        print(f"Database error: {e}")
        flash('An error occurred while saving the patient information', 'error')
        return redirect(url_for('index'))

@app.route('/confirmation/<int:patient_id>')
def confirmation(patient_id):
    """Display confirmation page with patient information"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT first_name, last_name, date_of_birth, therapist_name, created_at
            FROM patients WHERE id = %s
        ''' if DATABASE_URL else '''
            SELECT first_name, last_name, date_of_birth, therapist_name, created_at
            FROM patients WHERE id = ?
        ''', (patient_id,))
        
        patient = cursor.fetchone()
        conn.close()
        
        if not patient:
            flash('Patient not found', 'error')
            return redirect(url_for('index'))
        
        patient_data = {
            'first_name': patient[0],
            'last_name': patient[1],
            'date_of_birth': patient[2],
            'therapist_name': patient[3],
            'created_at': patient[4]
        }
        
        return render_template('confirmation.html', patient=patient_data)
        
    except Exception as e:
        print(f"Confirmation error: {e}")
        flash('An error occurred while retrieving patient information', 'error')
        return redirect(url_for('index'))

# Admin Routes (for creating new therapists)
@app.route('/register-therapist')
@login_required
def register_therapist():
    """Display therapist registration form (admin only for now)"""
    return render_template('register_therapist.html')

@app.route('/register-therapist', methods=['POST'])
@login_required
def register_therapist_post():
    """Process therapist registration"""
    username = request.form.get('username', '').strip()
    email = request.form.get('email', '').strip()
    full_name = request.form.get('full_name', '').strip()
    password = request.form.get('password', '')
    confirm_password = request.form.get('confirm_password', '')
    
    # Validation
    errors = []
    if not username:
        errors.append('Username is required')
    if not email:
        errors.append('Email is required')
    if not full_name:
        errors.append('Full name is required')
    if not password:
        errors.append('Password is required')
    if password != confirm_password:
        errors.append('Passwords do not match')
    if len(password) < 6:
        errors.append('Password must be at least 6 characters long')
    
    if errors:
        for error in errors:
            flash(error, 'error')
        return redirect(url_for('register_therapist'))
    
    # Check if username or email already exists
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT COUNT(*) FROM therapists WHERE username = %s OR email = %s
    ''' if DATABASE_URL else '''
        SELECT COUNT(*) FROM therapists WHERE username = ? OR email = ?
    ''', (username, email))
    
    if cursor.fetchone()[0] > 0:
        flash('Username or email already exists', 'error')
        conn.close()
        return redirect(url_for('register_therapist'))
    
    # Create new therapist
    password_hash = generate_password_hash(password)
    
    try:
        if DATABASE_URL:
            cursor.execute('''
                INSERT INTO therapists (username, email, password_hash, full_name)
                VALUES (%s, %s, %s, %s)
            ''', (username, email, password_hash, full_name))
        else:
            cursor.execute('''
                INSERT INTO therapists (username, email, password_hash, full_name)
                VALUES (?, ?, ?, ?)
            ''', (username, email, password_hash, full_name))
        
        conn.commit()
        conn.close()
        
        flash(f'Therapist {full_name} registered successfully!', 'success')
        return redirect(url_for('dashboard'))
        
    except Exception as e:
        print(f"Registration error: {e}")
        flash('An error occurred while registering the therapist', 'error')
        conn.close()
        return redirect(url_for('register_therapist'))

@app.route('/delete_therapist/<int:therapist_id>', methods=['POST'])
@login_required
def delete_therapist(therapist_id):
    therapist = get_current_therapist()
    if not is_admin(therapist):
        flash('Unauthorized', 'error')
        return redirect(url_for('dashboard'))
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM therapists WHERE id = %s' if DATABASE_URL else 'DELETE FROM therapists WHERE id = ?', (therapist_id,))
    conn.commit()
    conn.close()
    flash('Therapist deleted.', 'success')
    return redirect(url_for('dashboard'))

@app.route('/delete_patient/<int:patient_id>', methods=['POST'])
@login_required
def delete_patient(patient_id):
    therapist = get_current_therapist()
    if not is_admin(therapist):
        flash('Unauthorized', 'error')
        return redirect(url_for('dashboard'))
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM patients WHERE id = %s' if DATABASE_URL else 'DELETE FROM patients WHERE id = ?', (patient_id,))
    conn.commit()
    conn.close()
    flash('Patient deleted.', 'success')
    return redirect(url_for('dashboard'))

# Simple confirmation route without ID for testing
@app.route('/confirmation')
def confirmation_simple():
    """Simple confirmation page for testing"""
    return render_template('confirmation.html', patient=None)

# Initialize database on app startup
init_db()

if __name__ == '__main__':
    # Configure for production deployment
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_ENV') != 'production'
    
    app.run(host='0.0.0.0', port=port, debug=debug)