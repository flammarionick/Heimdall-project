// User storage and current session
// User storage and session management
let users = [{ username: "Admin", password: "admin123", isAdmin: true }];
let currentUser = null;

// Function to display specific pages with access control
function showPage(pageId) {
  const pages = document.querySelectorAll(".page");
  pages.forEach(page => page.style.display = "none");
  document.getElementById(pageId).style.display = "block";

  // Restrict access to admin dashboard for non-admins
  if (pageId === 'admin-dashboard' && (!currentUser || !currentUser.isAdmin)) {
    alert("Admin access only. Please login as admin.");
    showPage('login');
  } else if (pageId === 'admin-dashboard') {
    populateUserTable();
  }
}

// Handle login functionality
document.getElementById("loginForm").addEventListener("submit", (e) => {
  e.preventDefault();
  const username = document.getElementById("username").value;
  const password = document.getElementById("password").value;

  // Authenticate user
  currentUser = users.find(user => user.username === username && user.password === password);
  if (currentUser) {
    alert("Login successful!");
    showPage(currentUser.isAdmin ? 'admin-dashboard' : 'register-inmate');
  } else {
    alert("Invalid credentials, please try again.");
  }
});

// Handle inmate registration form submission
document.getElementById("inmateForm").addEventListener("submit", async function (e) {
  e.preventDefault();

  let formData = new FormData(this);  // Collect the form data

  try {
    // Send the form data to the Flask backend for processing
    const response = await fetch('/register', {
      method: 'POST',
      body: formData
    });

    const result = await response.text();
    alert(result);  // Display the result from the server
  } catch (error) {
    console.error("Error during inmate registration:", error);
    alert("Failed to register inmate.");
  }
});

// Create new user form handler
document.getElementById("createUserForm").addEventListener("submit", (e) => {
  e.preventDefault();
  const newUsername = document.getElementById("newUsername").value;
  const newPassword = document.getElementById("newPassword").value;

  users.push({ username: newUsername, password: newPassword, isAdmin: false });
  alert(`User ${newUsername} created successfully!`);
  showPage('admin-dashboard');
});

// Update admin credentials form handler
document.getElementById("updateAdminForm").addEventListener("submit", (e) => {
  e.preventDefault();
  const newAdminUsername = document.getElementById("adminUsername").value;
  const newAdminPassword = document.getElementById("adminPassword").value;

  const adminUser = users.find(user => user.isAdmin);
  adminUser.username = newAdminUsername;
  adminUser.password = newAdminPassword;
  alert("Admin credentials updated successfully!");
  showPage('admin-dashboard');
});

// Populate the user table in admin dashboard
function populateUserTable() {
  const userTable = document.getElementById("userTable");
  userTable.innerHTML = "";  // Clear existing rows

  users.forEach(user => {
    if (!user.isAdmin) { // Only display non-admin users
      const row = userTable.insertRow();
      row.innerHTML = `
        <td>${user.username}</td>
        <td>${user.isAdmin ? "Admin" : "User"}</td>
        <td><button onclick="deleteUser('${user.username}')">Delete</button></td>
      `;
    }
  });
}

// Delete user function
function deleteUser(username) {
  users = users.filter(user => user.username !== username);
  alert(`User ${username} deleted successfully.`);
  populateUserTable();
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
