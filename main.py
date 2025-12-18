import time
import tkinter.messagebox
import tkinter.simpledialog

from attendance_core import RunOptions, list_sheet_tabs, run_attendance
import ui_tk


def main() -> None:
    welcome = ui_tk.collect_welcome()
    tabs = list_sheet_tabs(welcome.sheet_url)
    sheet = ui_tk.collect_sheet_selection(tabs)

    msg_student_ids = []
    if welcome.skip_close_to_12:
        if tkinter.messagebox.askyesno(
            title="MSG list",
            message="Do you have a list of students who you want to get above 12 hrs?",
        ):
            msg_student_ids = ui_tk.maybe_get_msg_student_list()

    desired_participants_to_add = 0
    if welcome.skip_close_to_12:
        try:
            raw = tkinter.simpledialog.askstring(
                title="Managed attendance",
                prompt="How many participants do you want to add?",
            )
            if raw:
                desired_participants_to_add = int(raw)
        except Exception:
            desired_participants_to_add = 0

    options = RunOptions(
        attend_type=welcome.attend_type,
        sheet_url=welcome.sheet_url,
        worksheet_title=sheet.worksheet_title,
        row_start_index=sheet.row_start_index,
        skip_close_to_12=welcome.skip_close_to_12,
        validate_name=welcome.validate_name,
        msg_student_ids=msg_student_ids,
        desired_participants_to_add=desired_participants_to_add,
    )

    time.sleep(0.2)
    run_attendance(options)


if __name__ == "__main__":
    main()
