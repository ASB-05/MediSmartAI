document.addEventListener('DOMContentLoaded', () => {
    const appointmentsListDiv = document.getElementById('appointments-list');
    const container = document.querySelector('.dashboard-container');
    const userRole = container.dataset.userRole;

    async function fetchAppointments() {
        try {
            const response = await fetch('/api/my-appointments');
            if (!response.ok) {
                throw new Error('Failed to fetch appointments');
            }
            const appointments = await response.json();
            displayAppointments(appointments);
        } catch (error) {
            appointmentsListDiv.innerHTML = `<p style="color: red;">Error: ${error.message}</p>`;
        }
    }

    function displayAppointments(appointments) {
        if (appointments.length === 0) {
            appointmentsListDiv.innerHTML = '<p>You have no upcoming appointments.</p>';
            return;
        }

        appointmentsListDiv.innerHTML = ''; // Clear loading message
        appointments.forEach(app => {
            const card = document.createElement('div');
            card.className = 'appointment-card';

            // Dynamically set title based on user role
            const title = userRole === 'Doctor'
                ? `<h3>Appointment with ${app.patientName}</h3>`
                : `<h3>Appointment with ${app.doctorName}</h3>`;

            card.innerHTML = `
                <div class="info">
                    ${title}
                    <p><strong>Date:</strong> ${app.date}</p>
                    <p><strong>Time:</strong> ${app.time}</p>
                    <p><strong>Type:</strong> ${app.appointmentType}</p>
                </div>
                <div class="actions">
                    <button class="cancel-btn" data-id="${app._id}">Cancel</button>
                </div>
            `;
            appointmentsListDiv.appendChild(card);
        });
    }
    
    // Event listener for cancellation
    appointmentsListDiv.addEventListener('click', async (e) => {
        if (e.target.classList.contains('cancel-btn')) {
            const appointmentId = e.target.dataset.id;
            if (confirm('Are you sure you want to cancel this appointment?')) {
                try {
                    const response = await fetch(`/api/appointments/${appointmentId}/cancel`, {
                        method: 'POST'
                    });
                    const result = await response.json();
                    if (!response.ok) throw new Error(result.error || 'Failed to cancel');
                    
                    alert(result.message);
                    fetchAppointments(); // Refresh the list
                } catch (error) {
                    alert(`Error: ${error.message}`);
                }
            }
        }
    });

    fetchAppointments();
});