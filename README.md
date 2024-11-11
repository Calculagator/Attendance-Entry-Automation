# Attendance Entry Automation

## ‼️First-Time Setup Instructions
### Google Sheets
This automation connects directly to Google Sheets.
1. Before you start, make sure you're logged into a *personal Gmail* account. Using your work email will cause some hiccups.
2. Follow the instructions in this video from 1:50 - 6:50.
    - If you are required to select an organization, make sure you're logged into a *personal Gmail* account.
    - As said in the video, do not share the credentials file with others.
3. 

1. Clone the repo to your machine.
2. Open a code editor such as Visual Studio Code. You may instead use PowerShell (Windows) or Terminal (Mac).
3. Open the project folder.
    - Click File > Open Folder > Select the folder "Attendance-Entry-Automation"
4. Create a virtual environment.
    - Click View > Terminal
    - Type  `python -m venv venv` or `python3 -m venv venv`
5. Activate the virtual environment.
    - Windows:  `venv\Scripts\activate`
    - Mac:  `source venv/bin/activate`
6. Install required packages and dependencies.
   - Type   `pip install -r requirements.txt`
7. In the "KAERS-Enrollment-Automation" folder, create a **.env** file for your KAERS login credentials.
   - Open the .env file and type:
       - `USERNAME = 'your KAERS username'`
       - `PASSWORD = 'your KAERS password'`
8. Deactivate the virtual environment.
   - Type `deactivate`

