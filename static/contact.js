document.addEventListener("DOMContentLoaded", () => {
    const submitButton = document.getElementById('submitBtn');
    if(submitButton) {
        submitButton.addEventListener('click', submitForm);
    }
});

function submitForm() {
    const name = document.getElementById('name').value.trim();
    const email = document.getElementById('email').value.trim();
    const subject = document.getElementById('subject').value.trim();
    const message = document.getElementById('message').value.trim();
    const confirmation = document.getElementById('confirmationMessage');

    if (name === "" || email === "" || subject === "" || message === "") {
        alert("Please fill all fields before submitting!");
        return;
    }

    const contactData = { name, email, subject, message };

    fetch('/api/contact', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(contactData)
    })
    .then(response => response.json())
    .then(data => {
        if (data.error) throw new Error(data.error);
        confirmation.textContent = `Thank you, ${name}! Your message has been received.`;
        document.getElementById('contactForm').reset();
    })
    .catch(error => {
        console.error('Error submitting form:', error);
        confirmation.textContent = `Error: ${error.message}`;
        confirmation.style.color = 'red';
    });
}