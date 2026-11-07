"""Private-reference integrity and independently calculated error metrics."""

from copy import deepcopy
from dataclasses import replace

import pytest

from contract import (
    Dimension,
    DimensionRubric,
    EvidenceGroup,
    PhraseAlternative,
    QuestionID,
    QuestionInput,
    QuestionOutput,
    ReferenceOutput,
    RubricOutput,
    StudentAnswer,
    TeacherGrade,
)
from verifier import verify_output, verify_task


@pytest.fixture
def grading_case():
    request = QuestionInput(QuestionID.NQ007)
    dimensions = [Dimension(f"D{i}", f"Dimension {i}", ["poor", "fair", "good", "excellent"]) for i in range(1, 6)]
    answers = [StudentAnswer(f"S{i}", "Answer with no matching terms.") for i in range(1, 6)]
    question = QuestionOutput(request.question_id, "Question", "Model answer", dimensions, answers)
    reference = ReferenceOutput(
        question,
        [
            TeacherGrade(answer.student_id, dimension.dimension_id, 1.0)
            for answer in answers
            for dimension in dimensions
        ],
    )
    output = RubricOutput(
        request.question_id,
        [
            DimensionRubric(
                dimension.dimension_id,
                [EvidenceGroup([PhraseAlternative([word], [])]) for word in ("stack", "queue", "heap")],
            )
            for dimension in dimensions
        ],
    )
    return request, output, reference


@pytest.mark.parametrize(
    ("error", "passes"),
    [(0, True), (0.5, True), (0.7499, True), (0.75, True), (0.7501, False), (1.0, False), (3.0, False)],
)
def test_pass_threshold_uses_unrounded_error(grading_case, tmp_path, error, passes):
    request, output, reference = grading_case
    for grade in reference.teacher_grades:
        grade.mean_score = 1 + error
    verdict = verify_task("generate-rubric", request, output, reference, tmp_path)
    assert verdict["valid"] is passes
    assert verdict["score"] == pytest.approx(1 - error / 3)
    assert verdict["details"]["grades_compared"] == 25


def corrupt_reference(reference, case):
    if case == "wrong-question":
        reference.question.question_id = QuestionID.NQ004
    elif case == "blank-question":
        reference.question.question = " \n "
    elif case == "blank-model":
        reference.question.model_answer = ""
    elif case == "missing-dimension":
        reference.question.dimensions.pop()
    elif case == "duplicate-dimension":
        reference.question.dimensions[1].dimension_id = "D1"
    elif case == "unknown-dimension":
        reference.question.dimensions[0].dimension_id = "D99"
    elif case == "missing-level":
        reference.question.dimensions[0].levels.pop()
    elif case == "extra-level":
        reference.question.dimensions[0].levels.append("extra")
    elif case == "missing-answer":
        reference.question.answers.pop()
    elif case == "duplicate-answer":
        reference.question.answers[1].student_id = "S1"
    elif case == "unknown-answer":
        reference.question.answers[0].student_id = "S99"
    elif case == "missing-grade":
        reference.teacher_grades.pop()
    elif case == "extra-grade":
        reference.teacher_grades.append(deepcopy(reference.teacher_grades[0]))
    elif case == "duplicate-grade":
        reference.teacher_grades[1] = deepcopy(reference.teacher_grades[0])
    elif case == "unknown-grade-student":
        reference.teacher_grades[0].student_id = "S99"
    elif case == "unknown-grade-dimension":
        reference.teacher_grades[0].dimension_id = "D99"
    else:
        reference.teacher_grades[0].mean_score = {
            "nan": float("nan"),
            "positive-infinity": float("inf"),
            "negative-infinity": -float("inf"),
            "below-range": 0.999,
            "above-range": 4.001,
        }[case]


@pytest.mark.parametrize(
    "case",
    [
        "wrong-question",
        "blank-question",
        "blank-model",
        "missing-dimension",
        "duplicate-dimension",
        "unknown-dimension",
        "missing-level",
        "extra-level",
        "missing-answer",
        "duplicate-answer",
        "unknown-answer",
        "missing-grade",
        "extra-grade",
        "duplicate-grade",
        "unknown-grade-student",
        "unknown-grade-dimension",
        "nan",
        "positive-infinity",
        "negative-infinity",
        "below-range",
        "above-range",
    ],
)
def test_corrupt_reference_fails_tool_and_task_checks(grading_case, tmp_path, case):
    request, output, reference = grading_case
    corrupt_reference(reference, case)
    for verdict in (
        verify_output("pin_teacher_grades", request, reference, tmp_path),
        verify_task("generate-rubric", request, output, reference, tmp_path),
    ):
        assert verdict["valid"] is False
        assert verdict["score"] == 0
        assert verdict["message"]


def test_missing_reference_fails_before_scoring(grading_case, tmp_path):
    request, output, _ = grading_case
    verdict = verify_task("generate-rubric", request, output, None, tmp_path)
    assert verdict["valid"] is False
    assert verdict["score"] == 0


def test_submission_for_a_different_question_is_rejected(grading_case, tmp_path):
    request, output, reference = grading_case
    output.question_id = QuestionID.NQ004
    assert not verify_task("generate-rubric", request, output, reference, tmp_path)["valid"]


def test_unrounded_teacher_means_and_dimension_metrics(grading_case, tmp_path):
    request, output, reference = grading_case
    for grade in reference.teacher_grades:
        grade.mean_score = 1 + int(grade.dimension_id[-1]) / 10
    verdict = verify_task("generate-rubric", request, output, reference, tmp_path)
    assert verdict["details"]["mean_absolute_error"] == pytest.approx(0.3)
    assert verdict["details"]["mean_absolute_error_by_dimension"] == {
        "D1": 0.1,
        "D2": 0.2,
        "D3": 0.3,
        "D4": 0.4,
        "D5": 0.5,
    }
    assert verdict["score"] == pytest.approx(0.9)
    assert verdict["details"]["best_constant_baseline"] == pytest.approx(0.3)


def test_opposite_errors_do_not_cancel(grading_case, tmp_path):
    request, output, reference = grading_case
    for answer in reference.question.answers:
        answer.text = "stack"
    for grade in reference.teacher_grades:
        grade.mean_score = 1.0 if grade.student_id in ("S1", "S2") else 3.0
    verdict = verify_task("generate-rubric", request, output, reference, tmp_path)
    assert verdict["valid"] is False
    assert verdict["details"]["mean_absolute_error"] == 1.0


def test_rubric_order_and_reference_grade_order_do_not_change_error(grading_case, tmp_path):
    request, output, reference = grading_case
    before = verify_task("generate-rubric", request, output, reference, tmp_path)
    reference.teacher_grades.reverse()
    output.rubric.reverse()
    assert verify_task("generate-rubric", request, output, reference, tmp_path) == before


def test_verification_is_deterministic_and_does_not_mutate_inputs(grading_case, tmp_path):
    request, output, reference = grading_case
    before = deepcopy(grading_case)
    first = verify_task("generate-rubric", request, output, reference, tmp_path)
    second = verify_task("generate-rubric", request, output, reference, tmp_path)
    assert first == second
    assert grading_case == before
    assert list(tmp_path.iterdir()) == []


def test_multiple_questions_can_be_verified_without_shared_state(grading_case, tmp_path):
    request, output, reference = grading_case
    first = verify_task("generate-rubric", request, output, reference, tmp_path)
    other_question = replace(reference.question, question_id=QuestionID.NQ004)
    other_reference = replace(reference, question=other_question)
    other_output = replace(output, question_id=QuestionID.NQ004)
    assert (
        verify_task(
            "generate-rubric",
            QuestionInput(QuestionID.NQ004),
            other_output,
            other_reference,
            tmp_path,
        )
        == first
    )
