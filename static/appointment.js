document.addEventListener("DOMContentLoaded", () => {
    const domainSelect = document.getElementById("domainSelect");
    const doctorSelect = document.getElementById("doctorSelect");
    const dateInput = document.getElementById("appointmentDate");
    const timeInput = document.getElementById("appointmentTime");
    const confirmation = document.getElementById("confirmation");
    const suggestionsBox = document.getElementById("ai-suggestions-box");
    const suggestionsContainer = document.getElementById("ai-suggestions");

    let doctorsData = [];

    // Fetch all doctors to populate dropdowns
    fetch('/api/doctors')
        .then(response => response.json())
        .then(data => {
            doctorsData = data;
            if (doctorsData.length === 0) {
                domainSelect.innerHTML = '<option value="">No doctors available</option>';
                return;
            }
            const uniqueDomains = [...new Set(doctorsData.map(d => d.domain))];
            uniqueDomains.forEach(domain => {
                const option = document.createElement("option");
                option.value = domain;
                option.textContent = domain;
                domainSelect.appendChild(option);
            });
        })
        .catch(error => console.error('Error fetching doctors:', error));
    
    domainSelect.addEventListener("change", () => {
        const selectedDomain = domainSelect.value;
        doctorSelect.innerHTML = '<option value="">--Select Doctor--</option>';
        if (selectedDomain) {
            const filteredDoctors = doctorsData.filter(d => d.domain === selectedDomain);
            filteredDoctors.forEach(doc => {
                const option = document.createElement("option");
                // Store the entire doctor object as a JSON string
                option.value = JSON.stringify(doc);
                option.textContent = `Dr. ${doc.name} (${doc.hospitalName})`;
                doctorSelect.appendChild(option);
            });
        }
    });

    // --- AI Scheduling Logic ---
    async function getAiSuggestions() {
        if (!doctorSelect.value) {
            suggestionsBox.classList.add('hidden');
            return;
        }
        const selectedDoctor = JSON.parse(doctorSelect.value);
        const doctorName = selectedDoctor.name;
        const date = dateInput.value;

        if (!doctorName || !date) {
            suggestionsBox.classList.add('hidden');
            return;
        }

        try {
            const response = await fetch('/api/schedule-suggestions', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ doctorName, date })
            });
            const suggestions = await response.json();
            displaySuggestions(suggestions);
        } catch (error) {
            console.error('Error fetching suggestions:', error);
        }
    }

    function displaySuggestions(suggestions) {
        suggestionsContainer.innerHTML = ''; // Clear old suggestions
        if (suggestions.length === 0) {
            suggestionsContainer.innerHTML = '<p>No AI-suggested slots for this day. Please pick a time manually.</p>';
        } else {
            suggestions.forEach(slot => {
                const btn = document.createElement('button');
                btn.type = 'button';
                btn.className = `suggestion-btn ${slot.status}`; // 'optimal' or 'busy'
                btn.textContent = slot.time;
                btn.onclick = () => {
                    timeInput.value = slot.time;
                };
                suggestionsContainer.appendChild(btn);
            });
        }
        suggestionsBox.classList.remove('hidden');
    }

    // Fetch suggestions when doctor or date changes
    doctorSelect.addEventListener('change', getAiSuggestions);
    dateInput.addEventListener('change', getAiSuggestions);


    // Handle appointment form submission
    document.getElementById("appointmentForm").addEventListener("submit", function(e) {
        e.preventDefault();
        confirmation.textContent = "Booking...";
        confirmation.style.color = 'orange';

        const selectedDoctor = JSON.parse(doctorSelect.value);
        const appointmentType = document.getElementById("appointmentType").value;

        const appointmentData = {
            doctorName: selectedDoctor.name,
            appointmentType: appointmentType,
            date: dateInput.value,
            time: timeInput.value,
            additionalNotes: document.getElementById("additionalNotes").value,
            // Add hospital details if it's an offline appointment
            hospitalName: appointmentType === 'Offline' ? selectedDoctor.hospitalName : null,
            hospitalLocation: appointmentType === 'Offline' ? selectedDoctor.hospitalLocation : null,
        };

        fetch('/api/appointments', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(appointmentData),
            })
            .then(response => response.json())
            .then(data => {
                if (data.error) throw new Error(data.error);
                let successMessage = data.message;
                if (appointmentType === 'Offline') {
                    successMessage += ` Please visit ${selectedDoctor.hospitalName} in ${selectedDoctor.hospitalLocation}.`;
                }
                confirmation.textContent = successMessage;
                confirmation.style.color = 'green';
                document.getElementById("appointmentForm").reset();
                suggestionsBox.classList.add('hidden');
            })
            .catch(error => {
                confirmation.textContent = `Error: ${error.message}`;
                confirmation.style.color = 'red';
            });
    });
});
