import os
import re
import time
import logging
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional, Sequence

import gspread
import gspread.utils
import pandas as pd
from dotenv import load_dotenv
from google.oauth2.service_account import Credentials
from gspread import exceptions
from playwright.sync_api import Playwright, sync_playwright, TimeoutError as PwTimeoutError


class WouldGetOver12HoursException(Exception):
    """Raised if adding the current row's attendance would get the student above 12 hours."""


class TestOrientationAlreadyEnteredException(Exception):
    """Raised if their test attendance hours (Orientation/Intake) has already been entered in KAERS."""


class LastNameNotInKAERSProfileNameException(Exception):
    """Raised if student's last name isn't in the student's KAERS profile--implies
    it's the wrong student (wrong ID on attendance sheet)."""


@dataclass(frozen=True)
class RunOptions:
    attend_type: str
    sheet_url: str
    worksheet_title: str
    row_start_index: int = 0  # 0-based
    skip_close_to_12: bool = False
    validate_name: bool = False
    msg_student_ids: Optional[Sequence[int]] = None
    desired_participants_to_add: int = 0


SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]


def list_sheet_tabs(sheet_url: str, credentials_path: str = "credentials.json") -> list[str]:
    client = _authorize_gspread(credentials_path)
    wb_id = _workbook_id_from_url(sheet_url)
    wb = client.open_by_key(wb_id)
    return [ws.title for ws in wb.worksheets()]


def run_attendance(options: RunOptions, credentials_path: str = "credentials.json") -> None:
    _ensure_logs_dir()

    client = _authorize_gspread(credentials_path)
    wb_id = _workbook_id_from_url(options.sheet_url)
    wb = client.open_by_key(wb_id)

    worksheet = wb.worksheet(options.worksheet_title)
    df = _load_sheet_dataframe(worksheet)

    entered_column = df.columns.get_loc("entered?") + 1

    try:
        hours_after_entry_column = df.columns.get_loc("Hours after entry") + 1
        hours_after_entry_col_exists = True
    except KeyError:
        hours_after_entry_col_exists = False
        hours_after_entry_column = -1

    log_path = f"logs/{wb.title.replace('/', '.')} _ {options.worksheet_title.replace('/', '.')}.log"
    logging.basicConfig(
        level=logging.INFO,
        filename=log_path,
        filemode="a",
        format="%(asctime)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    logging.info(
        "\n\n~ %s Entry ~\nFile chosen: %s\nSkip rows that get above 12 hours: %s\n",
        options.attend_type,
        wb.title,
        options.skip_close_to_12,
    )

    msg_student_ids = set(map(int, options.msg_student_ids or []))

    def run(playwright: Playwright) -> None:
        browser = playwright.chromium.launch(headless=False, args=["--start-maximized"])
        context = browser.new_context(no_viewport=True)
        page = context.new_page()

        non_msg_participants_added = 0

        load_dotenv(override=True)
        username = os.getenv("USERNAME")
        password = os.getenv("PASSWORD")

        if not username or not password:
            raise RuntimeError("USERNAME/PASSWORD not found in environment (.env is optional).")

        page.goto("https://kaers.ky.gov/SignIn.aspx")
        page.locator("#rtxtUserName").click()
        page.locator("#rtxtUserName").fill(username)
        page.locator("#rtxtPassword").click()
        page.locator("#rtxtPassword").fill(password)
        page.get_by_role("button", name="Sign in").click()
        time.sleep(8)

        current_row = int(options.row_start_index or 0)

        for _ in df["Row ID"].tolist():
            try:
                kaers_id = df["KAERS ID"][current_row]
                first_name = df["First Name"][current_row]
                last_name = df["Last Name"][current_row]

                add_participant_anyway = non_msg_participants_added < int(options.desired_participants_to_add or 0)

                if pd.isna(kaers_id) or len(str(kaers_id)) != 7:
                    if pd.isna(first_name) and pd.isna(last_name):
                        logging.info("Blank row found. Program stopped. Row %s", current_row)
                        break

                    logging.warning("Invalid ID: Row %s", current_row + 1)
                    record_feedback(worksheet, "Invalid ID", current_row, entered_column)
                    continue

                kaers_id = int(kaers_id)

                entered_cell = str(df["entered?"][current_row])
                if entered_cell in {"✅", "✔️", "YES"}:
                    logging.info(
                        "Skipped: Row %s - Entry already entered. Status is: %s",
                        current_row + 1,
                        entered_cell,
                    )
                    continue

                if options.attend_type.startswith("Distance Learning"):
                    if df["Total Time"][current_row] == 0:
                        logging.info("Skipped (time = 0): Row %s", current_row + 1)
                        record_feedback(worksheet, "Skipped (time = 0)", current_row, entered_column)
                        continue

                page.goto(f"https://kaers.ky.gov/StudentGeneral.aspx?student_record_id={kaers_id}")
                time.sleep(0.25)

                session_expired_check(page, username, password)

                if options.validate_name:
                    if not last_name_is_in_full_name(page, str(last_name)):
                        raise LastNameNotInKAERSProfileNameException

                enroll_status = page.locator("[id=\"lblStatus\"]").inner_text()
                if enroll_status == "GENERAL":
                    logging.warning("%s: Row %s", enroll_status, current_row + 1)
                    record_feedback(worksheet, enroll_status, current_row, entered_column)
                    continue

                page.get_by_role("link", name="Tests").click()
                time.sleep(2)
                page.get_by_role("link", name="Enrollment").click()
                time.sleep(6)

                if enroll_status == "SEPARATED":
                    try:
                        logging.info("Row %s - Attempting to un-separate", current_row + 1)
                        un_separate(page, kaers_id)
                        logging.info("Row %s - Successfully un-separated", current_row + 1)
                    except PwTimeoutError:
                        logging.warning("%s: Row %s - could not un-separate", enroll_status, current_row + 1)
                        record_feedback(worksheet, f"{enroll_status} - could not un-separate", current_row, entered_column)
                        continue

                page.locator("#ctl00_MainContent_RadTabStripEnrollmentVerticalTab").get_by_role(
                    "link", name="Attendance"
                ).click(timeout=20000)
                time.sleep(1)

                if page.get_by_text(
                    "This client is not enrolled in your location. Contact the enrollment location fo"
                ).is_visible():
                    logging.warning("Row %s - enrolled somewhere else", current_row + 1)
                    record_feedback(worksheet, "Error: Enrolled somewhere else", current_row, entered_column)
                    continue

                if options.attend_type == "Orientation/Intake":
                    if check_if_test_orientation_entered(page, kaers_id):
                        raise TestOrientationAlreadyEnteredException

                if is_GED_Ready_No_Initial_Test(page) and would_get_over_12_hrs(page, kaers_id, df, current_row, options.attend_type):
                    raise WouldGetOver12HoursException

                if options.skip_close_to_12:
                    over_12 = would_get_over_12_hrs(page, kaers_id, df, current_row, options.attend_type)
                    if over_12 and kaers_id not in msg_student_ids and add_participant_anyway:
                        pass
                    elif over_12 and kaers_id not in msg_student_ids:
                        raise WouldGetOver12HoursException

                attendance_type = str.title(df["Attendance Type"][current_row])
                attendance_date = str(df["Attendance Date"][current_row])

                page.locator(
                    f"[id=\"ctl00_MainContent_Attendance_userControl\\?{kaers_id}_rcbAttendType_Arrow\"]"
                ).click()
                page.locator(
                    f"[id=\"ctl00_MainContent_Attendance_userControl\\?{kaers_id}_rcbAttendType_DropDown\"]"
                ).get_by_text(attendance_type).click()
                page.locator(
                    f"[id=\"ctl00_MainContent_Attendance_userControl\\?{kaers_id}_rdpAttendDate_dateInput\"]"
                ).click()
                page.locator(
                    f"[id=\"ctl00_MainContent_Attendance_userControl\\?{kaers_id}_rdpAttendDate_dateInput\"]"
                ).fill(attendance_date)
                page.locator("#ctl00_MainContent_RadTabStripEnrollmentVerticalTab").get_by_role(
                    "link", name="Attendance"
                ).click(timeout=3000)
                time.sleep(1)

                if options.attend_type in {"Live Attendance", "Orientation/Intake"}:
                    start_time = str(df["Start Time"][current_row])
                    end_time = str(df["End Time"][current_row])
                    page.locator(
                        f"[id=\"ctl00_MainContent_Attendance_userControl\\?{kaers_id}_rtpStartTime_dateInput\"]"
                    ).click()
                    page.locator(
                        f"[id=\"ctl00_MainContent_Attendance_userControl\\?{kaers_id}_rtpStartTime_dateInput\"]"
                    ).fill(start_time)
                    page.locator(
                        f"[id=\"ctl00_MainContent_Attendance_userControl\\?{kaers_id}_rtpEndTime_dateInput\"]"
                    ).click()
                    page.locator(
                        f"[id=\"ctl00_MainContent_Attendance_userControl\\?{kaers_id}_rtpEndTime_dateInput\"]"
                    ).fill(end_time)
                else:
                    product = str(df["Product"][current_row])
                    total_time = str(df["Total Time"][current_row])
                    page.locator(
                        f"[id=\"ctl00_MainContent_Attendance_userControl\\?{kaers_id}_rcbProducts_Arrow\"]"
                    ).click()
                    time.sleep(0.5)
                    page.get_by_text(product).click()
                    page.get_by_role("textbox", name="Total time should not be more than 20 hours!").click()
                    page.get_by_role("textbox", name="Total time should not be more than 20 hours!").fill(total_time)

                if hours_after_entry_col_exists:
                    over_12_now = would_get_over_12_hrs(page, kaers_id, df, current_row, options.attend_type)
                    if over_12_now and add_participant_anyway and kaers_id not in msg_student_ids:
                        non_msg_participants_added += 1
                        cell_to_color = gspread.utils.rowcol_to_a1(current_row + 2, hours_after_entry_column)
                        worksheet.format(cell_to_color, {"backgroundColor": {"red": 1, "green": 0.463, "blue": 0.925}})
                    elif over_12_now:
                        cell_to_color = gspread.utils.rowcol_to_a1(current_row + 2, hours_after_entry_column)
                        worksheet.format(cell_to_color, {"backgroundColor": {"red": 0.039, "green": 0.941, "blue": 0.376}})

                page.get_by_role("button", name="Save").click()
                time.sleep(1)

                try:
                    page.get_by_text("Attendance has been Saved.").click()
                    logging.info("Successfully entered: Row %s", current_row + 1)
                    record_feedback(worksheet, "✅", current_row, entered_column)
                    if hours_after_entry_col_exists:
                        record_attend_hrs(page, worksheet, current_row, hours_after_entry_column, kaers_id)
                except PwTimeoutError:
                    if page.locator(
                        f"[id=\"MainContent_Attendance_userControl\\?{kaers_id}_customValidatorAttendDate\"]"
                    ).is_visible():
                        enroll_date = page.locator("#MainContent_lblEnrollmentDate").inner_text()
                        logging.warning("Date/time rejected: Row %s", current_row + 1)
                        record_feedback(worksheet, f"Date/time rejected | Enrolled: {enroll_date}", current_row, entered_column)
                        if hours_after_entry_col_exists:
                            record_attend_hrs(page, worksheet, current_row, hours_after_entry_column, kaers_id)
                    else:
                        logging.warning("Error: Row %s - something went wrong", current_row + 1)
                        record_feedback(worksheet, "Error: Something went wrong", current_row, entered_column)

            except exceptions.APIError as err:
                logging.error("%s - Error: Row %s | Something went wrong on Google's end", err, current_row + 1)
                record_feedback(worksheet, "Error: Something went wrong on Google's end", current_row, entered_column)

            except LastNameNotInKAERSProfileNameException as err:
                logging.warning(
                    "%s - Entry skipped: Row %s | Maybe wrong student (first name not in profile)",
                    err,
                    current_row + 1,
                )
                record_feedback(worksheet, "Skipped (wrong student? first name not in profile)", current_row, entered_column)

            except TestOrientationAlreadyEnteredException as err:
                logging.warning(
                    "%s - Entry skipped: Row %s | Orientation/Intake already entered",
                    err,
                    current_row + 1,
                )
                record_feedback(worksheet, "Skipped (Orientation/Intake already entered)", current_row, entered_column)

            except WouldGetOver12HoursException as err:
                logging.warning(
                    "%s - Entry skipped: Row %s | Entry would get student above 12 hrs (managed attendance) | Program: %s",
                    err,
                    current_row + 1,
                    get_program_type(page),
                )
                record_feedback(worksheet, f"Skipped (managed attendance) | Program: {get_program_type(page)}", current_row, entered_column)

            except PwTimeoutError as err:
                logging.error("%s - Entry failed: Row %s", err, current_row + 1)
                record_feedback(worksheet, "Error: Something timed out", current_row, entered_column)

            except ValueError as err:
                logging.error("%s - Entry failed: Row %s", err, current_row + 1)
                record_feedback(worksheet, "Error: Invalid info", current_row, entered_column)

            finally:
                current_row += 1

        context.close()
        browser.close()

    with sync_playwright() as playwright:
        run(playwright)


def record_feedback(ws: gspread.Worksheet, message: str, current_row: int, entered_column: int) -> None:
    ws.update_cell(current_row + 2, entered_column, f"{message}")


def get_split_name(page) -> list[str]:
    return page.locator("#lblStudentName").text_content().title().split()


def last_name_is_in_full_name(page, last_name: str) -> bool:
    first_of_last_name = last_name.title().split()[0]
    return first_of_last_name in get_split_name(page)


def session_expired_check(page, username: str, password: str) -> None:
    current_url = page.url
    if "SessionExpired" in current_url:
        logging.warning("Session expired. Attempting to log back in.")
        page.goto("https://kaers.ky.gov/SignIn.aspx")
        page.locator("#rtxtUserName").click()
        page.locator("#rtxtUserName").fill(username)
        page.locator("#rtxtPassword").click()
        page.locator("#rtxtPassword").fill(password)
        page.get_by_role("button", name="Sign in").click()
        time.sleep(8)


def un_separate(page, kaers_id: int) -> None:
    page.get_by_role("button", name="Edit Enrollment").first.click(timeout=5000)
    time.sleep(3)
    page.locator("#ctl00_MainContent_RadTabStripEnrollmentVerticalTab").get_by_role("link", name="Enrollment").click(timeout=5000)
    page.locator(f"[id=\"MainContent_Enrollment_userControl\\?{kaers_id}_chkReleased\"]").uncheck(timeout=3000)
    time.sleep(0.5)
    page.get_by_role("button", name="Update").click(timeout=3000)
    time.sleep(8)


def check_if_test_orientation_entered(page, kaers_id: int) -> bool:
    try:
        page.locator(
            f"[id=\"ctl00_MainContent_Attendance_userControl\\?{kaers_id}_rgAttendance_ctl00_ctl03_ctl01_PageSizeComboBox_Arrow\"]"
        ).click(timeout=5000)
        time.sleep(1)
        page.locator(
            f"[id=\"ctl00_MainContent_Attendance_userControl\\?{kaers_id}_rgAttendance_ctl00_ctl03_ctl01_PageSizeComboBox_DropDown\"]"
        ).get_by_text("50").click()
        time.sleep(5)
        page.get_by_role("button", name="Last Page").click(timeout=10000)
    except PwTimeoutError:
        pass

    try:
        page.get_by_role("cell", name="Orientation/Intake").first.click(timeout=5000)
        time.sleep(5)
        return True
    except PwTimeoutError:
        return False


def get_program_type(page) -> str:
    return page.locator("#MainContent_lblProgramType").text_content()


def is_GED_Ready_No_Initial_Test(page) -> bool:
    return get_program_type(page) == "GED Ready / No Initial Test"


def would_get_over_12_hrs(page, kaers_id: int, df: pd.DataFrame, current_row: int, attend_type: str) -> bool:
    current_attend_hours = float(
        page.locator(f"[id=\"MainContent_Attendance_userControl\\?{kaers_id}_lblHrS\"]").inner_text(timeout=5000)
    )

    if attend_type in {"Live Attendance", "Orientation/Intake"}:
        start_time = datetime.strptime(str(df["Start Time"][current_row]).strip(), "%H:%M")
        end_time = datetime.strptime(str(df["End Time"][current_row]).strip(), "%H:%M")
        attendance_to_add = (end_time - start_time).seconds / 3600
    else:
        attendance_to_add = float(df["Total Time"][current_row])

    if current_attend_hours < 12 and current_attend_hours + attendance_to_add >= 12:
        return True
    return False


def record_attend_hrs(page, ws: gspread.Worksheet, current_row: int, hours_after_entry_column: int, kaers_id: int) -> None:
    current_attend_hours = float(
        page.locator(f"[id=\"MainContent_Attendance_userControl\\?{kaers_id}_lblHrS\"]").inner_text(timeout=5000)
    )
    ws.update_cell(current_row + 2, hours_after_entry_column, f"{current_attend_hours}")


def _authorize_gspread(credentials_path: str) -> gspread.Client:
    creds = Credentials.from_service_account_file(credentials_path, scopes=SCOPES)
    return gspread.authorize(creds)


def _workbook_id_from_url(sheet_url: str) -> str:
    text_blob = re.split("spreadsheets/d/", sheet_url)[1]
    return re.split("/edit", text_blob)[0]


def _ensure_logs_dir() -> None:
    Path("logs").mkdir(parents=True, exist_ok=True)


def _load_sheet_dataframe(ws: gspread.Worksheet) -> pd.DataFrame:
    df = pd.DataFrame(ws.get_all_records())
    df = df.replace("", None)
    df = df.replace("#N/A", None)
    return df
