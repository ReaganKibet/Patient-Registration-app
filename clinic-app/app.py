from flask import Flask, render_template, request, redirect, url_for, flash
import sqlite3
from datetime import datetime
import os

app = Flask('Patient Registration App')
app.secret_key = 'your-secret-key-change-in-production'

# Database configuration
DATABASE = 'clinic.db'

def init_db():
    """Initialize the database with required tables"""
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
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
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO patients (first_name, last_name, date_of_birth, therapist_name)
            VALUES (?, ?, ?, ?)
        ''', (first_name, last_name, date_of_birth, therapist_name))
        
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
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        
        cursor.execute('''
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
    app.run(debug=True)