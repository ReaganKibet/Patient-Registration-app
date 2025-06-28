from flask import Flask, render_template, request, redirect, url_for, flash
import sqlite3
import psycopg2
from datetime import datetime
import os
from urllib.parse import urlparse

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')

# Database configuration - support both SQLite (local) and PostgreSQL (production)
DATABASE_URL = os.environ.get('DATABASE_URL')

def get_db_connection():
    """Get database connection - PostgreSQL in production, SQLite locally"""
    if DATABASE_URL:
        # Production - PostgreSQL
        return psycopg2.connect(DATABASE_URL)
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
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
    
    conn.commit()
    conn.close()

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

@app.route('/')
def index():
    """Display the patient form"""
    return render_template('index.html')

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
    
    try:
        # Store in database
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO patients (first_name, last_name, date_of_birth, therapist_name)
            VALUES (%s, %s, %s, %s)
        ''' if DATABASE_URL else '''
            INSERT INTO patients (first_name, last_name, date_of_birth, therapist_name)
            VALUES (?, ?, ?, ?)
        ''', (first_name, last_name, date_of_birth, therapist_name))
        
        if DATABASE_URL:
            patient_id = cursor.fetchone()[0] if cursor.rowcount > 0 else None
            cursor.execute('SELECT lastval()')
            patient_id = cursor.fetchone()[0]
        else:
            patient_id = cursor.lastrowid
            
        conn.commit()
        conn.close()
        
        # Redirect to confirmation page
        return redirect(url_for('confirmation', patient_id=patient_id))
        
    except Exception as e:
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
        flash('An error occurred while retrieving patient information', 'error')
        return redirect(url_for('index'))

if __name__ == '__main__':
    # Initialize database on startup
    init_db()
    
    # Configure for production deployment
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_ENV') != 'production'
    
    app.run(host='0.0.0.0', port=port, debug=debug)