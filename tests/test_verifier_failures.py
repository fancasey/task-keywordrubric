"""Reject malformed references, rubrics, and submitted grades."""

from dataclasses import replace

import pytest
from test_verifier import rubric

from contract import GradeAnswersInput, QuestionID, QuestionInput, RubricOutput, StudentAnswer
from plugin.grading import grade_answers
from plugin.questions import pin_teacher_grades
from verifier import verify_task


@pytest.mark.parametrize("change", ["missing", "duplicate", "nan", "range", "question", "students"])
def test_bad_references(change, tmp_path):
    request = QuestionInput(QuestionID.NQ007)
    reference = pin_teacher_grades(request, tmp_path)
    if change == "missing":
        reference = None
    elif change == "duplicate":
        reference.teacher_grades[-1] = reference.teacher_grades[0]
    elif change in ("nan", "range"):
        reference.teacher_grades[0].mean_score = float("nan") if change == "nan" else 5
    elif change == "question":
        reference.question.question_id = QuestionID.NQ004
    else:
        reference.question.answers.pop()
    assert not verify_task(
        "generate-rubric", request, RubricOutput(request.question_id, rubric()), reference, tmp_path
    )["valid"]


@pytest.mark.parametrize("change", ["empty", "duplicate", "wrong_question"])
def test_invalid_submissions(change, tmp_path):
    request = QuestionInput(QuestionID.NQ007)
    output = RubricOutput(request.question_id, rubric())
    if change == "empty":
        output.rubric = []
    elif change == "duplicate":
        output.rubric.append(output.rubric[0])
    else:
        output = replace(output, question_id=QuestionID.NQ004)
    assert not verify_task("generate-rubric", request, output, pin_teacher_grades(request, tmp_path), tmp_path)["valid"]


@pytest.mark.parametrize("ids", [[""], [" "], ["a", "a"]])
def test_invalid_student_ids(ids, tmp_path):
    request = GradeAnswersInput(QuestionID.NQ007, rubric(), [StudentAnswer(i, "stack") for i in ids])
    with pytest.raises(ValueError, match="Student IDs"):
        grade_answers(request, tmp_path)
