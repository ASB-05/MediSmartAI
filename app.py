from flask import Flask, request, jsonify, render_template, redirect, url_for
from flask_cors import CORS
from pymongo import MongoClient
from fpdf import FPDF
from flask_mail import Mail, Message
import os
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from bson.objectid import ObjectId
from datetime import datetime
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.tree import DecisionTreeClassifier
from sklearn.preprocessing import LabelEncoder
import numpy as np
from dotenv import load_dotenv
import openai

load_dotenv() # <-- ADD THIS LINE TO LOAD THE .env FILE
from ai_models import (
    get_schedule_suggestions,
    get_symptom_recommendation_openai,
    get_diet_recommendation_openai
)

# --- Initialization ---

# Define the base directory of the current script.
# This makes path resolution robust, regardless of the current working directory.
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Initialize Flask app, explicitly telling it where to find templates and static files
# relative to the BASE_DIR.
app = Flask(__name__,
            template_folder=os.path.join(BASE_DIR, 'templates'),
            static_folder=os.path.join(BASE_DIR, 'static'))

# ---vvv--- ENHANCED DEBUGGING CODE ---vvv---
# This section helps verify that Flask is looking for files in the correct place.
# It's good practice to keep this during development.
current_working_directory = BASE_DIR # Use BASE_DIR for reliable path reporting
template_folder_path = os.path.join(current_working_directory, 'templates') # Use 'templates' relative to BASE_DIR
print(f"\n--- DEBUG INFO ---")
print(f"-> Your script is running from this base directory:")
print(f"   '{current_working_directory}'")
print(f"-> Flask is configured to look for the 'templates' folder at this absolute path:")
print(f"   '{os.path.abspath(template_folder_path)}'")
print(f"-> Does this 'templates' folder actually exist? -> {'YES' if os.path.isdir(template_folder_path) else '!!! NO !!!'}")

# This part lists the files inside the 'templates' folder to confirm their presence
if os.path.isdir(template_folder_path):
    print(f"-> Here are the files found inside your 'templates' folder:")
    files_in_templates = os.listdir(template_folder_path)
    if not files_in_templates:
        print("   '!!! YOUR TEMPLATES FOLDER IS EMPTY !!!'")
    else:
        for filename in files_in_templates:
            print(f"   - {filename}")
else:
    print(f"!!! WARNING: The 'templates' folder was not found at '{os.path.abspath(template_folder_path)}' !!!")

print(f"--- END DEBUG INFO ---\n")
# ---^^^--- END OF OF DEBUGGING CODE ---^^^---

app.config['SECRET_KEY'] = os.urandom(24)
CORS(app)

# --- Flask-Mail Configuration ---
# Ensure these environment variables are set in your system or .env file
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = os.environ.get('MAIL_USERNAME')
app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD')
app.config['MAIL_DEFAULT_SENDER'] = os.environ.get('MAIL_USERNAME')

# ---vvv--- ADD THIS DEBUGGING CODE ---vvv---
print("--- MAIL DEBUG INFO ---")
print(f"MAIL_USERNAME is: {app.config.get('MAIL_USERNAME')}")
# This next line is just to check IF the password was found, not to show it.
# If it shows 'None', the variable was not found.
if app.config.get('MAIL_PASSWORD'):
    print("MAIL_PASSWORD is: SET")
else:
    print("MAIL_PASSWORD is: !!! NOT SET / NOT FOUND !!!")
print("------------------------")
# ---^^^--- END OF DEBUGGING CODE ---^^^---

mail = Mail(app)

app.config['SECRET_KEY'] = os.urandom(24)
CORS(app)

# --- MongoDB Configuration ---
# Ensure MongoDB is running and accessible at this address
client = MongoClient('mongodb://localhost:27017/')
db = client['medismart_db']
users_collection = db['users']
doctors_collection = db['doctors']
appointments_collection = db['appointments']
contacts_collection = db['contacts']
consultations_collection = db['consultations']


# --- Flask-Login Configuration ---
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login' # Redirects unauthenticated users to the login page

class User(UserMixin):
    def __init__(self, user_data):
        self.id = str(user_data['_id'])
        self.email = user_data['email']
        self.name = user_data['name']
        self.role = user_data['role']

@login_manager.user_loader
def load_user(user_id):
    """Loads a user from the database given their ID."""
    user_data = users_collection.find_one({'_id': ObjectId(user_id)})
    return User(user_data) if user_data else None

# --- AI Models ---
# These models are simple examples. In a real application, they would be
# trained on much larger datasets and potentially loaded from saved files.

# Scheduler Model (Logistic Regression for optimal slot prediction)
scheduler_data = {
    'hour': [9, 10, 11, 12, 13, 14, 15, 16, 9, 10, 11, 12, 13, 14, 15, 16],
    'is_booked': [1, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 1, 0, 1, 0],
    'is_optimal': [1, 1, 1, 0, 0, 0, 0, 0, 1, 1, 1, 0, 0, 0, 0, 0]
}
scheduler_df = pd.DataFrame(scheduler_data)
X_scheduler = scheduler_df[['hour', 'is_booked']]
y_scheduler = scheduler_df['is_optimal']
scheduler_model = LogisticRegression()
scheduler_model.fit(X_scheduler, y_scheduler)

# Diet Recommendation Model (Decision Tree Classifier)
diet_data = {
    'disease': ['Diabetes', 'Hypertension', 'Obesity', 'Fever', 'Cold'],
    'diet': ['Low Carb Diet', 'Low Sodium Diet', 'Low Calorie Diet', 'Fluid-Rich Diet', 'Vitamin C Rich Diet']
}
diet_df = pd.DataFrame(diet_data)
le = LabelEncoder() # Used to encode categorical 'disease' into numerical format
diet_df['disease_encoded'] = le.fit_transform(diet_df['disease'])
X_diet = diet_df[['disease_encoded']]
y_diet = diet_df['diet']
diet_model = DecisionTreeClassifier()
diet_model.fit(X_diet, y_diet)

# --- PDF & Email Helper Functions ---
def create_appointment_pdf(appointment_data):
    """Generates a PDF confirmation for an appointment."""
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(0, 10, 'MediSmart AI - Appointment Confirmation', 0, 1, 'C')
    pdf.ln(10)
    pdf.set_font("Arial", '', 12)
    pdf.cell(0, 8, f"Patient: {appointment_data['patientName']}", 0, 1)
    pdf.cell(0, 8, f"Doctor: {appointment_data['doctorName']}", 0, 1)
    pdf.cell(0, 8, f"Date: {appointment_data['date']}", 0, 1)
    pdf.cell(0, 8, f"Time: {appointment_data['time']}", 0, 1)
    pdf.cell(0, 8, f"Type: {appointment_data['appointmentType']}", 0, 1)
    pdf.ln(5)
    pdf.multi_cell(0, 8, f"Notes: {appointment_data.get('additionalNotes', 'N/A')}")
    
    # Create a unique filename for the PDF
    pdf_file_path = os.path.join(BASE_DIR, f"appointment_{appointment_data['_id']}.pdf")
    pdf.output(pdf_file_path)
    return pdf_file_path

def send_appointment_email(recipient_email, attachment_path):
    """Sends an email with the appointment PDF attached."""
    try:
        msg = Message("Your MediSmart AI Appointment Confirmation", recipients=[recipient_email])
        msg.body = "Dear Patient,\n\nPlease find your appointment details attached.\n\nThank you for choosing MediSmart AI."
        with app.open_resource(attachment_path) as fp:
            msg.attach(os.path.basename(attachment_path), "application/pdf", fp.read())
        mail.send(msg)
        return True
    except Exception as e:
        print(f"Error sending email: {e}")
        return False

# --- Main Page Routes ---
# These routes render the main HTML pages of the application.
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/doctors')
def doctors_page():
    return render_template('doctor.html')

@app.route('/appointments')
@login_required # Requires user to be logged in
def appointments_page():
    return render_template('appointment.html')

@app.route('/consult-online')
@login_required
def consult_online_page():
    return render_template('consultOnline.html')

@app.route('/contact')
def contact_page():
    return render_template('contact.html')

@app.route('/elder-ai')
def elder_ai_page():
    return render_template('elderAI.html')

@app.route('/nutri-ai')
@login_required
def nutri_ai_page():
    # This is the route that was causing the error.
    # With the BASE_DIR fix, it should now correctly find 'nutriAI.html'.
    return render_template('nutriAI.html')
    
# --- User Authentication Routes ---
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        password = request.form.get('password')
        role = request.form.get('role')
        
        # Check if user already exists
        user_exists = users_collection.find_one({'email': email})
        if user_exists:
            # Optionally, add a flash message here to inform the user
            return redirect(url_for('signup')) 
        
        # Hash password for security
        hashed_password = generate_password_hash(password, method='pbkdf2:sha256')
        users_collection.insert_one({'name': name, 'email': email, 'password': hashed_password, 'role': role})
        return redirect(url_for('login'))
    return render_template('signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        user_data = users_collection.find_one({'email': email})
        
        # Verify password
        if user_data and check_password_hash(user_data['password'], password):
            user = User(user_data)
            login_user(user) # Log the user in
            return redirect(url_for('dashboard')) # Redirect to dashboard on successful login
        
        # Optionally, add a flash message for invalid credentials
        return redirect(url_for('login')) # Redirect back to login on failure
    return render_template('login.html')

@app.route('/logout')
@login_required # Only logged-in users can log out
def logout():
    logout_user() # Log the user out
    return redirect(url_for('index')) # Redirect to home page

@app.route('/dashboard')
@login_required
def dashboard():
    # The dashboard will display content based on the logged-in user's role
    return render_template('dashboard.html')

@app.route('/symptom-checker')
def symptom_checker():
    return render_template('symptom_checker.html')

# --- API Routes ---
# These routes handle data requests from the frontend via JavaScript.

@app.route('/api/appointments', methods=['POST'])
@login_required
def book_appointment():
    """Handles booking a new appointment."""
    try:
        data = request.get_json()
        # Add current user's details to the appointment data
        data['patientName'] = current_user.name
        data['patientEmail'] = current_user.email
        data['patientId'] = current_user.id
        
        result = appointments_collection.insert_one(data)
        appointment_id = result.inserted_id
        data['_id'] = appointment_id # Add the generated ID back to data for PDF creation
        
        pdf_path = create_appointment_pdf(data)
        email_sent = send_appointment_email(data['patientEmail'], pdf_path)
        
        # Clean up the generated PDF file after sending the email
        if os.path.exists(pdf_path):
            os.remove(pdf_path)
            
        if email_sent:
            return jsonify({'message': 'Appointment booked! A confirmation has been sent to your email.'}), 201
        else:
            return jsonify({'message': 'Appointment booked, but the confirmation email could not be sent.'}), 207 # Partial success
    except Exception as e:
        print(f"Error booking appointment: {e}") # Log the error for debugging
        return jsonify({'error': str(e)}), 400

@app.route('/api/my-appointments')
@login_required
def my_appointments():
    """Fetches appointments for the logged-in user (patient or doctor)."""
    # Query based on user role
    if current_user.role == 'Patient':
        query = {'patientId': current_user.id}
    elif current_user.role == 'Doctor':
        query = {'doctorName': current_user.name} # Assuming doctor's name is unique or sufficient
    else:
        return jsonify({'error': 'Invalid user role'}), 403

    # Convert ObjectId to string for JSON serialization
    appointments = [{**app_data, '_id': str(app_data['_id'])} for app_data in appointments_collection.find(query)]
    return jsonify(appointments)

@app.route('/api/appointments/<appointment_id>/cancel', methods=['POST'])
@login_required
def cancel_appointment(appointment_id):
    """Allows a user to cancel their appointment."""
    try:
        appointment = appointments_collection.find_one({'_id': ObjectId(appointment_id)})
        
        # Ensure the user is authorized to cancel this appointment
        if appointment and (appointment.get('patientId') == current_user.id or appointment.get('doctorName') == current_user.name):
            appointments_collection.delete_one({'_id': ObjectId(appointment_id)})
            return jsonify({'message': 'Appointment cancelled successfully'}), 200
        
        return jsonify({'error': 'Unauthorized or Appointment not found'}), 403
    except Exception as e:
        print(f"Error cancelling appointment: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/schedule-suggestions', methods=['POST'])
@login_required
def schedule_suggestions_api():
    data = request.get_json()
    doctor_name = data.get('doctorName')
    selected_date = data.get('date')
    if not doctor_name or not selected_date:
        return jsonify({'error': 'Doctor name and date are required'}), 400
    # This still uses the scikit-learn model, which is appropriate for this task
    suggestions = get_schedule_suggestions(doctor_name, selected_date, appointments_collection)
    return jsonify(suggestions)

@app.route('/api/diet-recommendation', methods=['POST'])
@login_required
def diet_recommendation_api():
    data = request.get_json()
    disease = data.get('disease')
    user_details = data.get('healthRecords') # Get the additional details from the form
    if not disease:
        return jsonify({'error': 'Disease not provided'}), 400
    # Call the new OpenAI function
    recommendation = get_diet_recommendation_openai(disease, user_details)
    return jsonify(recommendation)

@app.route('/api/symptom-check', methods=['POST'])
def symptom_check_api():
    symptoms = request.get_json().get('symptoms', '')
    if not symptoms:
        return jsonify({'error': 'Symptoms not provided'}), 400
    # Call the new OpenAI function
    recommendation = get_symptom_recommendation_openai(symptoms)
    return jsonify(recommendation)

@app.route('/api/doctors', methods=['GET', 'POST'])
def handle_doctors():
    """Handles adding new doctors (POST) and fetching all doctors (GET)."""
    if request.method == 'POST':
        if not current_user.is_authenticated or current_user.role != 'Doctor':
             return jsonify({'error': 'Unauthorized action. Only doctors can add profiles.'}), 403
        try:
            doctors_collection.insert_one(request.get_json())
            return jsonify({'message': 'Doctor added successfully!'}), 201
        except Exception as e:
            print(f"Error adding doctor: {e}")
            return jsonify({'error': str(e)}), 400
    
    
    doctors = list(doctors_collection.find({}, {'_id': 0})) 
    return jsonify(doctors)

@app.route('/api/contact', methods=['POST'])
def handle_contact():
    """Handles submissions from the contact form."""
    try:
        data = request.get_json()
        contacts_collection.insert_one(data)
        return jsonify({'message': 'Contact form submitted successfully!'}), 201
    except Exception as e:
        print(f"Error submitting contact form: {e}")
        return jsonify({'error': str(e)}), 400

@app.route('/api/consultations', methods=['POST'])
@login_required
def handle_consultations():
    """Handles booking online consultations."""
    try:
        data = request.get_json()
        data['patientId'] = current_user.id  # Link consultation to the patient
        consultations_collection.insert_one(data)
        return jsonify({'message': 'Consultation booked successfully!'}), 201
    except Exception as e:
        print(f"Error booking consultation: {e}")
        return jsonify({'error': str(e)}), 400
    

@app.route('/api/elder/health-records', methods=['GET', 'POST'])
@login_required
def handle_health_records():
    """Handles fetching and adding health records for the logged-in user."""
    if request.method == 'POST':
        data = request.get_json()
        data['userId'] = current_user.id
        data['date'] = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
        health_records_collection.insert_one(data)
        return jsonify({'message': 'Health record added successfully!'}), 201
    
    # GET request
    records = list(health_records_collection.find({'userId': current_user.id}).sort('date', -1))
    for record in records:
        record['_id'] = str(record['_id']) # Convert ObjectId for JSON
    return jsonify(records)

@app.route('/api/elder/medications', methods=['GET', 'POST'])
@login_required
def handle_medications():
    """Handles fetching and adding medications for the logged-in user."""
    if request.method == 'POST':
        data = request.get_json()
        data['userId'] = current_user.id
        medications_collection.insert_one(data)
        return jsonify({'message': 'Medication added successfully!'}), 201
    
    # GET request
    meds = list(medications_collection.find({'userId': current_user.id}))
    for med in meds:
        med['_id'] = str(med['_id']) # Convert ObjectId for JSON
    return jsonify(meds)

@app.route('/api/elder/medications/<med_id>', methods=['DELETE'])
@login_required
def delete_medication(med_id):
    """Handles deleting a medication for the logged-in user."""
    result = medications_collection.delete_one({'_id': ObjectId(med_id), 'userId': current_user.id})
    if result.deleted_count == 1:
        return jsonify({'message': 'Medication deleted successfully!'}), 200
    return jsonify({'error': 'Medication not found or unauthorized'}), 404

if __name__ == '__main__':

    app.run(debug=True, port=5000)