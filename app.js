document.getElementById("inmateForm").addEventListener("submit", async function(e) {
  e.preventDefault();
  
  let formData = new FormData(this);  // Collect the form data

  // Send the form data to the Flask backend for processing
  const response = await fetch('/register', {
    method: 'POST',
    body: formData
  });

  // Get the response from the server
  const result = await response.text();
  alert(result);  // Display the result in an alert box
});
