# Attendance Entry Automation

## ‼️First-Time Setup Instructions
1. Clone the repo to your machine.
2. Open a code editor such as Visual Studio Code. You may instead use PowerShell (Windows) or Terminal (Mac).
3. Open the project folder.
    - Click File > Open Folder > Select the folder "Attendance-Entry-Automation"

Before we continue, we need to set up our connection to Google Sheets.

4. You'll need to be logged into a *personal Gmail* account to continue. Using your work email will cause some hiccups.
5. Follow the instructions in [this video](https://youtu.be/zCEJurLGFRk?t=110) only from 1:50 - 6:50. (The sections you need to watch are titled "Google Cloud Setup" and "Generating a Service Account".)
    - If you're required to select an organization, make sure you're logged into a *personal Gmail* account.
    - As said in the video, do not share the credentials file with others.
    - ⭐⭐I highly recommend **bookmarking the webpage** that has your API's email so you can quickly pull it up. You'll need that email everytime you want the automation to run a new sheet.
6. For the credentials file you downloaded, make sure you rename it as `credentials.json`.

Now we'll head back to Visual Studio Code.

7. Create a virtual environment.
    - Click View > Terminal
    - Type  `python -m venv venv` or `python3 -m venv venv`
8. Activate the virtual environment.
    - Windows:  `venv\Scripts\activate`
    - Mac:  `source venv/bin/activate`
9. Install required packages and dependencies.
   - Type   `pip install -r requirements.txt`
10. In the "KAERS-Enrollment-Automation" folder, create a `.env` file for your KAERS login credentials.
    - File > New File > On the left, right click the new untitled file > Rename > type `.env`
    - Open the `.env` file and type:
       - `USERNAME = 'your KAERS username'`
       - `PASSWORD = 'your KAERS password'`
12. Deactivate the virtual environment.
    - Type `deactivate`

The automation is all set up now. You're ready to go. 🙂

## How to use the Automation
### 📄 What You'll Need
- Visual Studio Code open
- The Attendance-Entry-Automation folder open in Visual Studio Code
- The attendance spreadsheet Google Sheet you want to enter open in your web browser. (The spreadsheet must be uploaded to Google Drive for the automation to work).
- Your Google Sheets API email

### 🖇️ Share the Attendance Spreadsheet with your Sheets API
1. Copy your Google Sheets API email.
2. Share your attendance spreadsheet Google Sheet with your API email.
   - Open your spreadsheet in Sheets
   - Just like you'd share a file with a coworker, on the right click Share and paste your API email
       - Make sure "Editor" is selected as the role
       - The Notify checkbox isn't important
   - Click Send
       - If a warning appears, click Share Anyway

### ⚙️ Turn On the Automation
1. With the Attendance-Entry-Automation folder open in Visual Studio Code, select and run the `main.py` file (click the triangle Play button on the right, or right-click `main.py` and choose "Run Python File in Terminal").
2. A window will appear with several options.
   - Select the type of attendance (live attendance, distance learning, etc.)
   - Go to the attendance spreadsheet in Google Sheets, copy the entire URL, and paste it into the automation window box labelled "Google Sheet URL:"
   - You have the option to check yes/no if you want to manage attendance for students under 12 hours
   - Click OK
3. A second window will appear.
   - Choose the tab from that spreadsheet you want to enter (they're usually named "Live Attendance" or "Distance Learning")
   - Enter the Row ID
       - If you're starting from the top (i.e., you want to run the whole report), type 1.
       - If you're wanting to start somewhere else in the report, just type the Row ID number of where you want to start.
       - Make sure you enter the Row ID number (look in the "Row ID" column) and not the row number
   - Click START
4. The automation will open a browser window, log in to KAERS using the credentials you specified in the `.env` file, and begin entering attendance.
5. The automation will write on the attendance spreadsheet Google Sheet under the "entered?" column as it goes, so its progress can be seen in real-time.

### 🏁 When the Automation finishes
When the automation is done, just go to the attendance spreadsheet in Google Sheets. The results are in the entered? column.





