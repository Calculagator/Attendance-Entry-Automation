import gspread.utils
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
from gspread import exceptions
from google.oauth2.service_account import Credentials
import re
from openpyxl import load_workbook


class WouldGetOver12HoursException(Exception):
    """Raised if adding the current row's attendance would get the student above 12 hours."""


class TestOrientationAlreadyEnteredException(Exception):
    """Raised if their test attendance hours (Orientation/Intake) has already been entered in KAERS."""


class WelcomeWindow:

    def __init__(self):

        self.attend_type = None
        self.row_start = None
        self.welcome_label = customtkinter.CTkLabel(master=frame, text="Attendance Entry Program",
                                                    font=("Roboto", 14, "bold"))
        self.welcome_label.grid(row=0, column=2, pady=15)
        self.type_label = customtkinter.CTkLabel(master=frame, text="Attendance type:")
        self.type_label.grid(row=1, column=1)

        self.options = [
            "Live Attendance",
            "Distance Learning",
            "Orientation/Intake",
            "CCN - Personal Contact"
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

        self.close_to_12_check = customtkinter.BooleanVar(value=False)
        self.close_to_12_checkbox = customtkinter.CTkCheckBox(master=frame, text="Skip students that would get above 12 hrs?", variable=self.close_to_12_check,
                                                           onvalue=True, offvalue=False)
        self.close_to_12_checkbox.grid(row=9, column=2, pady=5)

        # self.spreadsheet_label = customtkinter.CTkLabel(master=frame, text="Students to\nbypass 12 hr skip")
        # self.spreadsheet_label.grid(row=10, column=1)

        # self.chosen_sheet_label = customtkinter.CTkLabel(master=frame, text="[file name will display here]")
        # self.chosen_sheet_label.grid(row=10, column=2)

        # self.choose_file_button = customtkinter.CTkButton(master=frame, width=100, text="Choose file",
        #                                                   command=self.choose_file)
        # self.choose_file_button.grid(row=10, column=3)

        # self.enter_test_orientation_check = customtkinter.BooleanVar(value=False)
        # self.enter_test_orientation_checkbox = customtkinter.CTkCheckBox(master=frame, text="Is this Orientation/Intake attendance?", variable=self.enter_test_orientation_check,
        #                                                    onvalue=True, offvalue=False)
        # self.enter_test_orientation_checkbox.grid(row=10, column=2, pady=5)

        self.start_button = customtkinter.CTkButton(master=frame, text="Next", font=("Roboto", 14),
                                                    command=self.fields_completed_check)
        self.start_button.grid(row=11, column=2, pady=20)

    # def choose_file(self):
    #     self.file_path = filedialog.askopenfilename(
    #         initialdir="C:\\Users",
    #         title="Choose a spreadsheet",
    #         filetypes=(("Excel Files", "*.xlsx*"),))
    #     if self.file_path:
    #         self.file_name = os.path.basename(self.file_path)
    #         self.chosen_sheet_label.configure(text=f"{self.file_name}")

    def get_entries(self):
        self.attend_type = self.radio_state.get()
        self.url = self.google_sheet_url_entry.get()
        self.skip_close_to_12 = self.close_to_12_check.get()
        # self.should_enter_test_orientation = self.enter_test_orientation_check.get()
        print(f'Skip getting students past 12? -> {self.skip_close_to_12}')
        # print(f'Enter test/orientation hours? -> {self.should_enter_test_orientation}')

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

        self.row_start_label = customtkinter.CTkLabel(master=self.frame, text="Start at Row ID:")
        self.row_start_label.grid(row=9, column=0, pady=10)

        self.row_start_entry = customtkinter.CTkEntry(master=self.frame, width=150, font=("Roboto", 13))
        self.row_start_entry.grid(row=9, column=1, pady=10)

        self.start_button = customtkinter.CTkButton(master=self.frame, text="START", command=self.sheet_selected_check)
        self.start_button.grid(row=10, column=2, pady=10)

    def sheet_selected_check(self):
        """Checks if a sheet was chosen. If not, displays "Oops" message box. Otherwise, saves selected sheet as variable."""
        self.ws = self.radio_state.get()
        self.row_start = int(self.row_start_entry.get()) - 1
        if self.ws == "None":
            tkinter.messagebox.showinfo(title="Oops!", message="Please select a sheet.")
        else:
            print(self.ws)
            window.destroy()


def user_has_MSG_list() -> bool:
    """Asks if user has an Excel file of MSG students. User replies 'Y' or 'N'."""
    valid_response = False
    while valid_response == False:
        has_MSG_list = str.upper(input("Do you have a list of students who you want to get above 12 hrs?\nPlease type Y or N and push Enter: "))
        if (has_MSG_list == 'Y' or has_MSG_list == 'N'):
            valid_response = True
    
    if has_MSG_list == 'Y':
        return True
    else:
        return False


def get_MSG_student_list() -> list:
    """User chooses Excel file of MSG students. Converts KAERS ID column to a list.
    The desired tab in the Excel file must be named 'Sheet1'."""
    file_path = filedialog.askopenfilename(
                initialdir="C:\\Users",
                title="Choose a spreadsheet",
                filetypes=(("Excel Files", "*.xlsx*"),))

    students_to_enter_df = pd.read_excel(file_path, 'Sheet1')
    students_to_enter_list = students_to_enter_df['KAERS ID'].fillna(0).astype(int).tolist()

    return students_to_enter_list


def on_close():
    """If user clicks close button, gives warning message about closing program."""
    close = tkinter.messagebox.askokcancel(title="Close", message="Would you like to close the program?")
    if close:
        sys.exit()


# def estimate_completion_time(df):
#     num_of_entries = df['KAERS ID'].count()
#     print("Num of entries: ", num_of_entries)
#     rate = 120
#     estimated_time = (num_of_entries - WelcWin.row_start + 1) / rate

#     if estimated_time < 1:
#         hours = 0
#         minutes = 60 * (estimated_time % 1)
#     else:
#         hours = estimated_time
#         minutes = 60 * (hours % 1)

#     add_time = timedelta(hours=hours, minutes=minutes)
#     estimate_finish_time = (datetime.now() + add_time).strftime("%H:%M")

#     yes_no_box = tkinter.messagebox.askyesno(title="Estimated Time",
#                                              message=f"This process is estimated to finish at {estimate_finish_time}.\n\n"
#                                                      f"Start the program?")
#     if not yes_no_box:
#         sys.exit()

#     return estimate_finish_time


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


def create_log(log_path: str) -> str:
    """Creates log with version number to prevent overwriting logs."""
    log_exists = os.path.isfile(log_path)
    version_number = 2

    while log_exists:
        log_path = log_path.replace(f" ver{str(version_number - 1)}", "")
        log_path = log_path + " ver" + str(version_number)
        version_number += 1
        log_exists = os.path.isfile(log_path)

    return log_path


def get_enroll_status(page: Playwright, current_row) -> str:
    """Returns student's enrollment status from profile page.
       If not enrolled, records status."""
    enroll_status = page.locator(f"[id=\"lblStatus\"]").inner_text()

    if enroll_status != 'ENROLLED':
        logging.warning(f"{enroll_status}: Row {current_row + 1}")
        record_feedback(message=f'{enroll_status}', current_row=current_row)

    return enroll_status


def un_separate(page: Playwright, KAERS_ID: str):
    """Un-separates a student: Unchecks the 'Released' box and clicks Update,
       which should change the student's status to ENROLLED."""
    page.get_by_role("button", name="Edit Enrollment").first.click(timeout=5000)
    time.sleep(3)
    page.locator("#ctl00_MainContent_RadTabStripEnrollmentVerticalTab").get_by_role("link", name="Enrollment").click(timeout=5000)
    page.locator(f"[id=\"MainContent_Enrollment_userControl\\?{KAERS_ID}_chkReleased\"]").uncheck(timeout=3000)
    time.sleep(.5)
    page.get_by_role("button", name="Update").click(timeout=3000)
    time.sleep(8)


def check_if_test_orientation_entered(page: Playwright, KAERS_ID: float) -> bool:
    try:
        page.locator(f"[id=\"ctl00_MainContent_Attendance_userControl\\?{KAERS_ID}_rgAttendance_ctl00_ctl03_ctl01_PageSizeComboBox_Arrow\"]").click(timeout=5000)
        time.sleep(1)
        page.locator(f"[id=\"ctl00_MainContent_Attendance_userControl\\?{KAERS_ID}_rgAttendance_ctl00_ctl03_ctl01_PageSizeComboBox_DropDown\"]").get_by_text("50").click()
        time.sleep(5)
        page.get_by_role("button", name="Last Page").click(timeout=10000)
    except PwTimeoutError:
        pass
    
    try:
        page.get_by_role("cell", name="Orientation/Intake").first.click(timeout=5000)
        time.sleep(5)
        return True
    except (PwTimeoutError):
        return False


def would_get_over_12_hrs(page: Playwright, KAERS_ID: float, current_row: int) -> bool:
    """Pulls student's attendance hours from KAERS. Returns boolean of whether adding
       the current row's attendance would get the student above 12 hours."""
    current_attend_hours = float(page.locator(f"[id=\"MainContent_Attendance_userControl\\?{KAERS_ID}_lblHrS\"]").inner_text(timeout=5000))
    logging.info(f"Row {current_row + 1} - Current attendance hours: {current_attend_hours}")

    if WelcWin.attend_type == "Live Attendance" or WelcWin.attend_type == "Orientation/Intake":
        start_time = datetime.strptime(str(df['Start Time'][current_row]).strip(), "%H:%M")
        end_time = datetime.strptime(str(df['End Time'][current_row]).strip(), "%H:%M")

        total_time = end_time - start_time
        secs = total_time.seconds
        attendance_to_add = secs/3600
    else:
        attendance_to_add = float(df['Total Time'][current_row])

    logging.info(f"Row {current_row + 1} - Attendance to add: {attendance_to_add}")
    
    if current_attend_hours < 12 and current_attend_hours + attendance_to_add >= 12:
        return True
    else:
        return False


def record_attend_hrs(page: Playwright, current_row: int, KAERS_ID: float):
    """Pulls and records student's attendance hours in KAERS after row has been entered."""
    current_attend_hours = float(page.locator(f"[id=\"MainContent_Attendance_userControl\\?{KAERS_ID}_lblHrS\"]").inner_text(timeout=5000))
    ws.update_cell(current_row + 2, HOURS_AFTER_ENTRY_COLUMN, f'{current_attend_hours}')


# def process_finished_analysis(df: pd.DataFrame):
#     """Logs automation's performance data such as number of rows entered, errors, etc."""
#     global num_entered, num_date_time_rejected, num_timeout_errors, num_skipped_close_to_12
#     total_rows = df['KAERS ID'].count()
#     num_rows_attempted = total_rows - WelcWin.row_start

#     logging.info(f"\nAttendance entry complete - Rows entered: {num_entered} | Rows attempted: {num_rows_attempted}\n"
#                  f"Date/Time rejected: {num_date_time_rejected} | Timeout errors: {num_timeout_errors} | Skipped over 12 hrs: {num_skipped_close_to_12}")


# Opens Welcome Window: user selects attendance type, enters Google Sheet url, row ID to start on, and whether to skip getting students above 12 hrs
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

# ~~~

scopes = ['https://www.googleapis.com/auth/spreadsheets']

creds = Credentials.from_service_account_file("credentials.json", scopes=scopes)
client = gspread.authorize(creds)

url = WelcWin.url
text_blob = (re.split('spreadsheets/d/', url)[1])
wb_id = re.split('/edit', text_blob)[0]
wb = client.open_by_key(wb_id)

tabs = list(map(lambda x: x.title, wb.worksheets()))

MSG_student_list = []

if user_has_MSG_list():
    MSG_student_list = get_MSG_student_list()


# Opens Select Sheet Window; user selects sheet to use within the spreadsheet
window = CTk()
window.title("Select sheet")
window.minsize(width=200, height=200)
window.config(padx=25, pady=10)
sheet_window = SelectSheetWindow()
window.protocol("WM_DELETE_WINDOW", on_close)
window.mainloop()

log_path = f"logs/{wb.title.replace('/', '.')} _ {sheet_window.ws.replace('/', '.')}.log"

# log_path = create_log(log_path)


logging.basicConfig(level=logging.INFO, filename=log_path, filemode='a',
                    format="%(asctime)s - %(levelname)s - %(message)s", datefmt="%Y-%m-%d %H:%M:%S")

ws = wb.worksheet(f"{sheet_window.ws}")
df = pd.DataFrame(ws.get_all_records())
df = df.replace('', None)
df = df.replace('#N/A', None)
# idx = df.columns.get_loc("entered?")
ENTERED_COLUMN = df.columns.get_loc("entered?") + 1
try:
    HOURS_AFTER_ENTRY_COLUMN = df.columns.get_loc("Hours after entry") + 1
    hours_after_entry_col_exists = True
except KeyError:
    hours_after_entry_col_exists = False

# estimated_finish_time = estimate_completion_time(df)

logging.info(f"\n\n~ {WelcWin.attend_type} Entry ~\n"
             f"File chosen: {wb.title}\n"
             f"Skip rows that get above 12 hours: {WelcWin.skip_close_to_12}\n")
            #  f"Estimated finish time - {estimated_finish_time}\n")

starting_time = datetime.now().strftime("%H:%M")

num_entered = 0
num_date_time_rejected = 0
num_timeout_errors = 0
if WelcWin.skip_close_to_12:
    num_skipped_close_to_12 = 0
else:
    num_skipped_close_to_12 = 'N/A'


def run(playwright: Playwright) -> None:
    browser = playwright.chromium.launch(headless=False, args=["--start-maximized"])
    context = browser.new_context(no_viewport=True)
    page = context.new_page()
    global num_entered, num_date_time_rejected, num_timeout_errors, num_skipped_close_to_12

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


    if sheet_window.row_start:
        current_row = sheet_window.row_start
    else:
        current_row = 0


    for column in df['Row ID'].tolist():

        try:
            #TODO: catch when session expires
            # if "Session Expired" in url:
                #log "Session expired"
                #input("Session has expired. Please log into KAERS again and then push enter: ")


            KAERS_ID = df['KAERS ID'][current_row]
            FIRST_NAME = df['First Name'][current_row]
            LAST_NAME = df['Last Name'][current_row]
            

            if pd.isna(df['KAERS ID'][current_row]) or len(str(KAERS_ID)) != 7:
                if pd.isna(FIRST_NAME) and pd.isna(LAST_NAME):
                    logging.info(f'Blank row found. Program stopped. Row {current_row}\n')
                    break
                else:
                    logging.warning(f"Invalid ID: Row {current_row + 1}")
                    record_feedback(message='Invalid ID', current_row=current_row)
                    continue

            KAERS_ID = int(KAERS_ID)


            entered_cell = str(df['entered?'][current_row])
            if entered_cell == '✅' or entered_cell == '✔️' or entered_cell == 'YES':
                logging.info(f"Skipped: Row {current_row + 1} - Entry already entered. Status is: {entered_cell}")
                continue


            if WelcWin.attend_type == "Distance Learning":
                if df['Total Time'][current_row] == 0:
                    logging.info(f"Skipped (time = 0): Row {current_row + 1}")
                    record_feedback(message='Skipped (time = 0)', current_row=current_row)
                    continue

            
            # if str(KAERS_ID) in separated_list:
            #     logging.warning(f"SEPARATED (skipped): Row {current_row + 1}")
            #     record_feedback(message='Separated (skipped)', current_row=current_row)
            #     continue
           
            page.goto(f"https://kaers.ky.gov/StudentGeneral.aspx?student_record_id={KAERS_ID}")
            time.sleep(.25)

            enroll_status = page.locator(f"[id=\"lblStatus\"]").inner_text()
            
            if enroll_status == 'GENERAL':
                logging.warning(f"{enroll_status}: Row {current_row + 1}")
                record_feedback(message=f'{enroll_status}', current_row=current_row)
                continue

            page.get_by_role("link", name="Tests").click()
            time.sleep(2)
            page.get_by_role("link", name="Enrollment").click()
            time.sleep(3)

            if enroll_status == 'SEPARATED':
                try:
                    logging.info(f"Row {current_row + 1} - Attempting to un-separate")
                    un_separate(page, KAERS_ID)
                    logging.info(f"Row {current_row + 1} - Successfully un-separated")
                except PwTimeoutError:
                    logging.warning(f"{enroll_status}: Row {current_row + 1} - could not un-separate")
                    record_feedback(message=f'{enroll_status} - could not un-separate', current_row=current_row)
                    continue

            # try:
            #     page.get_by_text("This client is not enrolled in your location. Contact the enrollment location fo").click(timeout=2000)
            #     logging.warning(f"Row {current_row +1} - enrolled somewhere else")
            #     record_feedback(message='Error: Enrolled somewhere else', current_row=current_row)
            #     continue
            # except PwTimeoutError:
            #     pass

            page.locator("#ctl00_MainContent_RadTabStripEnrollmentVerticalTab").get_by_role("link", name="Attendance").click(timeout=20000)
            time.sleep(1)

            if page.get_by_text("This client is not enrolled in your location. Contact the enrollment location fo").is_visible():
                logging.warning(f"Row {current_row +1} - enrolled somewhere else")
                record_feedback(message='Error: Enrolled somewhere else', current_row=current_row)
                continue

            if WelcWin.attend_type == 'Orientation/Intake':
                if check_if_test_orientation_entered(page, KAERS_ID):
                    raise TestOrientationAlreadyEnteredException

            if WelcWin.skip_close_to_12:
                if would_get_over_12_hrs(page, KAERS_ID, current_row) and KAERS_ID not in MSG_student_list:
                    raise WouldGetOver12HoursException

            attendance_type = str.title(df['Attendance Type'][current_row])
            attendance_date = str(df['Attendance Date'][current_row])
            page.locator(f"[id=\"ctl00_MainContent_Attendance_userControl\\?{KAERS_ID}_rcbAttendType_Arrow\"]").click()
            page.locator(f"[id=\"ctl00_MainContent_Attendance_userControl\\?{KAERS_ID}_rcbAttendType_DropDown\"]").get_by_text(attendance_type).click()
            page.locator(f"[id=\"ctl00_MainContent_Attendance_userControl\\?{KAERS_ID}_rdpAttendDate_dateInput\"]").click()
            page.locator(f"[id=\"ctl00_MainContent_Attendance_userControl\\?{KAERS_ID}_rdpAttendDate_dateInput\"]").fill(attendance_date)
            page.locator("#ctl00_MainContent_RadTabStripEnrollmentVerticalTab").get_by_role("link", name="Attendance").click(timeout=3000)
            time.sleep(1)
           
            if WelcWin.attend_type == "Live Attendance" or WelcWin.attend_type == "Orientation/Intake":
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

            if hours_after_entry_col_exists and would_get_over_12_hrs(page, KAERS_ID, current_row):
                cell_to_color = gspread.utils.rowcol_to_a1(current_row + 2, HOURS_AFTER_ENTRY_COLUMN)
                ws.format(cell_to_color, {"backgroundColor": {"red": 0.039,"green": 0.941,"blue": 0.376}})

            page.get_by_role("button", name="Save").click()
            time.sleep(1)

            try:
                page.get_by_text("Attendance has been Saved.").click()
                logging.info(f"Successfully entered: Row {current_row + 1}")
                time.sleep(.5)
                record_feedback(message='✅', current_row=current_row)
                time.sleep(.5)
                if hours_after_entry_col_exists:
                    record_attend_hrs(page, current_row, KAERS_ID)
                num_entered += 1
            except PwTimeoutError:
                if page.locator(f"[id=\"MainContent_Attendance_userControl\\?{KAERS_ID}_customValidatorAttendDate\"]").is_visible():
                    enroll_date = page.locator("#MainContent_lblEnrollmentDate").inner_text()
                    logging.warning(f"Date/time rejected: Row {current_row + 1}")
                    record_feedback(message=f'Date/time rejected | Enrolled: {enroll_date}', current_row=current_row)
                    if hours_after_entry_col_exists:
                        record_attend_hrs(page, current_row, KAERS_ID)
                    num_date_time_rejected += 1
                else:
                    logging.warning(f"Error: Row {current_row + 1} - something went wrong")
                    record_feedback(message='Error: Something went wrong', current_row=current_row)


        except exceptions.APIError as err:
            logging.error(f"{err} - Error: Row {current_row + 1} | Something went wrong on Google's end")
            record_feedback(message="Error: Something went wrong on Google's end", current_row=current_row)


        except TestOrientationAlreadyEnteredException as err:
            logging.warning(f"{err} - Entry skipped: Row {current_row + 1} | Orientation/Intake already entered")
            record_feedback(message='Skipped (Orientation/Intake already entered)', current_row=current_row)


        except WouldGetOver12HoursException as err:
            logging.warning(f"{err} - Entry skipped: Row {current_row + 1} | Entry would get student above 12 hrs")
            record_feedback(message='Skipped (entry would get student above 12hrs)', current_row=current_row)
            num_skipped_close_to_12 += 1


        except PwTimeoutError as err:
            logging.error(f"{err} - Entry failed: Row {current_row + 1}")
            record_feedback(message='Error: Something timed out', current_row=current_row)
            num_timeout_errors += 1


        except ValueError as err:
            logging.error(f"{err} - Entry failed: Row {current_row + 1}")
            record_feedback(message='Error: Invalid info', current_row=current_row)


        finally:
            current_row += 1


    # ---------------------
    context.close()
    browser.close()


with sync_playwright() as playwright:
    run(playwright)


# process_finished_analysis(df)
