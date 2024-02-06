from playwright.sync_api import Playwright, sync_playwright, expect, TimeoutError as PwTimeoutError
from dotenv import load_dotenv
import os
import tkinter.messagebox
import customtkinter
from customtkinter import *
from openpyxl import load_workbook
import pandas as pd
from datetime import datetime, timedelta
import time
import logging
from logging import FileHandler
import gspread
from google.oauth2.service_account import Credentials
import re


class WelcomeWindow:

    def __init__(self):

        self.attend_type = None
        self.row_start = None
        self.welcome_label = customtkinter.CTkLabel(master=frame, text="Welcome to the Attendance\n Entry Program!",
                                                    font=("Roboto", 14, "bold"))
        self.welcome_label.grid(row=0, column=2, pady=15)
        self.type_label = customtkinter.CTkLabel(master=frame, text="Attendance type:")
        self.type_label.grid(row=1, column=1)

        self.options = [
            "Live Attendance",
            "Distance Learning",
            "Personal Contact (CCN)"
        ]

        self.radio_state = StringVar(value="None")
        i = 0
        for name in self.options:
            button = customtkinter.CTkRadioButton(master=frame, text=name, font=("Roboto", 14), value=name,
                                                  variable=self.radio_state)
            button.grid(row=1 + i, column=2, sticky="W", pady=5)
            i += 1

        self.spreadsheet_label = customtkinter.CTkLabel(master=frame, text="Google Sheet URL:")
        self.spreadsheet_label.grid(row=5, column=1)

        self.google_sheet_url_entry = customtkinter.CTkEntry(master=frame, width=150, font=("Roboto", 13))
        self.google_sheet_url_entry.grid(row=5, column=2)

        self.row_start_label = customtkinter.CTkLabel(master=frame, text="Start at Row ID:")
        self.row_start_label.grid(row=8, column=1, pady=5)
        self.row_start_entry = customtkinter.CTkEntry(master=frame, width=150, font=("Roboto", 13))
        self.row_start_entry.grid(row=8, column=2, pady=5)

        self.start_button = customtkinter.CTkButton(master=frame, text="Next", font=("Roboto", 14),
                                                    command=self.fields_completed_check)
        self.start_button.grid(row=9, column=2, pady=20)

    def get_entries(self):
        self.attend_type = self.radio_state.get()
        self.row_start = int(self.row_start_entry.get()) - 1
        self.url = self.google_sheet_url_entry.get()

    def fields_completed_check(self):
        """If any field is empty, gives a messagebox. If all fields are filled, gathers user's selections and closes window."""
        if str(self.radio_state.get()) == "0" or not self.google_sheet_url_entry:
            tkinter.messagebox.showinfo(title="Oops!", message="Please make sure all fields are completed.")
        else:
            self.get_entries()
            window.destroy()

class SelectSheetWindow:

    def __init__(self):
        self.ws = None
        self.frame = customtkinter.CTkFrame(master=window)
        self.frame.grid()
        global wb

        self.select_sheet_label = customtkinter.CTkLabel(master=self.frame,
                                                         text="Select the tab you want to use:",
                                                         font=("Roboto", 14, "bold"))
        self.select_sheet_label.grid(row=0, column=0, sticky=W)
        self.select_sheet_label.configure(padx=10, pady=20)

        self.radio_state = StringVar(value="None")
        i = 0
        for name in tabs:
            i += 1
            button = customtkinter.CTkRadioButton(master=self.frame, text=name, value=name, variable=self.radio_state)
            button.grid(sticky=W, padx=50, pady=5)

        self.start_button = customtkinter.CTkButton(master=self.frame, text="Next", command=self.sheet_selected_check)
        self.start_button.grid(row=i + 1, pady=10)

    def sheet_selected_check(self):
        """Checks if a sheet was chosen. If not, displays "Oops" message box. Otherwise, saves selected sheet as variable."""
        self.ws = self.radio_state.get()
        if self.ws == "None":
            tkinter.messagebox.showinfo(title="Oops!", message="Please select a sheet.")
        else:
            print(self.ws)
            window.destroy()

def on_close():
    """If user clicks close button, gives warning message about closing program."""
    # TODO: focus on No button (right now it focuses on Yes)
    close = tkinter.messagebox.askokcancel(title="Close", message="Would you like to close the program?")
    if close:
        sys.exit()


def estimate_completion_time():
    global df
    row_count = df['KAERS ID'].count()
    print("Num of rows: ", row_count)
    rate = 175
    estimated_time = (row_count - WelcWin.row_start + 1) / rate

    if estimated_time < 1:
        hours = 0
        minutes = 60 * (estimated_time % 1)
    else:
        hours = estimated_time
        minutes = 60 * (hours % 1)

    add_time = timedelta(hours=hours, minutes=minutes)
    estimate_finish_time = (datetime.now() + add_time).strftime("%H:%M")
    logging.info(f"Estimated time = {estimate_finish_time}")

    yes_no_box = tkinter.messagebox.askyesno(title="Estimated Time",
                                             message=f"This process is estimated to finish at {estimate_finish_time}.\n\n"
                                                     f"Start the program?")
    if not yes_no_box:
        sys.exit()


# Opens Welcome Window: user selects attendance type, file, copied file name & enters login info
window = CTk()
customtkinter.set_appearance_mode("dark")
customtkinter.set_default_color_theme("dark-blue")
frame = customtkinter.CTkFrame(master=window)
frame.grid()
window.title("Attendance Entry")
window.minsize(width=300, height=300)
window.config(padx=25, pady=25)
WelcWin = WelcomeWindow()
window.protocol("WM_DELETE_WINDOW", on_close)
window.mainloop()
# https://docs.google.com/spreadsheets/d/1Dxn1vYr6Ey3ZzGz4M0XsCUJMDcr7u2UiCvC5eEE3pzc/edit#gid=480225743

# ~~~

scopes = ['https://www.googleapis.com/auth/spreadsheets']

creds = Credentials.from_service_account_file("credentials.json", scopes=scopes)
client = gspread.authorize(creds)

url = WelcWin.url
text_blob = (re.split('spreadsheets/d/', url)[1])
wb_id = re.split('/edit', text_blob)[0]
wb = client.open_by_key(wb_id)

tabs = list(map(lambda x: x.title, wb.worksheets()))
print(tabs)
print(wb.title)

# Opens Select Sheet Window; user selects sheet to use within the spreadsheet
window = CTk()
window.title("Select sheet")
window.minsize(width=200, height=200)
window.config(padx=25, pady=10)
sheet_window = SelectSheetWindow()
window.protocol("WM_DELETE_WINDOW", on_close)
window.mainloop()

# logger = logging.getLogger(f'{wb.title}.log')
# log_file_path = 'logs'
# file_handler = FileHandler(log_file_path)
# formatter = logging.Formatter(format="%(asctime)s - %(levelname)s - %(message)s",
#                               datefmt="%Y-%m-%d %H:%M:%S")
# file_handler.setFormatter(formatter)
# logger.addHandler(file_handler)
logging.basicConfig(level=logging.INFO, filename=f"logs/" + f"{wb.title}.log".replace('/', '.'), filemode='w',
                    format="%(asctime)s - %(levelname)s - %(message)s", datefmt="%Y-%m-%d %H:%M:%S")


# values_list = sheet.sheet1.row_values(1)
# print(values_list)

ws = wb.worksheet(f"{sheet_window.ws}")
df = pd.DataFrame(ws.get_all_records())
idx = df.columns.get_loc("entered?")
ENTERED_COLUMN = idx + 1

estimate_completion_time()

logging.info(f"\n\n~ {WelcWin.attend_type} Entry ~\n"
             f"File chosen: {wb.title}\n")
starting_time = datetime.now().strftime("%H:%M")

