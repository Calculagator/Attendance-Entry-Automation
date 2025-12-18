import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import customtkinter
from customtkinter import CTk, StringVar
import tkinter.messagebox
from tkinter import filedialog
import pandas as pd


@dataclass(frozen=True)
class WelcomeSelections:
    attend_type: str
    sheet_url: str
    skip_close_to_12: bool
    validate_name: bool


@dataclass(frozen=True)
class SheetSelections:
    worksheet_title: str
    row_start_index: int


def collect_welcome() -> WelcomeSelections:
    window = CTk()
    customtkinter.set_appearance_mode("dark")
    customtkinter.set_default_color_theme("dark-blue")
    frame = customtkinter.CTkFrame(master=window)
    frame.grid()

    window.title("Attendance Entry")
    window.minsize(width=300, height=300)
    window.config(padx=25, pady=25)

    selections: dict[str, object] = {}

    def on_close() -> None:
        close = tkinter.messagebox.askokcancel(title="Close", message="Would you like to close the program?")
        if close:
            sys.exit()

    options = [
        "Live Attendance",
        "Distance Learning/Online Self-Study",
        "Orientation/Intake",
        "CCN - Personal Contact",
    ]

    customtkinter.CTkLabel(master=frame, text="Attendance Entry Program", font=("Roboto", 14, "bold")).grid(
        row=0, column=2, pady=15
    )
    customtkinter.CTkLabel(master=frame, text="Attendance type:").grid(row=1, column=1)

    radio_state = StringVar(value="None")
    for idx, name in enumerate(options):
        button = customtkinter.CTkRadioButton(
            master=frame, text=name, font=("Roboto", 14), value=name, variable=radio_state
        )
        button.grid(row=1 + idx, column=2, sticky="W", pady=5)

    customtkinter.CTkLabel(master=frame, text="Google Sheet URL:").grid(row=5, column=1)
    sheet_url_entry = customtkinter.CTkEntry(master=frame, width=150, font=("Roboto", 13))
    sheet_url_entry.grid(row=5, column=2, pady=5)

    managed_attendance_check = customtkinter.BooleanVar(value=False)
    customtkinter.CTkCheckBox(
        master=frame,
        text="Managed attendance?",
        variable=managed_attendance_check,
        onvalue=True,
        offvalue=False,
    ).grid(row=9, column=2, pady=5)

    name_validation = customtkinter.BooleanVar(value=False)
    customtkinter.CTkCheckBox(
        master=frame,
        text="Name check?",
        variable=name_validation,
        onvalue=True,
        offvalue=False,
    ).grid(row=10, column=2, pady=5)

    def on_next() -> None:
        attend_type = str(radio_state.get())
        sheet_url = str(sheet_url_entry.get()).strip()

        if attend_type == "None" or not sheet_url:
            tkinter.messagebox.showinfo(title="Oops!", message="Please make sure all fields are completed.")
            return

        selections["attend_type"] = attend_type
        selections["sheet_url"] = sheet_url
        selections["skip_close_to_12"] = bool(managed_attendance_check.get())
        selections["validate_name"] = bool(name_validation.get())
        window.destroy()

    customtkinter.CTkButton(master=frame, text="Next", font=("Roboto", 14), command=on_next).grid(
        row=11, column=2, pady=20
    )

    window.protocol("WM_DELETE_WINDOW", on_close)
    window.mainloop()

    return WelcomeSelections(
        attend_type=str(selections["attend_type"]),
        sheet_url=str(selections["sheet_url"]),
        skip_close_to_12=bool(selections["skip_close_to_12"]),
        validate_name=bool(selections["validate_name"]),
    )


def collect_sheet_selection(tabs: list[str]) -> SheetSelections:
    window = CTk()
    window.title("Select sheet")
    window.minsize(width=200, height=200)
    window.config(padx=25, pady=10)

    frame = customtkinter.CTkFrame(master=window)
    frame.grid()

    selections: dict[str, object] = {}

    def on_close() -> None:
        close = tkinter.messagebox.askokcancel(title="Close", message="Would you like to close the program?")
        if close:
            sys.exit()

    customtkinter.CTkLabel(
        master=frame,
        text="Select the tab you want to use:",
        font=("Roboto", 14, "bold"),
    ).grid(row=0, column=0, sticky="w", padx=10, pady=20)

    radio_state = StringVar(value="None")

    row = 1
    column = 1
    for name in tabs:
        if row > 8:
            row = 1
            column += 1
        button = customtkinter.CTkRadioButton(master=frame, text=name, value=name, variable=radio_state)
        button.grid(row=row, column=column, sticky="w", padx=50, pady=5)
        row += 1

    customtkinter.CTkLabel(master=frame, text="Start at Row ID:").grid(row=9, column=0, pady=10)
    row_start_entry = customtkinter.CTkEntry(master=frame, width=150, font=("Roboto", 13))
    row_start_entry.grid(row=9, column=1, pady=10)

    def on_start() -> None:
        ws_title = radio_state.get()
        if ws_title == "None":
            tkinter.messagebox.showinfo(title="Oops!", message="Please select a sheet.")
            return

        raw = str(row_start_entry.get()).strip()
        if not raw:
            row_start_index = 0
        else:
            try:
                row_start_index = int(raw) - 1
            except ValueError:
                tkinter.messagebox.showinfo(title="Oops!", message="Row ID must be a number.")
                return

        selections["worksheet_title"] = str(ws_title)
        selections["row_start_index"] = int(row_start_index)
        window.destroy()

    customtkinter.CTkButton(master=frame, text="START", command=on_start).grid(row=10, column=2, pady=10)

    window.protocol("WM_DELETE_WINDOW", on_close)
    window.mainloop()

    return SheetSelections(
        worksheet_title=str(selections["worksheet_title"]),
        row_start_index=int(selections["row_start_index"]),
    )


def maybe_get_msg_student_list() -> list[int]:
    """Returns a list of KAERS IDs from an Excel file, or an empty list if user cancels."""
    file_path = filedialog.askopenfilename(
        initialdir=str(Path.home()),
        title="Choose a spreadsheet",
        filetypes=(("Excel Files", "*.xlsx*"),),
    )

    if not file_path:
        return []

    students_to_enter_df = pd.read_excel(file_path, "Sheet1")
    return students_to_enter_df["KAERS ID"].fillna(0).astype(int).tolist()
