document.addEventListener('DOMContentLoaded', () => {
    let userMedications = [];

    // --- SECTION VISIBILITY ---
    window.showSection = function(targetId) {
        document.querySelectorAll('.section').forEach(section => {
            section.style.display = 'none';
        });
        const activeSection = document.getElementById(targetId);
        if (activeSection) {
            activeSection.style.display = 'block';
            activeSection.scrollIntoView({ behavior: 'smooth' });
            // Load data for the shown section
            if (targetId === 'health-records') loadHealthRecords();
            if (targetId === 'appointments') loadAppointments();
            if (targetId === 'medications') loadMedications();
        }
    }

    // --- EMERGENCY CALLS ---
    document.querySelectorAll('.emergency-call').forEach(button => {
        button.addEventListener('click', (event) => {
            event.stopPropagation();
            if (button.textContent.includes("Ambulance")) {
                alert("Calling Ambulance (108)...");
                window.location.href = 'tel:108';
            } else {
                alert("Calling Family Contact...");
                window.location.href = 'tel:+911234567890'; // Replace with a real number
            }
        });
    });

    // --- HEALTH RECORDS ---
    const healthRecordForm = document.getElementById('healthRecordForm');
    const healthRecordsList = document.getElementById('healthRecordsList');

    async function loadHealthRecords() {
        try {
            const response = await fetch('/api/elder/health-records');
            if (!response.ok) throw new Error('Could not fetch health records.');
            const records = await response.json();
            healthRecordsList.innerHTML = '<h3>Saved Records</h3>';
            if (records.length === 0) {
                healthRecordsList.innerHTML += '<p>No records found.</p>';
                return;
            }
            records.forEach(r => {
                const recordEl = document.createElement('div');
                recordEl.className = 'item-card';
                recordEl.innerHTML = `<strong>${r.metric}:</strong> ${r.value} <span class="timestamp">${new Date(r.date + 'Z').toLocaleString()}</span>`;
                healthRecordsList.appendChild(recordEl);
            });
        } catch (error) {
            healthRecordsList.innerHTML = `<p class="error">${error.message}</p>`;
        }
    }

    healthRecordForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const metric = document.getElementById('recordMetric').value;
        const value = document.getElementById('recordValue').value;
        try {
            await fetch('/api/elder/health-records', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ metric, value })
            });
            healthRecordForm.reset();
            loadHealthRecords();
        } catch (error) {
            alert(`Error saving record: ${error.message}`);
        }
    });

    // --- APPOINTMENTS ---
    const elderAppointmentsList = document.getElementById('elderAppointmentsList');
    async function loadAppointments() {
        try {
            const response = await fetch('/api/my-appointments');
            if (!response.ok) throw new Error('Please log in to see appointments.');
            const appointments = await response.json();
            elderAppointmentsList.innerHTML = '<h3>Upcoming Appointments</h3>';
            if (appointments.length === 0) {
                elderAppointmentsList.innerHTML += '<p>No upcoming appointments found.</p>';
                return;
            }
            appointments.forEach(app => {
                const appEl = document.createElement('div');
                appEl.className = 'item-card';
                appEl.innerHTML = `<strong>With ${app.doctorName}</strong> on ${app.date} at ${app.time}`;
                elderAppointmentsList.appendChild(appEl);
            });
        } catch (error) {
            elderAppointmentsList.innerHTML = `<p class="error">${error.message}</p>`;
        }
    }

    // --- MEDICATIONS ---
    const medicationForm = document.getElementById('medicationForm');
    const medicationsList = document.getElementById('medicationsList');

    async function loadMedications() {
        try {
            const response = await fetch('/api/elder/medications');
            if (!response.ok) throw new Error('Could not fetch medication schedule.');
            const meds = await response.json();
            userMedications = meds; // Store for the reminder checker
            medicationsList.innerHTML = '<h3>My Medication Schedule</h3>';
            if (meds.length === 0) {
                medicationsList.innerHTML += '<p>No medications added yet.</p>';
                return;
            }
            meds.forEach(m => {
                const medEl = document.createElement('div');
                medEl.className = 'item-card';
                medEl.innerHTML = `
                    <span><strong>${m.name}</strong> (${m.dosage}) at <strong>${m.time}</strong></span>
                    <button class="delete-btn" data-id="${m._id}">&times;</button>`;
                medicationsList.appendChild(medEl);
            });
        } catch (error) {
            medicationsList.innerHTML = `<p class="error">${error.message}</p>`;
        }
    }
    
    medicationForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const name = document.getElementById('medName').value;
        const dosage = document.getElementById('medDosage').value;
        const time = document.getElementById('medTime').value;
        try {
            await fetch('/api/elder/medications', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ name, dosage, time })
            });
            medicationForm.reset();
            loadMedications();
        } catch (error) {
            alert(`Error saving medication: ${error.message}`);
        }
    });

    medicationsList.addEventListener('click', async (e) => {
        if (e.target.classList.contains('delete-btn')) {
            const medId = e.target.dataset.id;
            if (confirm('Are you sure you want to delete this medication?')) {
                try {
                    await fetch(`/api/elder/medications/${medId}`, { method: 'DELETE' });
                    loadMedications();
                } catch (error) {
                    alert(`Error deleting medication: ${error.message}`);
                }
            }
        }
    });
    
    // --- IMPROVED MEDICATION REMINDER ---
    const reminderBanner = document.getElementById('reminder-banner');
    function checkMedicationReminders() {
        const now = new Date();
        const currentTime = now.getHours().toString().padStart(2, '0') + ':' + now.getMinutes().toString().padStart(2, '0');

        userMedications.forEach(med => {
            if (med.time === currentTime && !med.reminded) {
                med.reminded = true; // Mark as reminded for today
                reminderBanner.innerHTML = `
                    <div class="reminder-content">
                        <h2>Time for your medication!</h2>
                        <p>Please take: <strong>${med.name} (${med.dosage})</strong></p>
                        <button id="dismissReminderBtn">Dismiss</button>
                    </div>`;
                reminderBanner.className = 'reminder-banner-visible';
            }
        });
    }

    // Reset reminders daily
    function resetReminders() {
        userMedications.forEach(med => med.reminded = false);
    }

    reminderBanner.addEventListener('click', (e) => {
        if (e.target.id === 'dismissReminderBtn') {
            reminderBanner.className = 'reminder-banner-hidden';
        }
    });
    
    loadMedications(); // Initial load
    setInterval(checkMedicationReminders, 15000); // Check every 15 seconds
    setInterval(resetReminders, 1000 * 60 * 60 * 24); // Reset daily
});