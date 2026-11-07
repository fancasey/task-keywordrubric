"""Read the bundled, fixed-layout question and teacher-score workbooks."""

from pathlib import Path
from xml.etree import ElementTree
from zipfile import ZipFile

from contract import (
    QuestionContextOutput,
    QuestionOutput,
    ReferenceOutput,
    StudentAnswer,
    StudentListOutput,
    StudentResponseOutput,
    TeacherGrade,
)

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


def question_cells(question_id):
    with ZipFile(DATASET / QUESTIONS) as workbook:
        for member in workbook.namelist():
            if member.startswith("xl/worksheets/sheet") and member.endswith(".xml"):
                cells = sheet_cells(workbook, member)
                if cells.get("A3") == question_id.value:
                    return cells
    raise ValueError("Question is missing from the dataset")


def question_context(question_id, cells):
    model_answer = "\n".join(cells[f"J{row}"] for row in range(3, 8) if cells.get(f"J{row}"))
    return QuestionContextOutput(question_id, cells["B3"], model_answer)


def get_question(arguments, workspace):
    return question_context(arguments.question_id, question_cells(arguments.question_id))


def load_question_with_answers(question_id):
    cells = question_cells(question_id)
    context = question_context(question_id, cells)
    answers = [StudentAnswer(f"S{i}", cells[f"L{row}"]) for i, row in enumerate(range(3, 8), 1)]
    return QuestionOutput(question_id, context.question, context.model_answer, answers)


def pin_teacher_grades(arguments, workspace):
    question = load_question_with_answers(arguments.question_id)
    with ZipFile(DATASET / SCORES) as workbook:
        cells = sheet_cells(workbook, "xl/worksheets/sheet1.xml")

    cells_for_question = question_cells(arguments.question_id)
    dimensions = {cells_for_question[f"{column}1"]: f"D{i}" for i, column in enumerate(CRITERION_COLUMNS, 1)}
    grades = [
        TeacherGrade(cells[f"C{row}"], dimensions[cells[f"B{row}"]], float(cells[f"I{row}"]))
        for row in range(2, len([cell for cell in cells if cell.startswith("A")]) + 1)
        if cells[f"A{row}"] == arguments.question_id.value
    ]
    return ReferenceOutput(question, grades)


def list_students(arguments, workspace):
    question = load_question_with_answers(arguments.question_id)
    return StudentListOutput(arguments.question_id, [answer.student_id for answer in question.answers])


def get_student_response(arguments, workspace):
    question = load_question_with_answers(arguments.question_id)
    for answer in question.answers:
        if answer.student_id == arguments.student_id:
            return StudentResponseOutput(arguments.question_id, answer)
    raise ValueError(f"Unknown student ID for {arguments.question_id.value}: {arguments.student_id}")
