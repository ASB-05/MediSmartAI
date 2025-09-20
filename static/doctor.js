document.addEventListener("DOMContentLoaded", () => {
    const addModal = document.getElementById("doctorFormModal");
    const viewModal = document.getElementById("viewDoctorsModal");
    const addCloseBtn = addModal.querySelector(".close");
    const viewCloseBtn = viewModal.querySelector(".close");
    const doctorForm = document.getElementById("doctorForm");

    // --- Add Doctor Modal Logic ---
    document.querySelectorAll(".add-doctor-btn").forEach(btn => {
        btn.addEventListener("click", (e) => {
            const currentDomainCard = e.target.closest(".domain-card");
            const domainName = currentDomainCard.dataset.domain;
            document.getElementById("docDomain").value = domainName;
            addModal.style.display = "flex";
        });
    });

    // --- View Doctors Modal Logic ---
    document.querySelectorAll(".view-doctors-btn").forEach(btn => {
        btn.addEventListener("click", (e) => {
            const domainCard = e.target.closest(".domain-card");
            const domainName = domainCard.dataset.domain;
            const viewDoctorsContainer = document.getElementById("viewDoctorsContainer");
            
            viewDoctorsContainer.innerHTML = '<p>Loading doctors...</p>';
            viewModal.style.display = "flex";

            fetch('/api/doctors')
                .then(response => response.json())
                .then(allDoctors => {
                    const filteredDoctors = allDoctors.filter(doc => doc.domain === domainName);
                    
                    viewDoctorsContainer.innerHTML = ''; 
                    
                    if (filteredDoctors.length === 0) {
                        viewDoctorsContainer.innerHTML = '<p>No doctors found for this domain.</p>';
                        return;
                    }

                    filteredDoctors.forEach(doc => {
                        const docCard = document.createElement('div');
                        docCard.className = 'doctor-card';
                        docCard.innerHTML = `
                            <img src="${doc.image}" alt="${doc.name}">
                            <h4>Dr. ${doc.name}</h4>
                            <p>${doc.degree}, ${doc.specialization}</p>
                            <p><strong>Experience:</strong> ${doc.experience} years</p>
                            <p><strong>Hospital:</strong> ${doc.hospitalName}, ${doc.hospitalLocation}</p>
                            <p><strong>Contact:</strong> ${doc.contact}</p>
                        `;
                        viewDoctorsContainer.appendChild(docCard);
                    });
                })
                .catch(error => {
                    console.error('Error fetching doctors:', error);
                    viewDoctorsContainer.innerHTML = '<p>Could not load doctors. Please try again.</p>';
                });
        });
    });

    // --- Modal Closing Logic ---
    const closeAddModal = () => {
        addModal.style.display = "none";
        doctorForm.reset();
    };
    const closeViewModal = () => {
        viewModal.style.display = "none";
    };

    addCloseBtn.addEventListener("click", closeAddModal);
    viewCloseBtn.addEventListener("click", closeViewModal);

    window.addEventListener("click", (e) => {
        if (e.target == addModal) closeAddModal();
        if (e.target == viewModal) closeViewModal();
    });

    // --- Form Submission Logic ---
    doctorForm.addEventListener("submit", (e) => {
        e.preventDefault();
        const newDoctor = {
            name: document.getElementById("docName").value,
            degree: document.getElementById("docDegree").value,
            experience: document.getElementById("docExperience").value,
            specialization: document.getElementById("docSpecialization").value,
            domain: document.getElementById("docDomain").value,
            hospitalName: document.getElementById("docHospitalName").value,
            hospitalLocation: document.getElementById("docHospitalLocation").value,
            contact: document.getElementById("docContact").value,
            image: document.getElementById("docImage").value,
        };

        fetch('/api/doctors', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(newDoctor)
        })
        .then(response => {
            if(!response.ok) {
                return response.json().then(err => { throw new Error(err.error || 'Failed to add doctor') });
            }
            return response.json();
        })
        .then(data => {
            alert(data.message || 'Doctor added successfully!');
            closeAddModal();
        })
        .catch(error => {
            console.error('Error adding doctor:', error);
            alert(`Error: ${error.message}`);
        });
    });
});
