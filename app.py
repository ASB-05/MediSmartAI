import os
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, jsonify
from flask_cors import CORS
from flask_mail import Mail, Message
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from pymongo import MongoClient
from werkzeug.security import generate_password_hash, check_password_hash
from bson.objectid import ObjectId
from fpdf import FPDF
from dotenv import load_dotenv

# --- Load environment variables ---
load_dotenv()

# --- Import AI models from the dedicated module ---
from ai_models import get_schedule_suggestions, get_symptom_recommendation_openai, get_diet_recommendation_openai

# --- Initialize Flask Application ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
app = Flask(
    __name__,
    template_folder=os.path.join(BASE_DIR, 'templates'),
    static_folder=os.path.join(BASE_DIR, 'static')
)
app.config['SECRET_KEY'] = os.urandom(24)
CORS(app)

# --- Mail Configuration ---
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
consultations_collection = db['consultations']
health_records_collection = db['health_records']
medications_collection = db['medications']

# --- Flask-Login Configuration ---
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

class User(UserMixin):
    """User model for Flask-Login."""
    def __init__(self, user_data):
        self.id = str(user_data['_id'])
        self.email = user_data['email']
        self.name = user_data['name']
        self.role = user_data['role']

@login_manager.user_loader
def load_user(user_id):
    """Loads a user from the database."""
    user_data = users_collection.find_one({'_id': ObjectId(user_id)})
    return User(user_data) if user_data else None

# --- PDF & Email Helper Functions ---
def create_appointment_pdf(appointment_data):
    """Generates a beautifully formatted PDF confirmation for an appointment."""
    pdf = FPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)
    
    # --- Header ---
    pdf.set_font("Arial", "B", 20)
    pdf.set_text_color(0, 119, 182)  # Blue color
    pdf.cell(0, 15, "MediSmart AI", 0, 1, 'C')
    pdf.set_font("Arial", "", 12)
    pdf.set_text_color(100, 100, 100) # Gray color
    pdf.cell(0, 8, "Your Appointment Confirmation", 0, 1, 'C')
    pdf.ln(15)

    # --- Details Section with Border ---
    pdf.set_font("Arial", "", 12)
    pdf.set_text_color(0, 0, 0) # Black color
    pdf.set_draw_color(220, 220, 220) # Light gray border
    pdf.set_line_width(0.5)
    
    # Calculate content width
    page_width = pdf.w
    margin = 20
    content_width = page_width - (2 * margin)
    
    # Get y position before drawing the box
    y_before_box = pdf.get_y()
    
    # Set a consistent left margin for the text inside the box
    text_x_pos = margin + 5
    
    # --- Draw content first to calculate height ---
    pdf.set_xy(text_x_pos, y_before_box + 5)
    pdf.set_font("Arial", "B", 12)
    pdf.cell(40, 10, "Patient:", 0, 0)
    pdf.set_font("Arial", "", 12)
    pdf.cell(0, 10, appointment_data['patientName'], 0, 1)

    pdf.set_x(text_x_pos)
    pdf.set_font("Arial", "B", 12)
    pdf.cell(40, 10, "Doctor:", 0, 0)
    pdf.set_font("Arial", "", 12)
    pdf.cell(0, 10, f"Dr. {appointment_data['doctorName']}", 0, 1)

    pdf.set_x(text_x_pos)
    pdf.set_font("Arial", "B", 12)
    pdf.cell(40, 10, "Date:", 0, 0)
    pdf.set_font("Arial", "", 12)
    pdf.cell(0, 10, appointment_data['date'], 0, 1)
    
    pdf.set_x(text_x_pos)
    pdf.set_font("Arial", "B", 12)
    pdf.cell(40, 10, "Time:", 0, 0)
    pdf.set_font("Arial", "", 12)
    pdf.cell(0, 10, appointment_data['time'], 0, 1)

    pdf.set_x(text_x_pos)
    pdf.set_font("Arial", "B", 12)
    pdf.cell(40, 10, "Type:", 0, 0)
    pdf.set_font("Arial", "", 12)
    pdf.cell(0, 10, appointment_data['appointmentType'], 0, 1)
    
    # Conditionally add Hospital Location for Offline appointments
    if appointment_data.get('appointmentType') == 'Offline':
        pdf.set_x(text_x_pos)
        pdf.set_font("Arial", "B", 12)
        pdf.cell(40, 10, "Location:", 0, 0)
        pdf.set_font("Arial", "", 12)
        pdf.multi_cell(content_width - 50, 10, f"{appointment_data.get('hospitalName', 'N/A')}, {appointment_data.get('hospitalLocation', 'N/A')}", 0, 'L')

    pdf.ln(5) # Add padding at the bottom
    y_after_content = pdf.get_y()
    
    # Calculate the total height of the box
    box_height = y_after_content - y_before_box
    
    # Draw the rounded rectangle (border) around the content area
    pdf.rounded_rect(margin, y_before_box, content_width, box_height, 5, 'D')

    # --- Footer ---
    pdf.set_y(-40)
    pdf.set_font("Arial", "I", 10)
    pdf.set_text_color(150, 150, 150)
    pdf.multi_cell(0, 5, "Thank you for choosing MediSmart AI. Please arrive 15 minutes early for offline appointments. If you need to cancel, please do so from your dashboard.", 0, 'C')

    path = os.path.join(BASE_DIR, f"appointment_{appointment_data['_id']}.pdf")
    pdf.output(path)
    return path


def send_appointment_email(recipient_email, attachment_path):
    """Sends a confirmation email with the PDF attachment."""
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
def index(): return render_template('index.html')

@app.route('/doctors')
def doctors_page(): return render_template('doctor.html', current_user=current_user)

@app.route('/appointments')
@login_required
def appointments_page(): return render_template('appointment.html')

@app.route('/consult-online')
@login_required
def consult_online_page(): return render_template('consultOnline.html')

@app.route('/contact')
def contact_page(): return render_template('contact.html')

@app.route('/elder-ai')
def elder_ai_page(): return render_template('elderAI.html')

@app.route('/nutri-ai')
@login_required
def nutri_ai_page(): return render_template('nutriAI.html')

@app.route('/symptom-checker')
def symptom_checker(): return render_template('symptom_checker.html')

@app.route('/dashboard')
@login_required
def dashboard(): return render_template('dashboard.html')

# --- User Authentication Routes ---
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        password = request.form.get('password')
        role = request.form.get('role')
        if users_collection.find_one({'email': email}):
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
            login_user(User(user_data))
            return redirect(url_for('dashboard'))
        return redirect(url_for('login'))
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

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
        data['_id'] = result.inserted_id
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
    apps = [{**a, '_id': str(a['_id'])} for a in appointments_collection.find(query)]
    return jsonify(apps)

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
        return jsonify({'error': str(e)}), 500

@app.route('/api/doctors', methods=['GET', 'POST'])
def handle_doctors():
    if request.method == 'POST':
        if not current_user.is_authenticated or current_user.role != 'Doctor':
            return jsonify({'error': 'Unauthorized action. Only doctors can add profiles.'}), 403
        try:
            doctors_collection.insert_one(request.get_json())
            return jsonify({'message': 'Doctor added successfully!'}), 201
        except Exception as e:
            return jsonify({'error': str(e)}), 400
    
    doctors_list = []
    for doc in doctors_collection.find({}):
        doc['_id'] = str(doc['_id'])
        doctors_list.append(doc)
    return jsonify(doctors_list)

@app.route('/api/contact', methods=['POST'])
def handle_contact():
    try:
        contacts_collection.insert_one(request.get_json())
        return jsonify({'message': 'Contact form submitted successfully!'}), 201
    except Exception as e:
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
        return jsonify({'error': str(e)}), 400

# --- AI-Powered API Routes ---

@app.route('/api/schedule-suggestions', methods=['POST'])
@login_required
def schedule_suggestions_api():
    data = request.get_json()
    doctor_name = data.get('doctorName')
    selected_date = data.get('date')
    if not doctor_name or not selected_date:
        return jsonify({'error': 'Doctor name and date are required'}), 400
    suggestions = get_schedule_suggestions(doctor_name, selected_date, appointments_collection)
    return jsonify(suggestions)

@app.route('/api/symptom-check', methods=['POST'])
def symptom_check_api():
    symptoms = request.get_json().get('symptoms', '')
    if not symptoms:
        return jsonify({'error': 'Symptoms not provided'}), 400
    recommendation = get_symptom_recommendation_openai(symptoms)
    return jsonify(recommendation)

@app.route('/api/diet-recommendation', methods=['POST'])
@login_required
def diet_recommendation_api():
    data = request.get_json()
    disease = data.get('disease')
    user_details = data.get('healthRecords')
    if not disease:
        return jsonify({'error': 'Disease not provided'}), 400
    recommendation = get_diet_recommendation_openai(disease, user_details)
    return jsonify(recommendation)

# --- ElderCare AI API Routes ---

@app.route('/api/elder/health-records', methods=['GET', 'POST'])
@login_required
def handle_health_records():
    if request.method == 'POST':
        data = request.get_json()
        data['userId'] = current_user.id
        data['date'] = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
        health_records_collection.insert_one(data)
        return jsonify({'message': 'Health record added successfully!'}), 201
    
    records = list(health_records_collection.find({'userId': current_user.id}).sort('date', -1))
    for record in records:
        record['_id'] = str(record['_id'])
    return jsonify(records)

@app.route('/api/elder/medications', methods=['GET', 'POST'])
@login_required
def handle_medications():
    if request.method == 'POST':
        data = request.get_json()
        data['userId'] = current_user.id
        medications_collection.insert_one(data)
        return jsonify({'message': 'Medication added successfully!'}), 201
    
    meds = list(medications_collection.find({'userId': current_user.id}))
    for med in meds:
        med['_id'] = str(med['_id'])
    return jsonify(meds)

@app.route('/api/elder/medications/<med_id>', methods=['DELETE'])
@login_required
def delete_medication(med_id):
    result = medications_collection.delete_one({'_id': ObjectId(med_id), 'userId': current_user.id})
    if result.deleted_count == 1:
        return jsonify({'message': 'Medication deleted successfully!'}), 200
    return jsonify({'error': 'Medication not found or unauthorized'}), 404

# --- Run Application ---
if __name__ == '__main__':
    app.run(debug=True, port=5000)