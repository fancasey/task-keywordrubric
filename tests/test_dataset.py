"""Cross-check each bundled question against the independent CSV export and evaluator cells."""

import csv
from collections import Counter
from zipfile import ZipFile

import pytest
from slimconfig import plain_output

from contract import QuestionID, QuestionInput
from plugin.questions import CRITERION_COLUMNS, DATASET, QUESTIONS, get_question, pin_teacher_grades, sheet_cells

CSV = DATASET / "Input file for NLP of 4 question scores.csv"


@pytest.mark.parametrize("question_id", list(QuestionID))
def test_all_response_and_score_exports_agree(question_id, tmp_path):
    with CSV.open(encoding="utf-8-sig", newline="") as source:
        rows = [row for row in csv.DictReader(source) if row["QID"] == question_id.value]
    assert len(rows) == 25
    assert Counter(row["StudentID"] for row in rows) == {f"S{i}": 5 for i in range(1, 6)}
    csv_by_key = {(row["StudentID"], row["Rubric"]): row for row in rows}
    assert len(csv_by_key) == 25

    with ZipFile(DATASET / QUESTIONS) as workbook:
        sheets = [
            sheet_cells(workbook, name)
            for name in workbook.namelist()
            if name.startswith("xl/worksheets/sheet") and name.endswith(".xml")
        ]
    cells = next(sheet for sheet in sheets if sheet["A3"] == question_id.value)

    reference = pin_teacher_grades(QuestionInput(question_id), tmp_path)
    teacher_by_key = {(grade.student_id, grade.dimension_id): grade.mean_score for grade in reference.teacher_grades}
    assert len(teacher_by_key) == 25
    for index, column in enumerate(CRITERION_COLUMNS):
        dimension_name = cells[f"{column}1"]
        for answer in reference.question.answers:
            key = answer.student_id, dimension_name
            row = csv_by_key[key]
            assert answer.text.strip() == row["ResponseText"].strip(), key
            teacher_mean = teacher_by_key[answer.student_id, f"D{index + 1}"]
            # The original workbook has five evaluators for each dimension.
            start = 12 + 5 * index
            evaluator_columns = [
                chr(65 + column) if column < 26 else "A" + chr(65 + column - 26) for column in range(start, start + 5)
            ]
            answer_row = int(answer.student_id[1:]) + 2
            ratings = [int(cells[f"{column}{answer_row}"]) for column in evaluator_columns]
            assert teacher_mean == pytest.approx(sum(ratings) / 5), key
            assert int(row["Score"]) == round(teacher_mean), key


def test_only_selected_questions_exist_in_all_exports():
    with CSV.open(encoding="utf-8-sig", newline="") as source:
        rows = list(csv.DictReader(source))
    assert Counter(row["QID"] for row in rows) == {question.value: 25 for question in QuestionID}
    with ZipFile(DATASET / QUESTIONS) as workbook:
        sheets = [
            sheet_cells(workbook, name)
            for name in workbook.namelist()
            if name.startswith("xl/worksheets/sheet") and name.endswith(".xml")
        ]
    assert len(sheets) == 4
    assert {sheet["A3"] for sheet in sheets} == {question.value for question in QuestionID}


@pytest.mark.parametrize("question_id", list(QuestionID))
def test_public_context_excludes_student_answers_and_teacher_scores(question_id, tmp_path):
    request = QuestionInput(question_id)
    public = plain_output(get_question(request, tmp_path))
    reference = pin_teacher_grades(request, tmp_path)
    assert set(public) == {"question_id", "question", "model_answer"}
    assert public["question_id"] == question_id.value
    assert len(reference.question.answers) == 5
    assert all(answer.text for answer in reference.question.answers)
    assert {grade.student_id for grade in reference.teacher_grades} == {"S1", "S2", "S3", "S4", "S5"}
