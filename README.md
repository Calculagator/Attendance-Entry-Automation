# Attendance Entry Automation

## Basic Windows installation (prereqs)
Install these first:

1. **VS Code + Git (recommended via Ninite)**
   - Go to https://ninite.com/
   - Select:
     - **Visual Studio Code**
     - **Git**
     - **Python x64 3**
   - Download and run the installer.


## ‼️First-Time Setup Instructions
1. Clone the repo to your machine.
2. Open a code editor such as Visual Studio Code. 
3. Open the project folder.
    - Click File > Open Folder > Select the folder "Attendance-Entry-Automation"

Before we continue, we need to set up our connection to Google Sheets.

4. You'll need to be logged into a *personal Gmail* account to continue. Using your work email will cause some hiccups.
5. Follow the instructions in [this video](https://youtu.be/zCEJurLGFRk?t=110) only from 1:50 - 6:50. (The sections you need to watch are titled "Google Cloud Setup" and "Generating a Service Account".)
   - Create/sign in to a Google Cloud account (use a *personal Gmail* account).
   - Create a new Google Cloud project (or select an existing one).
   - Enable the **Google Sheets API** for your project:
     - https://console.cloud.google.com/marketplace/product/google/sheets.googleapis.com
   - On the Google Sheets API page (after enabling), click **Create credentials** and follow the prompts to create a **Service Account**, then download the **JSON key** (this is your credentials file).
     - At this point, I (Joel A) believe the video is incorrect. It directs you to add the "editor" role to your service account. I think that it should be assigned no roles or special permissions. 
     - As said in the video, do not share the credentials file with others.
   - ⭐⭐I highly recommend **bookmarking the webpage** that has your API's email so you can quickly pull it up. You'll need that email every time you want the automation to run a new sheet.
   - **JoelA- What about sharing the whole drive?**
6. Put the downloaded JSON key file into the `Attendance-Entry-Automation` folder and rename it to `credentials.json`.

Now we'll head back to Visual Studio Code.

### macOS note (Tkinter)
This project uses `customtkinter`, which requires Python's built-in Tkinter module.

Before installing the Python packages, verify Tkinter works:

```zsh
python3 -m tkinter
```

- If a small demo window opens, you're good.
- If you get `ModuleNotFoundError: No module named '_tkinter'`, your current Python installation was built without Tk.
    - If you're using Homebrew Python 

```zsh
brew update
# may need to adjust to current python version
brew install python-tk@3.13

# Verify Tkinter works
python3.13 -m tkinter
```

After switching Python installs, recreate your virtual environment so it uses the fixed interpreter.

7. Create a virtual environment.
    - Click View > Terminal
    - Windows (recommended): `py -m venv venv`
    - Mac: `python3 -m venv venv` (or `python -m venv venv`)
8. Activate the virtual environment.
    - Windows:  `venv\Scripts\activate`
    - Mac:  `source ./venv/bin/activate`
9. Install required packages and dependencies.
   - Type   `pip install -r requirements.txt`
10. Install Playwright browsers (required before first use):
   - `python -m playwright install`
   - (or `playwright install`)
11.  In the `Attendance-Entry-Automation` folder, create a `.env` file for your KAERS login credentials.
     - Copy the template file and rename it to `.env`:
         - Windows: `copy .env.template .env`
         - Mac/Linux: `cp .env.template .env`
     - Open `.env` and set your values:
         - `USERNAME=your_kaers_username`
         - `PASSWORD=your_kaers_password`


The automation is all set up now. You're ready to go. 🙂