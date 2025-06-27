# Pediatric Therapy Clinic - Patient Registration App

A simple Flask application for registering patients at a pediatric therapy clinic.

## Project Structure
```
clinic-app/
├── app.py              # Main Flask application
├── requirements.txt    # Python dependencies
├── README.md          # This file
├── templates/
│   ├── index.html     # Patient registration form
│   └── confirmation.html  # Confirmation page
└── static/
    └── style.css      # Stylesheet
```

## Installation & Setup

1. **Clone/Download the project**
2. **Create a virtual environment:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```
3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```
4. **Run the application:**
   ```bash
   python app.py
   ```
5. **Open your browser and go to:** `http://127.0.0.1:5000`

## Features

- Patient registration form with validation
- SQLite database storage
- Confirmation page showing registered patient details
- Responsive web design
- Form validation (required fields, past date validation)

## Database

The app automatically creates a SQLite database (`clinic.db`) with the following schema:

```sql
CREATE TABLE patients (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    first_name TEXT NOT NULL,
    last_name TEXT NOT NULL,
    date_of_birth DATE NOT NULL,
    therapist_name TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

---

## Add-On Questions - Responses

### 1. Form Validation Handling

**How the app handles form validation:**

The app implements both client-side and server-side validation:

- **Client-side**: HTML5 `required` attributes and `type="date"` provide immediate feedback
- **Server-side**: The `validate_form_data()` function checks for:
  - Empty/missing required fields (first name, last name, therapist name, date of birth)
  - Invalid date format
  - Future dates (date of birth must be in the past)

**What happens when validation fails:**
- Validation errors are collected in a list
- Flash messages display specific error messages to the user
- User is redirected back to the form with their previously entered data preserved
- Form shows visual indicators (red border for required fields, green for valid)

### 2. Extending for Therapist Logins

**Structure for therapist authentication:**

```python
# Additional database tables needed:
CREATE TABLE therapists (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    full_name TEXT NOT NULL,
    is_active BOOLEAN DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE therapist_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    therapist_id INTEGER,
    session_token TEXT UNIQUE NOT NULL,
    expires_at TIMESTAMP NOT NULL,
    FOREIGN KEY (therapist_id) REFERENCES therapists (id)
);
```

**Implementation approach:**
- Add Flask-Login for session management
- Create login/logout routes with password hashing (bcrypt)
- Add `@login_required` decorator to protect routes
- Pre-populate therapist name from logged-in user
- Add therapist dashboard showing their patients
- Implement role-based access (admin vs therapist)

### 3. HIPAA-Compliant Cloud Deployment

**Key considerations for HIPAA compliance:**

**Infrastructure:**
- Use AWS/Azure/GCP with BAA (Business Associate Agreement)
- Deploy in HIPAA-eligible regions
- Use encrypted storage (EBS encryption, encrypted RDS)
- Implement VPC with private subnets

**Security measures:**
- SSL/TLS encryption in transit (HTTPS only)
- Database encryption at rest
- Secure environment variables for secrets
- Regular security patches and updates
- Access logging and monitoring

**Deployment architecture:**
```
Internet → Load Balancer (SSL) → Private Subnet → App Servers
                                        ↓
                              Private RDS Database (encrypted)
```

**Specific steps:**
1. Use Docker containers with minimal base images
2. Deploy to ECS/EKS with encryption enabled
3. Use RDS PostgreSQL with encryption at rest
4. Implement WAF for additional security
5. Set up CloudTrail for audit logging
6. Regular automated backups with encryption

### 4. Database Initialization Placement

**Current placement: `init_db()` function called in `if __name__ == '__main__':`**

**Why this placement:**
- Ensures database is created before the app starts accepting requests
- Only runs when the script is executed directly (not imported)
- Simple and appropriate for development/small deployments

**Alternative approaches for production:**
- **Separate migration script**: Create `init_db.py` for one-time setup
- **Flask CLI command**: Use `@app.cli.command()` decorator
- **Application factory pattern**: Move to `create_app()` function
- **Database migrations**: Use Alembic for version-controlled schema changes

**Production recommendation:**
```python
# migrations/init_db.py
def init_database():
    """Run this once during deployment"""
    # Database initialization code here
    pass

# Then in app.py, check if tables exist before creating
def ensure_tables():
    """Ensure tables exist, but don't recreate if they do"""
    # More robust approach for production
```

This placement ensures proper database setup while maintaining flexibility for different deployment scenarios.