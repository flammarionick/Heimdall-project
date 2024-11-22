HEIMDALL PROJECT
A real-time facial recognition and criminal detection system designed to improve security at high-risk locations.

FEATURES
Real-time facial recognition using live camera feeds.
Secure admin and user management system.
Inmate database with profile management.
Dynamic AI model integration for facial recognition.
Live Demo
The project is deployed on Render:
URL: https://heimdall-project.onrender.com

Note:
Due to time and financial constraints, I was not able to find a free deployment platform that could support the large AI model. As a result, the AI functionality does not work on the public URL. However, you can set it up locally to experience the full functionality.

GETTING STARTED
Follow these steps to set up the project locally and explore its features.

PREREQUISITES
Python 3.10 or higher installed on your system.
Git installed on your system.
A virtual environment tool (e.g., venv or virtualenv).
Required Python packages listed in requirements.txt.
A supported browser for viewing the web application.

SETUP INSTRUCTIONS
Step 1: Clone the Repository

git clone https://github.com/FLAMMARYON/Heimdall-project.git


Step 2: Set Up a Virtual Environment
Create and activate a virtual environment to manage dependencies:
python -m venv venv
venv\Scripts\activate


Step 3: Install Dependencies
Install the required Python packages:
pip install -r requirements.txt

Step 4: Configure the Application
Database Configuration:

Ensure that the database file 'inmate_database.db' is properly configured in the project directory.
If it does not exist, create it by running the Flask app.

Environment Variables:
Create a .env file in the project root and set the following variables:
FLASK_APP=app.py
FLASK_ENV=development
SECRET_KEY=your_secret_key_here
DATABASE_PATH=inmate_database.db

Step 5: Prepare Static Assets
Ensure all static files are in the correct directory structure under static/. This includes JavaScript, CSS, and uploaded images.

Step 6: Run the Application Locally
Start the Flask development server:
flask run
The application will be accessible at http://127.0.0.1:5000.

Step 7: Testing the AI Functionality
To test the AI functionality, ensure you have the model and data files which you can download in the models folder of this repository

Place your AI model file in the models directory.
Ensure the file paths for datasets are correctly configured in your code.
For real-time recognition, ensure your webcam is enabled and functional.

Usage Instructions
Accessing the Web App:

Visit http://127.0.0.1:5000 in your browser.
Log in with default admin credentials.

AI Model Integration:
Use the "Start Recognition" button to activate the webcam and detect faces in real-time.
Upload an image for facial recognition to compare with registered profiles.
