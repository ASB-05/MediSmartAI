document.addEventListener("DOMContentLoaded", () => {
    const doctorDropdown = document.getElementById('doctor');
    const bookBtn = document.getElementById('bookBtn');
    const confirmationBox = document.getElementById('confirmationBox');

    // Fetch doctors to populate the dropdown
    fetch('/api/doctors')
        .then(response => response.json())
        .then(doctorsList => {
            doctorsList.forEach((doc) => {
                const option = document.createElement('option');
                option.value = JSON.stringify(doc); // Store whole object
                option.textContent = `${doc.name} (${doc.specialization})`;
                doctorDropdown.appendChild(option);
            });
        })
        .catch(error => console.error('Error fetching doctors:', error));

    bookBtn.addEventListener('click', () => {
        const name = document.getElementById('name').value.trim();
        const disease = document.getElementById('disease').value.trim();
        const doctorValue = doctorDropdown.value;
        const date = document.getElementById('date').value;
        const time = document.getElementById('time').value;

        if (name === "" || disease === "" || doctorValue === "" || date === "" || time === "") {
            alert("Please fill all fields!");
            return;
        }

        const selectedDoctor = JSON.parse(doctorValue);
        const consultationData = { name, disease, doctor: selectedDoctor, date, time };

        fetch('/api/consultations', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(consultationData)
        })
        .then(response => response.json())
        .then(data => {
            if(data.error) throw new Error(data.error);
            confirmationBox.style.display = "block";
            confirmationBox.innerHTML = `
                <h3>Consultation Booked Successfully!</h3>
                <p><strong>Patient Name:</strong> ${name}</p>
                <p><strong>Disease:</strong> ${disease}</p>
                <p><strong>Doctor:</strong> ${selectedDoctor.name} (${selectedDoctor.specialization})</p>
                <p><strong>Date:</strong> ${date}</p>
                <p><strong>Time:</strong> ${time}</p>
            `;
        })
        .catch(error => {
            alert(`Error: ${error.message}`);
            console.error('Error:', error);
        });
    });
});