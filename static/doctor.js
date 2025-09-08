document.addEventListener("DOMContentLoaded", () => {
    const modal = document.getElementById("doctorFormModal");
    const closeBtn = document.querySelector(".close");
    const doctorForm = document.getElementById("doctorForm");
    let currentDomainCard = null;

    // Show modal
    document.querySelectorAll(".add-doctor-btn").forEach(btn => {
        btn.addEventListener("click", (e) => {
            currentDomainCard = e.target.closest(".domain-card");
            const domainName = currentDomainCard.dataset.domain;
            document.getElementById("docDomain").value = domainName;
            modal.style.display = "flex";
        });
    });

    // Close modal
    const closeModal = () => {
        modal.style.display = "none";
        doctorForm.reset();
    };
    closeBtn.addEventListener("click", closeModal);
    window.addEventListener("click", (e) => {
        if (e.target == modal) {
            closeModal();
        }
    });

    // Handle Add Doctor form submission
    doctorForm.addEventListener("submit", (e) => {
        e.preventDefault();
        if (!currentDomainCard) return;

        const newDoctor = {
            name: document.getElementById("docName").value,
            degree: document.getElementById("docDegree").value,
            experience: document.getElementById("docExperience").value,
            specialization: document.getElementById("docSpecialization").value,
            domain: document.getElementById("docDomain").value,
            contact: document.getElementById("docContact").value,
            image: document.getElementById("docImage").value,
        };

        fetch('/api/doctors', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(newDoctor)
        })
        .then(response => response.json())
        .then(data => {
            if(data.error) throw new Error(data.error);
            alert('Doctor added successfully!');
            // You might want to refresh the doctor list here
            closeModal();
        })
        .catch(error => {
            console.error('Error adding doctor:', error);
            alert(`Error: ${error.message}`);
        });
    });
});