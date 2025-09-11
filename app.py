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
import openai # <-- NEW: Import the OpenAI library

# --- LOAD ENVIRONMENT VARIABLES FIRST ---
# This must be the first thing you do to ensure variables are loaded
load_dotenv() 

# --- PATH & INITIALIZATION ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
app = Flask(__name__,
            template_folder=os.path.join(BASE_DIR, 'templates'),
            static_folder=os.path.join(BASE_DIR, 'static'))

# --- DEBUGGING INFO ---
current_working_directory = BASE_DIR
template_folder_path = os.path.join(current_working_directory, 'templates')
print(f"\n--- DEBUG INFO ---")
print(f"-> Your script is running from this base directory:")
print(f"   '{current_working_directory}'")
print(f"-> Flask is configured to look for the 'templates' folder at this absolute path:")
print(f"   '{os.path.abspath(template_folder_path)}'")
print(f"-> Does this 'templates' folder actually exist? -> {'YES' if os.path.isdir(template_folder_path) else '!!! NO !!!'}")
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

app.config['SECRET_KEY'] = os.urandom(24)
CORS(app)

# --- Flask-Mail Configuration ---
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = os.environ.get('MAIL_USERNAME')
app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD')
app.config['MAIL_DEFAULT_SENDER'] = os.environ.get('MAIL_USERNAME')
mail = Mail(app)

# --- OpenAI API Configuration ---
# Set the API key from the environment variable
openai.api_key = os.environ.get('OPENAI_API_KEY')

# Debugging check for the API key
print("--- OPENAI DEBUG INFO ---")
if openai.api_key:
    print("OPENAI_API_KEY is: SET")
else:
    print("OPENAI_API_KEY is: !!! NOT SET / NOT FOUND !!!")
print("------------------------")

# --- MongoDB Configuration ---
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
login_manager.login_view = 'login'

class User(UserMixin):
    def __init__(self, user_data):
        self.id = str(user_data['_id'])
        self.email = user_data['email']
        self.name = user_data['name']
        self.role = user_data['role']

@login_manager.user_loader
def load_user(user_id):
    user_data = users_collection.find_one({'_id': ObjectId(user_id)})
    return User(user_data) if user_data else None

# --- AI Models ---
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

diet_data = {
    'disease': ['Diabetes', 'Hypertension', 'Obesity', 'Fever', 'Cold'],
    'diet': ['Low Carb Diet', 'Low Sodium Diet', 'Low Calorie Diet', 'Fluid-Rich Diet', 'Vitamin C Rich Diet']
}
diet_df = pd.DataFrame(diet_data)
le = LabelEncoder()
diet_df['disease_encoded'] = le.fit_transform(diet_df['disease'])
X_diet = diet_df[['disease_encoded']]
y_diet = diet_df['diet']
diet_model = DecisionTreeClassifier()
diet_model.fit(X_diet, y_diet)

# --- PDF & Email Helper Functions ---
def create_appointment_pdf(appointment_data):
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
    pdf_file_path = os.path.join(BASE_DIR, f"appointment_{appointment_data['_id']}.pdf")
    pdf.output(pdf_file_path)
    return pdf_file_path

def send_appointment_email(recipient_email, attachment_path):
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
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/doctors')
def doctors_page():
    return render_template('doctor.html')

@app.route('/appointments')
@login_required
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
    return render_template('nutriAI.html')
    
# --- User Authentication Routes ---
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        password = request.form.get('password')
        role = request.form.get('role')
        user_exists = users_collection.find_one({'email': email})
        if user_exists:
            return redirect(url_for('signup')) 
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
        if user_data and check_password_hash(user_data['password'], password):
            user = User(user_data)
            login_user(user)
            return redirect(url_for('dashboard'))
        return redirect(url_for('login'))
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/dashboard')
@login_required
def dashboard():
    return render_template('dashboard.html')

@app.route('/symptom-checker')
def symptom_checker():
    return render_template('symptom_checker.html')

# --- API Routes ---
@app.route('/api/appointments', methods=['POST'])
@login_required
def book_appointment():
    try:
        data = request.get_json()
        data['patientName'] = current_user.name
        data['patientEmail'] = current_user.email
        data['patientId'] = current_user.id
        result = appointments_collection.insert_one(data)
        appointment_id = result.inserted_id
        data['_id'] = appointment_id
        pdf_path = create_appointment_pdf(data)
        email_sent = send_appointment_email(data['patientEmail'], pdf_path)
        if os.path.exists(pdf_path):
            os.remove(pdf_path)
        if email_sent:
            return jsonify({'message': 'Appointment booked! A confirmation has been sent to your email.'}), 201
        else:
            return jsonify({'message': 'Appointment booked, but the confirmation email could not be sent.'}), 207
    except Exception as e:
        print(f"Error booking appointment: {e}")
        return jsonify({'error': str(e)}), 400

@app.route('/api/my-appointments')
@login_required
def my_appointments():
    if current_user.role == 'Patient':
        query = {'patientId': current_user.id}
    elif current_user.role == 'Doctor':
        query = {'doctorName': current_user.name}
    else:
        return jsonify({'error': 'Invalid user role'}), 403
    appointments = [{**app_data, '_id': str(app_data['_id'])} for app_data in appointments_collection.find(query)]
    return jsonify(appointments)

@app.route('/api/appointments/<appointment_id>/cancel', methods=['POST'])
@login_required
def cancel_appointment(appointment_id):
    try:
        appointment = appointments_collection.find_one({'_id': ObjectId(appointment_id)})
        if appointment and (appointment.get('patientId') == current_user.id or appointment.get('doctorName') == current_user.name):
            appointments_collection.delete_one({'_id': ObjectId(appointment_id)})
            return jsonify({'message': 'Appointment cancelled successfully'}), 200
        return jsonify({'error': 'Unauthorized or Appointment not found'}), 403
    except Exception as e:
        print(f"Error cancelling appointment: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/schedule-suggestions', methods=['POST'])
@login_required
def schedule_suggestions():
    data = request.get_json()
    doctor_name = data.get('doctorName')
    selected_date = data.get('date')
    if not doctor_name or not selected_date:
        return jsonify({'error': 'Doctor name and date are required'}), 400
    time_slots = [f"{h:02d}:{m:02d}" for h in range(9, 17) for m in (0, 30)]
    booked_slots = {app['time'] for app in appointments_collection.find({'doctorName': doctor_name, 'date': selected_date})}
    suggestions = []
    for slot in time_slots:
        if slot in booked_slots:
            continue
        hour = int(slot.split(':')[0])
        prediction_data = pd.DataFrame({'hour': [hour], 'is_booked': [0]}) 
        prediction = scheduler_model.predict(prediction_data)[0]
        status = 'optimal' if prediction == 1 else 'busy'
        suggestions.append({'time': slot, 'status': status})
    return jsonify(suggestions)

@app.route('/api/diet-recommendation', methods=['POST'])
@login_required
def diet_recommendation():
    data = request.get_json()
    disease = data.get('disease')
    if not disease:
        return jsonify({'error': 'Disease not provided'}), 400
    try:
        disease_encoded = le.transform(np.array([disease])) 
        prediction_data = pd.DataFrame({'disease_encoded': disease_encoded})
        diet = diet_model.predict(prediction_data)[0]
        return jsonify({'diet': diet})
    except Exception as e:
        print(f"Error getting diet recommendation: {e}")
        return jsonify({'diet': 'A general balanced diet. Please consult a specialist for your condition.'})

@app.route('/api/symptom-check', methods=['POST'])
def symptom_check_api():
    """Provides a specialist recommendation based on user-entered symptoms using OpenAI API."""
    try:
        data = request.get_json()
        symptoms = data.get('symptoms')
        
        if not symptoms:
            return jsonify({'error': 'Symptoms not provided'}), 400

        prompt = f"Given the following symptoms: '{symptoms}', what type of medical specialist should a person consult? Provide a concise answer, for example: 'a General Physician' or 'a Dermatologist'. If the symptoms are serious, you can also suggest 'an Emergency Room'."

        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a helpful medical assistant. Your task is to recommend a type of medical specialist based on a list of symptoms."},
                {"role": "user", "content": prompt}
            ]
        )
        
        recommendation = response.choices[0].message['content'].strip()
        
        if not recommendation.lower().startswith(('a ', 'an ')):
            recommendation = "a " + recommendation
        
        return jsonify({'recommendation': recommendation})

    except openai.error.AuthenticationError:
        print("OpenAI API key is invalid. Please check your .env file.")
        return jsonify({'error': 'Authentication failed. Please contact support.'}), 500
    except Exception as e:
        print(f"Error calling OpenAI API: {e}")
        return jsonify({'error': 'An error occurred while processing your request.'}), 500

@app.route('/api/doctors', methods=['GET', 'POST'])
def handle_doctors():
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
    try:
        data = request.get_json()
        data['patientId'] = current_user.id
        consultations_collection.insert_one(data)
        return jsonify({'message': 'Consultation booked successfully!'}), 201
    except Exception as e:
        print(f"Error booking consultation: {e}")
        return jsonify({'error': str(e)}), 400

if __name__ == '__main__':
    app.run(debug=True, port=5000)