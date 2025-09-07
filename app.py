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

# --- Initialization ---
app = Flask(__name__)
app.config['SECRET_KEY'] = os.urandom(24)
CORS(app)

# --- Flask-Mail Configuration ---
# IMPORTANT: For this to work, you MUST set your email and password as environment variables.
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = os.environ.get('MAIL_USERNAME')
app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD')
app.config['MAIL_DEFAULT_SENDER'] = os.environ.get('MAIL_USERNAME')
mail = Mail(app)

# --- MongoDB Configuration ---
client = MongoClient('mongodb://localhost:27017/')
db = client['medismart_db']
users_collection = db['users']
doctors_collection = db['doctors']
appointments_collection = db['appointments']
contacts_collection = db['contacts']

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
    pdf_file_path = f"appointment_{appointment_data['_id']}.pdf"
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

# --- Main Page Routes (Remain the same) ---
@app.route('/')
def index():
    return render_template('index.html')
# ... other routes ...
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
def nutri_ai_page():
    return render_template('nutriAI.html')
    
# --- User Authentication Routes (Remain the same) ---
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

        # Generate PDF and send email
        pdf_path = create_appointment_pdf(data)
        email_sent = send_appointment_email(data['patientEmail'], pdf_path)

        if os.path.exists(pdf_path):
            os.remove(pdf_path)

        if email_sent:
            return jsonify({'message': 'Appointment booked! A confirmation has been sent to your email.'}), 201
        else:
            return jsonify({'message': 'Appointment booked, but the confirmation email could not be sent.'}), 207
            
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/api/my-appointments')
@login_required
def my_appointments():
    query = {'patientId': current_user.id} if current_user.role == 'Patient' else {'doctorName': current_user.name}
    appointments = [{**app, '_id': str(app['_id'])} for app in appointments_collection.find(query)]
    return jsonify(appointments)

@app.route('/api/appointments/<appointment_id>/cancel', methods=['POST'])
@login_required
def cancel_appointment(appointment_id):
    try:
        appointment = appointments_collection.find_one({'_id': ObjectId(appointment_id)})
        if appointment and appointment.get('patientId') == current_user.id:
            appointments_collection.delete_one({'_id': ObjectId(appointment_id)})
            return jsonify({'message': 'Appointment cancelled successfully'}), 200
        return jsonify({'error': 'Unauthorized'}), 403
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/schedule-suggestions', methods=['POST'])
def schedule_suggestions():
    # ... (This route remains the same as before)
    data = request.get_json()
    doctor_name = data.get('doctorName')
    selected_date = data.get('date')
    time_slots = [f"{h:02d}:{m:02d}" for h in range(9, 17) for m in (0, 30)]
    booked_slots = {app['time'] for app in appointments_collection.find({'doctorName': doctor_name, 'date': selected_date})}
    suggestions = []
    for slot in time_slots:
        if slot in booked_slots: continue
        hour = int(slot.split(':')[0])
        status = 'optimal' if 9 <= hour < 12 else 'busy'
        suggestions.append({'time': slot, 'status': status})
    return jsonify(suggestions)
    
@app.route('/api/symptom-check', methods=['POST'])
def symptom_check_api():
    # ... (This route remains the same as before)
    symptoms = request.get_json().get('symptoms', '').lower()
    domain_keywords = {
        'Dermatologist': ['rash', 'skin', 'itch', 'acne', 'mole'],
        'Cardiologist': ['chest pain', 'heart', 'pressure', 'palpitations', 'dizzy'],
        'Neurologist': ['headache', 'migraine', 'seizure', 'numbness', 'memory loss'],
        'Orthopedic': ['joint pain', 'bone', 'fracture', 'sprain', 'knee', 'back pain'],
        'General Physician': ['fever', 'cough', 'cold', 'sore throat', 'fatigue']
    }
    recommendation = "General Physician"
    max_matches = 0
    for domain, keywords in domain_keywords.items():
        matches = sum([1 for keyword in keywords if keyword in symptoms])
        if matches > max_matches:
            max_matches = matches
            recommendation = domain
    recommendation = f"a {recommendation}" if max_matches > 0 else "a General Physician for a consultation"
    return jsonify({'recommendation': recommendation})

@app.route('/api/doctors', methods=['GET', 'POST'])
def handle_doctors():
    if request.method == 'POST':
        try:
            doctors_collection.insert_one(request.get_json())
            return jsonify({'message': 'Doctor added successfully!'}), 201
        except Exception as e:
            return jsonify({'error': str(e)}), 400
    doctors = list(doctors_collection.find({}, {'_id': 0}))
    return jsonify(doctors)

if __name__ == '__main__':
    app.run(debug=True, port=5000)

