from playwright.sync_api import Playwright, sync_playwright, TimeoutError as PwTimeoutError
from dotenv import load_dotenv
import os
import tkinter.messagebox
import customtkinter
from customtkinter import *
import pandas as pd
from datetime import datetime, timedelta
import time
import logging
import gspread
from google.oauth2.service_account import Credentials
import re


class WouldGetOver12HoursException(Exception):
    """Raised if adding the current row's attendance would get the student above 12 hours."""


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

        self.close_to_12_check = customtkinter.BooleanVar(value=False)
        self.close_to_12_checkbox = customtkinter.CTkCheckBox(master=frame, text="Skip students close to 12 hrs?", variable=self.close_to_12_check,
                                                           onvalue=True, offvalue=False)
        self.close_to_12_checkbox.grid(row=9, column=2, pady=5)

        self.start_button = customtkinter.CTkButton(master=frame, text="Next", font=("Roboto", 14),
                                                    command=self.fields_completed_check)
        self.start_button.grid(row=10, column=2, pady=20)

    def get_entries(self):
        self.attend_type = self.radio_state.get()
        self.row_start = int(self.row_start_entry.get()) - 1
        self.url = self.google_sheet_url_entry.get()
        self.skip_close_to_12 = self.close_to_12_check.get()
        print(f'Skip below 12 = {self.skip_close_to_12}')

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
        row = 1
        column = 1
        for name in tabs:
            if row > 8:
                row = 1
                column += 1
            button = customtkinter.CTkRadioButton(master=self.frame, text=name, value=name, variable=self.radio_state)
            button.grid(row=row, column=column, sticky=W, padx=50, pady=5)
            row += 1

        self.start_button = customtkinter.CTkButton(master=self.frame, text="Next", command=self.sheet_selected_check)
        self.start_button.grid(row=9, column=2, pady=10)

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


def estimate_completion_time(df):
    num_of_entries = df['KAERS ID'].count()
    print("Num of entries: ", num_of_entries)
    rate = 175
    estimated_time = (num_of_entries - WelcWin.row_start + 1) / rate

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


def record_feedback(message: str, current_row: int):
    """Writes message parameter in 'entered?' column."""
    ws.update_cell(current_row + 2, ENTERED_COLUMN, f'{message}')


def tab_exists(title: str) -> bool:
    tab_exists: bool = wb.worksheet(title)
    return tab_exists


def create_tab(title: str, rows: int, cols: int):
    if tab_exists(title):
        print(f'A tab named {title} already exists.')
    else:
        wb.add_worksheet(title=title, rows=rows, cols=cols)
        print(f'Successfully created tab named {title}.')


def would_get_over_12_hrs(page: Playwright, KAERS_ID: float, current_row: int) -> bool:
    """Pulls student's attendance hours from KAERS. Returns boolean of whether adding
       the current row's attendance would get the student above 12 hours."""
    current_attend_hours = float(page.locator(f"[id=\"MainContent_Attendance_userControl\\?{KAERS_ID}_lblHrS\"]").inner_text(timeout=5000))
    logging.info(f"Row {current_row + 1} - Current attendance hours: {current_attend_hours}")

    if WelcWin.attend_type == "Live Attendance":
        start_time = datetime.strptime(str(df['Start Time'][current_row]), "%H:%M:%S")
        end_time = datetime.strptime(str(df['End Time'][current_row]), "%H:%M:%S")

        total_time = end_time - start_time
        secs = total_time.seconds
        attendance_to_add = secs/3600
    else:
        attendance_to_add = float(df['Total Time'][current_row])
    
    if current_attend_hours < 12 and current_attend_hours + attendance_to_add >= 12:
        return True
    else:
        return False
      
    # if 9 < current_attend_hours < 12:
    #     return True
    # else:
    #     return False


def process_completed_check():
    """Displays yes/no box with end time and copied file name. Asks if user would like to open the copied file.
     If yes, opens file."""
    finished_time = datetime.now().strftime("%H:%M")
    logging.info(f"Attendance entry complete | Started - {starting_time} | Finished - {finished_time}")


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
logging.basicConfig(level=logging.INFO, filename=f"logs/" + f"{wb.title} _ {sheet_window.ws}.log".replace('/', '.'), filemode='w',
                    format="%(asctime)s - %(levelname)s - %(message)s", datefmt="%Y-%m-%d %H:%M:%S")


# values_list = sheet.sheet1.row_values(1)
# print(values_list)

ws = wb.worksheet(f"{sheet_window.ws}")
df = pd.DataFrame(ws.get_all_records())
df = df.replace('', None)
df = df.replace('#N/A', None)
idx = df.columns.get_loc("entered?")
ENTERED_COLUMN = idx + 1

estimate_completion_time(df)

logging.info(f"\n\n~ {WelcWin.attend_type} Entry ~\n"
             f"File chosen: {wb.title}\n")
starting_time = datetime.now().strftime("%H:%M")


def run(playwright: Playwright) -> None:
    browser = playwright.chromium.launch(headless=False, args=["--start-maximized"])
    context = browser.new_context(no_viewport=True)
    page = context.new_page()

    load_dotenv(override=True)
    USERNAME = os.getenv("USERNAME")
    PASSWORD = os.getenv("PASSWORD")

    page.goto("https://kaers.ky.gov/SignIn.aspx")
    page.locator("#rtxtUserName").click()
    page.locator("#rtxtUserName").fill(USERNAME)
    page.locator("#rtxtPassword").click()
    page.locator("#rtxtPassword").fill(PASSWORD)
    page.get_by_role("button", name="Sign in").click()
    time.sleep(8)

    if WelcWin.row_start:
        current_row = WelcWin.row_start
    else:
        current_row = 0

    separated_list = []

    for column in df['Row ID'].tolist():

        try:
            #TODO: catch when session expires
            # if "Session Expired" in url:
                #log "Session expired"
                #input("Session has expired. Please log into KAERS again and then push enter: ")

            
            if pd.isna(df['KAERS ID'][current_row]):
                if pd.isna(df['First Name'][current_row]) and pd.isna(df['Last Name'][current_row]):
                        logging.info(f'Blank row found. Program stopped. Row {current_row}\n')
                        break
                else:
                    logging.warning(f"Blank ID: Row {current_row + 1}")
                    record_feedback(message='Blank ID', current_row=current_row)
                    continue

            if WelcWin.attend_type == "Distance Learning":
                if df['Total Time'][current_row] == 0:
                    logging.info(f"Skipped (time = 0): Row {current_row + 1}")
                    record_feedback(message='Skipped (time = 0)', current_row=current_row)
                    continue

            KAERS_ID = int(df['KAERS ID'][current_row])
            
            if str(KAERS_ID) in separated_list:
                logging.warning(f"SEPARATED (skipped): Row {current_row + 1}")
                record_feedback(message='Separated (skipped)', current_row=current_row)
                continue
           
            page.goto(f"https://kaers.ky.gov/StudentGeneral.aspx?student_record_id={KAERS_ID}")
            page.get_by_role("link", name="Tests").click()
            try:
                page.get_by_role("link", name="Enrollment").click()
                time.sleep(1)
                page.locator("#ctl00_MainContent_RadTabStripEnrollmentVerticalTab").get_by_role("link", name="Attendance").click(timeout=5000)
            except PwTimeoutError:
                separated_list.append(str(KAERS_ID))
                logging.warning(f"SEPARATED: Row {current_row + 1}; Separated ID's: {separated_list}")
                record_feedback(message='Separated', current_row=current_row)
                # create_tab(title='Separated', rows=500, cols=10)
                continue

            time.sleep(.5)

            if WelcWin.skip_close_to_12:
                if would_get_over_12_hrs(page, KAERS_ID, current_row):
                    raise WouldGetOver12HoursException

            attendance_type = str.title(df['Attendance Type'][current_row])
            attendance_date = str(df['Attendance Date'][current_row])
            page.locator(f"[id=\"ctl00_MainContent_Attendance_userControl\\?{KAERS_ID}_rcbAttendType_Arrow\"]").click()
            page.locator(f"[id=\"ctl00_MainContent_Attendance_userControl\\?{KAERS_ID}_rcbAttendType_DropDown\"]").get_by_text(attendance_type).click()
            page.locator(f"[id=\"ctl00_MainContent_Attendance_userControl\\?{KAERS_ID}_rdpAttendDate_dateInput\"]").click()
            page.locator(f"[id=\"ctl00_MainContent_Attendance_userControl\\?{KAERS_ID}_rdpAttendDate_dateInput\"]").fill(attendance_date)
            page.locator("#ctl00_MainContent_RadTabStripEnrollmentVerticalTab").get_by_role("link", name="Attendance").click(timeout=3000)
            time.sleep(1)
           
            if WelcWin.attend_type == "Live Attendance":
                start_time = str(df['Start Time'][current_row])
                end_time = str(df['End Time'][current_row])
                page.locator(f"[id=\"ctl00_MainContent_Attendance_userControl\\?{KAERS_ID}_rtpStartTime_dateInput\"]").click()
                page.locator(f"[id=\"ctl00_MainContent_Attendance_userControl\\?{KAERS_ID}_rtpStartTime_dateInput\"]").fill(start_time)
                page.locator(f"[id=\"ctl00_MainContent_Attendance_userControl\\?{KAERS_ID}_rtpEndTime_dateInput\"]").click()
                page.locator(f"[id=\"ctl00_MainContent_Attendance_userControl\\?{KAERS_ID}_rtpEndTime_dateInput\"]").fill(end_time)
           
            else:
                product = str(df['Product'][current_row])
                total_time = str(df['Total Time'][current_row])
                page.locator(f"[id=\"ctl00_MainContent_Attendance_userControl\\?{KAERS_ID}_rcbProducts_Arrow\"]").click()
                time.sleep(.5)
                page.get_by_text(product).click()
                page.get_by_role("textbox", name="Total time should not be more than 20 hours!").click()
                page.get_by_role("textbox", name="Total time should not be more than 20 hours!").fill(total_time)

            if pd.notna(df['Site'][current_row]):
                site = str(df['Site'][current_row])
                page.locator(f"[id=\"ctl00_MainContent_Attendance_userControl\\?{KAERS_ID}_rcbAttendSite_Arrow\"]").click()
                try:
                    page.locator(f"[id=\"ctl00_MainContent_Attendance_userControl\\?{KAERS_ID}_rcbAttendSite_DropDown\"]").get_by_text(site).click()
                except PwTimeoutError:
                    logging.warning(f"Enrolled somewhere else? Row {current_row + 1}")
                    record_feedback(message="Error: Enrolled somewhere else?", current_row=current_row)
                    continue
            # page.get_by_role("cell", name="Approve :", exact=True).click()

            page.get_by_role("button", name="Save").click()
            time.sleep(1)

            try:
                page.get_by_text("Attendance has been Saved.").click(timeout=8000)
                # page.locator(f'[id=\"ct100_MainContent_Attendance_userControl\\?{KAERS_ID}_lblMsg"]').click(timeout=8000)
                logging.info(f"Successfully entered: Row {current_row + 1}")
                record_feedback(message='✅', current_row=current_row)
            except PwTimeoutError:
                logging.warning(f"Date or time rejected: Row {current_row + 1}")
                record_feedback(message='Error: Date or time rejected', current_row=current_row)
        

        except WouldGetOver12HoursException as err:
            logging.warning(f"{err} - Entry skipped: Row {current_row + 1} | Entry would get student above 12hrs")
            record_feedback(message=f'Skipped (entry would get student above 12hrs)', current_row=current_row)


        except PwTimeoutError as err:
            logging.error(f"{err} - Entry failed: Row {current_row + 1}")
            record_feedback(message='Error: Something timed out', current_row=current_row)


        except ValueError as err:
            logging.error(f"{err} - Entry failed: Row {current_row + 1}")
            record_feedback(message='Error: Invalid info', current_row=current_row)
        

        # except (KeyError, ValueError):
        #     if str(KAERS_ID) == '#N/A':
        #         logging.warning(f"ID #N/A: Row {count + 1}")
        #         record_feedback(message='Error: Invalid ID', current_row=count)
        #         continue
        #     else:
        #         logging.info(f"Blank ID found. Stopping program. Row {count + 2}")
        #         break


        finally:
            current_row += 1


    # ---------------------
    context.close()
    browser.close()


with sync_playwright() as playwright:
    run(playwright)


process_completed_check()
