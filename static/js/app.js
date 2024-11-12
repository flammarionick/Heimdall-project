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
      populateUserTable();
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






// Handle inmate registration form submission
document.getElementById("inmateForm").addEventListener("submit", async function (e) {
  e.preventDefault();
  let formData = new FormData(this);

  try {
    const response = await fetch('/register', {
      method: 'POST',
      body: formData
    });

    const result = await response.text();
    alert(result);
  } catch (error) {
    console.error("Error during inmate registration:", error);
    alert("Failed to register inmate.");
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
document.getElementById("startRecognition").addEventListener("click", () => {
  const video = document.getElementById("video");

  if (navigator.mediaDevices && navigator.mediaDevices.getUserMedia) {
    navigator.mediaDevices.getUserMedia({ video: true })
      .then(stream => {
        video.srcObject = stream;
      })
      .catch(err => {
        console.error("Error accessing camera: ", err);
        alert("Camera access denied. Please allow camera permissions.");
      });
  } else {
    alert("Your browser does not support camera access.");
  }
});







