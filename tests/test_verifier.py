"""Check overall grading against aggregated teacher means and independent replay."""

from dataclasses import replace
from statistics import mean

import pytest

from contract import (
    EvidenceGroup,
    GradeAnswersInput,
    GradeAnswersOutput,
    PhraseAlternative,
    QuestionID,
    QuestionInput,
    RubricOutput,
    StudentAnswer,
)
from plugin.grading import grade_answers
from plugin.questions import get_question, pin_teacher_grades
from verifier import verify_output, verify_task
from verifier.scoring import score_answers


def rubric():
    return [EvidenceGroup([PhraseAlternative([word], [])]) for word in ("stack", "queue", "heap", "DFS")]


def test_verifier_loads_without_plugin_implementation(tmp_path):
    import subprocess
    import sys
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    script = """
import sys
sys.path.insert(0, sys.argv[1])
class NoPlugin:
    def find_spec(self, fullname, path=None, target=None):
        if fullname == 'plugin' or fullname.startswith('plugin.'):
            raise ImportError('plugin implementation is unavailable to the verifier')
sys.meta_path.insert(0, NoPlugin())
from contract import QuestionID, QuestionInput, StudentResponseInput
from verifier import verify_output
from verifier.questions import get_student_response, list_students
for question_id in QuestionID:
    request = QuestionInput(question_id)
    students = list_students(request, None)
    assert verify_output('list_students', request, students, None)['valid']
    for student_id in students.student_ids:
        lookup = StudentResponseInput(question_id, student_id)
        response = get_student_response(lookup, None)
        assert verify_output('get_student_response', lookup, response, None)['valid']
"""
    subprocess.run([sys.executable, "-I", "-c", script, str(root)], cwd=tmp_path, check=True)


@pytest.mark.parametrize("question_id", list(QuestionID))
def test_overall_comparison(question_id, tmp_path):
    request = QuestionInput(question_id)
    reference = pin_teacher_grades(request, tmp_path)
    output = RubricOutput(question_id, rubric())
    verdict = verify_task("generate-rubric", request, output, reference, tmp_path)
    expected_means = {
        answer.student_id: mean(g.mean_score for g in reference.teacher_grades if g.student_id == answer.student_id)
        for answer in reference.question.answers
    }
    grades = score_answers(reference.question.answers, output.rubric)
    error = mean(abs(g.score - expected_means[g.student_id]) for g in grades)
    assert verdict["details"]["teacher_overall_scores"] == expected_means
    assert verdict["details"]["grades_compared"] == 5
    assert verdict["details"]["mean_absolute_error"] == round(error, 3)
    assert verdict["score"] == pytest.approx(1 - error / 3)
    assert verdict["valid"] == (error <= 1.0)
    assert verify_output("get_question", request, get_question(request, tmp_path), tmp_path)["valid"]
    assert verify_output("pin_teacher_grades", request, reference, tmp_path)["valid"]


def test_tool_matches_independent_verifier(tmp_path):
    request = GradeAnswersInput(
        QuestionID.NQ007,
        rubric(),
        [StudentAnswer(str(i), text) for i, text in enumerate(("", "stack", "stack queue", "stack queue heap DFS"))],
    )
    actual = grade_answers(request, tmp_path)
    assert [g.score for g in actual.grades] == [1, 1.75, 2.5, 4]
    assert actual.grades == score_answers(request.answers, request.rubric)
    assert verify_output("grade_answers", request, actual, tmp_path)["valid"]
    tampered = GradeAnswersOutput(request.question_id, [replace(g, score=4) for g in actual.grades])
    assert not verify_output("grade_answers", request, tampered, tmp_path)["valid"]


def test_grading_task_uses_tool_contract_and_needs_no_teacher_reference(tmp_path):
    from contract import TASKS, Task

    assert TASKS[Task.GRADE_ANSWERS] == (GradeAnswersInput, GradeAnswersOutput)
    request = GradeAnswersInput(QuestionID.NQ007, rubric(), [StudentAnswer("custom", "stack queue")])
    output = grade_answers(request, tmp_path)
    assert verify_task("grade-answers", request, output, None, tmp_path)["valid"]
    tampered = replace(output, grades=[replace(output.grades[0], score=4)])
    assert not verify_task("grade-answers", request, tampered, None, tmp_path)["valid"]
    assert not verify_task("grade-answers", request, replace(output, grades=[]), None, tmp_path)["valid"]
    assert not verify_task(
        "grade-answers", request, replace(output, question_id=QuestionID.NQ004), None, tmp_path
    )["valid"]


def test_grading_task_rejects_invalid_inputs(tmp_path):
    request = GradeAnswersInput(QuestionID.NQ007, [], [StudentAnswer("custom", "stack")])
    output = GradeAnswersOutput(request.question_id, [])
    assert not verify_task("grade-answers", request, output, None, tmp_path)["valid"]
    request = replace(request, rubric=rubric(), answers=[StudentAnswer("duplicate", "")] * 2)
    assert not verify_task("grade-answers", request, output, None, tmp_path)["valid"]


@pytest.mark.parametrize("question_id", list(QuestionID))
def test_student_lookup_tasks_and_grading_workflow(question_id, tmp_path):
    from contract import StudentResponseInput
    from plugin.questions import get_student_response, list_students

    request = QuestionInput(question_id)
    students = list_students(request, tmp_path)
    assert verify_task("list-students", request, students, None, tmp_path)["valid"]
    assert not verify_task(
        "list-students", request, replace(students, student_ids=[]), None, tmp_path
    )["valid"]
    answers = []
    for student_id in students.student_ids:
        lookup = StudentResponseInput(question_id, student_id)
        response = get_student_response(lookup, tmp_path)
        assert verify_task("get-student-response", lookup, response, None, tmp_path)["valid"]
        changed = replace(response, answer=replace(response.answer, text="changed response"))
        assert not verify_task("get-student-response", lookup, changed, None, tmp_path)["valid"]
        answers.append(response.answer)
    grading = GradeAnswersInput(question_id, rubric(), answers)
    output = grade_answers(grading, tmp_path)
    assert verify_task("grade-answers", grading, output, None, tmp_path)["valid"]
    assert [grade.student_id for grade in output.grades] == students.student_ids
