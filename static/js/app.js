let currentUser = null;  // This will hold the currently logged-in user

// Function to display specific pages with access control
function showPage(pageId) {
  const pages = document.querySelectorAll(".page");
  pages.forEach(page => page.style.display = "none");
  document.getElementById(pageId).style.display = "block";

  // Restrict access to admin dashboard for non-admins
  if (pageId === 'admin-dashboard') {
    if (!currentUser || !currentUser.isAdmin) {
      alert("Admin access only. Please log in as admin.");
      showPage('login');
      return;  // Prevent further code execution in showPage
    } else {
      fetchAllUsers();
    }
  }
}




// Handle login functionality
document.getElementById("loginForm").addEventListener("submit", async function(event) {
  event.preventDefault();
  const username = document.getElementById("username").value;
  const password = document.getElementById("password").value;

  try {
    const response = await fetch('/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password })
    });

    if (response.ok) {
      const result = await response.json();
      alert("Login successful!");

      // Set the current user
      currentUser = {
        username: result.username,
        isAdmin: result.isAdmin
      };

       // Debugging to confirm the currentUser object is set correctly
       console.log("Current User:", currentUser);


      // Redirect based on user's role
      if (currentUser.isAdmin) {
        showPage('admin-dashboard');
      } else {
        showPage('landing');
      }
    } else {
      const errorData = await response.json();
      alert(errorData.error || "Invalid credentials, please try again.");
    }
  } catch (error) {
    console.error("Login request failed:", error);
    alert("An error occurred during login.");
  }
});

// Handle user registration form submission
document.getElementById("registerUserForm").addEventListener("submit", async function (event) {
  event.preventDefault();

  const username = document.getElementById("registerUsername").value;
  const password = document.getElementById("registerPassword").value;
  const role = document.getElementById("role").value;

  try {
    const response = await fetch('/register_user', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password, role })
    });

    if (response.ok) {
      const result = await response.json();
      alert(result.message);
      showPage('login');
    } else {
      const errorData = await response.json();
      alert(errorData.error || "Failed to register user. Please try again.");
    }
  } catch (error) {
    console.error("Error during user registration:", error);
    alert("An error occurred during registration.");
  }
});


// Function to fetch all users and display them using .then()
function fetchAllUsers() {
  fetch('/admin/get_users')
    .then(response => response.json())
    .then(data => {
      if (data.error) {
        console.log(data.error);  // Display error message if present
      } else {
        displayUserList(data);  // Display users in the UI
      }
    })
    .catch(error => console.error('Error fetching users:', error));  // Error handling
}

// Display user list in the admin dashboard
function displayUserList(users) {
  const userTable = document.getElementById("userTable");
  userTable.innerHTML = "";  // Clear any previous entries

  users.forEach(user => {
    const row = document.createElement("tr");

    // Create table cells for username and role
    const usernameCell = document.createElement("td");
    usernameCell.textContent = user.username;
    row.appendChild(usernameCell);

    const roleCell = document.createElement("td");
    roleCell.textContent = user.role;
    row.appendChild(roleCell);

    // Create action buttons (Edit, Suspend, Delete) with event listeners
    const actionsCell = document.createElement("td");

    ["Edit", "Suspend", "Delete"].forEach(action => {
      const actionButton = document.createElement("button");
      actionButton.textContent = action;
      actionButton.classList.add("action-button", action.toLowerCase());
      actionButton.addEventListener("click", () => handleUserAction(user.username, action.toLowerCase()));
      actionsCell.appendChild(actionButton);
    });

    row.appendChild(actionsCell);
    userTable.appendChild(row);
  });
}

// Function to handle admin actions
async function handleUserAction(username, action) {
  if (action === "edit") {
     // Show the edit form on the current page
     showEditUserPage(username); // Call function to load and show the edit form
  } else {
    try {
      const response = await fetch(`/admin/${action}_user`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username })
      });

      const result = await response.json();
      alert(result.message);
      fetchAllUsers();  // Refresh the user list after action
    } catch (error) {
      console.error(`Error performing ${action} action:`, error);
    }
  }
}

// Function to show the edit form on the current page
async function showEditUserPage(username) {
  try {
    // Fetch user data
    const response = await fetch(`/admin/get_user/${username}`);
    const userData = await response.json();

    // Populate the form fields with user data
    document.getElementById("edit-username").value = userData.username;
    document.getElementById("edit-role").value = userData.role;
    document.getElementById("edit-password").value = ""; // Clear password field

     // Display the edit user page section
     document.getElementById("edit-user-page").style.display = "block";
    } catch (error) {
      console.error("Error fetching user details:", error);
    }
  }

// Event listener to handle the form submission for updating the user
document.getElementById("edit-user-form").addEventListener("submit", async function(event) {
  event.preventDefault();
  
  const username = document.getElementById("edit-username").value;
  const role = document.getElementById("edit-role").value;

  try {
    const response = await fetch(`/admin/update_user/${username}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ role })
    });
    const result = await response.json();
    alert(result.message);

    // Hide the edit form after update and refresh the user list
    document.getElementById("edit-user-page").style.display = "none";
    fetchAllUsers();
  } catch (error) {
    console.error("Error updating user:", error);
  }
});


function suspendUser(userId) {
  fetch(`/admin/suspend_user/${userId}`, {
      method: 'POST'
  })
  .then(response => response.json())
  .then(data => {
      alert(data.message);
      location.reload();  // Refresh the page to show the updated status
  })
  .catch(error => console.error('Error:', error));
}

function deleteUser(userId) {
  if (confirm("Are you sure you want to delete this user? This action cannot be undone.")) {
      fetch(`/admin/delete_user/${userId}`, {
          method: 'POST'
      })
      .then(response => response.json())
      .then(data => {
          alert(data.message);
          location.reload();  // Refresh the page to remove the deleted user from the table
      })
      .catch(error => console.error('Error:', error));
  }
}




// Handle inmate registration form submission
document.getElementById("inmateForm").addEventListener("submit", async function (e) {
  e.preventDefault();
  const formData = new FormData(this);

  try {
      const response = await fetch('/register_inmate', {
          method: 'POST',
          body: formData,
      });

      const result = await response.json();
      if (response.ok) {
          alert("Inmate registered successfully!");
      } else {
          alert("Error: " + result.error);
      }
  } catch (error) {
      console.error("Error during inmate registration:", error);
      alert("Failed to register inmate.");
  }
});


const uploadForm = document.querySelector('#uploadForm');
uploadForm.addEventListener('submit', async (event) => {
    event.preventDefault();

    const formData = new FormData();
    formData.append('file', document.querySelector('#fileInput').files[0]);

    try {
        const response = await fetch('/predict', { // Adjust if hosted externally
            method: 'POST',
            body: formData,
        });

        const result = await response.json();
        if (response.ok) {
            document.querySelector('#predictionResult').textContent = `Predictions: ${JSON.stringify(result.predictions)}`;
        } else {
            alert(`Error: ${result.error}`);
        }
    } catch (error) {
        console.error('Prediction failed:', error);
        alert('Prediction failed: ' + error.message);
    }
});


// Populate the user table in admin dashboard
function populateUserTable() {
  const userTable = document.getElementById("userTable");
  userTable.innerHTML = "";

  // Fetch users from server to populate table (assuming a route for this exists)
  fetch('/get_users')
    .then(response => response.json())
    .then(users => {
      users.forEach(user => {
        if (!user.isAdmin) {
          const row = userTable.insertRow();
          row.innerHTML = `
            <td>${user.username}</td>
            <td>${user.isAdmin ? "Admin" : "User"}</td>
            <td><button onclick="deleteUser('${user.username}')">Delete</button></td>
          `;
        }
      });
    });
}

// Delete user function
function deleteUser(username) {
  // Assuming an API endpoint for deleting users
  fetch(`/delete_user?username=${username}`, { method: 'DELETE' })
    .then(response => response.text())
    .then(message => {
      alert(message);
      populateUserTable();
    });
}

// Real-time recognition functionality with camera access
document.addEventListener("DOMContentLoaded", () => {
  const startRecognitionButton = document.getElementById("startRecognition");
  if (startRecognitionButton) {
    startRecognitionButton.addEventListener("click", () => {
      const video = document.getElementById("video");

      if (navigator.mediaDevices && navigator.mediaDevices.getUserMedia) {
        navigator.mediaDevices.getUserMedia({ video: true })
          .then(stream => {
            video.srcObject = stream;
            console.log("Camera access granted.");
          })
          .catch(err => {
            console.error("Error accessing camera:", err);
            alert("Camera access denied. Please allow camera permissions.");
          });
      } else {
        alert("Your browser does not support camera access.");
      }
    });
  } else {
    console.warn("startRecognition button not found in the DOM.");
  }
});

// Call the function when the page loads
window.onload = function() {
  // You can call any other functions here as well
  if (currentUser && currentUser.isAdmin) {
    fetchAllUsers();  // Fetch and display the users if the admin is logged in
  }
};