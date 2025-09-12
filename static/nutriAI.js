document.addEventListener("DOMContentLoaded", () => {
    const getDietBtn = document.getElementById('getDietBtn');
    const routineBox = document.getElementById('routineBox');

    if (getDietBtn) {
        getDietBtn.addEventListener('click', () => {
            const name = document.getElementById('name').value.trim();
            const disease = document.getElementById('disease').value.trim();
            const healthRecords = document.getElementById('healthRecords').value.trim();

            if (name === "" || disease === "") {
                alert("Please fill in your name and primary condition.");
                return;
            }

            routineBox.style.display = "block";
            routineBox.innerHTML = `<p><strong>Analyzing your details and contacting AI Nutritionist...</strong></p>`;

            const dietRequestData = {
                disease: disease,
                healthRecords: healthRecords // Send the additional details
            };

            fetch('/api/diet-recommendation', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(dietRequestData)
            })
            .then(response => response.json())
            .then(data => {
                if (data.error) throw new Error(data.error);
                
                routineBox.innerHTML = `
                    <h3>AI Diet Recommendation for ${name}</h3>
                    <p><strong>Primary Condition:</strong> ${disease}</p>
                    <hr>
                    <p>${data.diet.replace(/\n/g, '<br>')}</p> <hr>
                    <p><em>This is an AI-generated suggestion. Always consult with a certified doctor or nutritionist.</em></p>
                `;
            })
            .catch(error => {
                routineBox.innerHTML = `<p style="color: red;">Error: ${error.message}</p>`;
            });
        });
    }
});