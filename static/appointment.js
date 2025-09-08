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
                option.value = doc.name;
                option.textContent = doc.name;
                doctorSelect.appendChild(option);
            });
        }
    });

    // --- NEW: AI Scheduling Logic ---
    async function getAiSuggestions() {
        const doctorName = doctorSelect.value;
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
            suggestionsContainer.innerHTML = '<p>No available slots for this day.</p>';
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

        const appointmentData = {
            doctorName: doctorSelect.value,
            appointmentType: document.getElementById("appointmentType").value,
            date: dateInput.value,
            time: timeInput.value,
            additionalNotes: document.getElementById("additionalNotes").value,
        };

        fetch('/api/appointments', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(appointmentData),
            })
            .then(response => response.json())
            .then(data => {
                if (data.error) throw new Error(data.error);
                confirmation.textContent = data.message;
                confirmation.style.color = 'green';
                document.getElementById("appointmentForm").reset();
                suggestionsBox.classList.add('hidden'); // Hide suggestions after booking
            })
            .catch(error => {
                confirmation.textContent = `Error: ${error.message}`;
                confirmation.style.color = 'red';
            });
    });
});
