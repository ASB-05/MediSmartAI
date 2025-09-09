document.addEventListener('DOMContentLoaded', () => {
    // Function to show a specific section and hide others
    function showSection(targetId) {
        // Hide all sections first
        document.querySelectorAll('.section').forEach(section => {
            section.style.display = 'none';
        });

        // Show the target section
        const activeSection = document.getElementById(targetId);
        if (activeSection) {
            activeSection.style.display = 'block';
            activeSection.scrollIntoView({ behavior: 'smooth' });
        }
    }

    // Add click listeners to the main dashboard buttons
    document.querySelectorAll('.dashboard .dash-btn').forEach(button => {
        button.addEventListener('click', () => {
            // Get the target section ID from the button's onclick attribute content
            const target = button.getAttribute('onclick').match(/'(.+?)'/)[1];
            if (target) {
                showSection(target);
            }
        });
    });

    // Add click listeners for emergency call buttons
    document.querySelectorAll('.emergency, .emergency-call').forEach(button => {
        button.addEventListener('click', (event) => {
            // This prevents the section-showing logic from re-triggering
            event.stopPropagation(); 
            
            if (button.textContent.includes("Ambulance")) {
                alert("Calling Ambulance...");
                // This simulates a call to an emergency number
                window.location.href = 'tel:108'; 
            } else {
                alert("Calling Children...");
                // Replace with a real contact number
                window.location.href = 'tel:+911234567890'; 
            }
        });
    });

    // --- Example Medication Reminder ---
    const medicines = [
        { name: "Heart Medication", time: "09:00" },
        { name: "Vitamin D", time: "13:00" },
        { name: "Blood Pressure Pill", time: "21:00" }
    ];

    function checkMedicineReminders() {
        const now = new Date();
        const currentTime = now.getHours().toString().padStart(2, '0') + ':' + now.getMinutes().toString().padStart(2, '0');

        medicines.forEach(med => {
            if (med.time === currentTime) {
                // In a real app, this would be a more noticeable notification
                alert(`Reminder: It's time to take your ${med.name}.`);
            }
        });
    }

    // Check for medicine reminders every 60 seconds
    setInterval(checkMedicineReminders, 60000);
});