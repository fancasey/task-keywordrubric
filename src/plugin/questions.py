"""Read the bundled, fixed-layout question and teacher-score workbooks."""

from pathlib import Path
from xml.etree import ElementTree
from zipfile import ZipFile

from contract import Dimension, QuestionOutput, ReferenceOutput, StudentAnswer, TeacherGrade

DATASET = Path(__file__).with_name("dataset")
QUESTIONS = "ALL 4 Ques scores 5 Evaluators 5 students.xlsx"
SCORES = "rubric_scores_with_mean.xlsx"
SHEET_NS = {"x": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
CRITERION_COLUMNS = ("M", "R", "W", "AB", "AG")


def sheet_cells(workbook, member):
    sheet = ElementTree.fromstring(workbook.read(member))
    cells = {}
    for cell in sheet.findall("x:sheetData/x:row/x:c", SHEET_NS):
        if cell.attrib.get("t") == "inlineStr":
            value = "".join(text.text or "" for text in cell.findall("x:is//x:t", SHEET_NS))
        else:
            value = cell.findtext("x:v", namespaces=SHEET_NS)
        if value is not None:
            cells[cell.attrib["r"]] = value
    return cells


def get_question(arguments, workspace):
    with ZipFile(DATASET / QUESTIONS) as workbook:
        for member in workbook.namelist():
            if member.startswith("xl/worksheets/sheet") and member.endswith(".xml"):
                cells = sheet_cells(workbook, member)
                if cells.get("A3") == arguments.question_id.value:
                    break
        else:
            raise ValueError("Question is missing from the dataset")

    dimensions = [
        Dimension(f"D{i}", cells[f"{name_col}1"], [cells[f"{level_col}{row}"] for row in (7, 6, 5, 4)])
        for i, (name_col, level_col) in enumerate(zip(CRITERION_COLUMNS, "EFGHI", strict=True), 1)
    ]
    answers = [StudentAnswer(f"S{i}", cells[f"L{row}"]) for i, row in enumerate(range(3, 8), 1)]
    model_answer = "\n".join(cells[f"J{row}"] for row in range(3, 8) if cells.get(f"J{row}"))
    return QuestionOutput(arguments.question_id, cells["B3"], model_answer, dimensions, answers)


def pin_teacher_grades(arguments, workspace):
    question = get_question(arguments, workspace)
    with ZipFile(DATASET / SCORES) as workbook:
        cells = sheet_cells(workbook, "xl/worksheets/sheet1.xml")

    dimensions = {dimension.name: dimension.dimension_id for dimension in question.dimensions}
    grades = [
        TeacherGrade(cells[f"C{row}"], dimensions[cells[f"B{row}"]], float(cells[f"I{row}"]))
        for row in range(2, len([cell for cell in cells if cell.startswith("A")]) + 1)
        if cells[f"A{row}"] == arguments.question_id.value
    ]
    return ReferenceOutput(question, grades)
