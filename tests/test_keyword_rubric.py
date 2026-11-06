from dataclasses import replace

import pytest
from slimconfig import plain_output

from contract import (
    Dimension,
    DimensionRubric,
    EvidenceGroup,
    GradeInput,
    QuestionID,
    QuestionInput,
    QuestionOutput,
    StudentAnswer,
)
from plugin.grading import grade_answers
from plugin.questions import get_question, pin_teacher_grades
from verifier import verify_input, verify_output, verify_task
from verifier.scoring import grade_answers as replay


def criterion(dimension_id, *groups):
    return DimensionRubric(dimension_id, [EvidenceGroup([list(terms) for terms in group]) for group in groups])


@pytest.mark.parametrize("question_id", list(QuestionID))
def test_dataset_and_reference_align(question_id, tmp_path):
    request = QuestionInput(question_id)
    question = get_question(request, tmp_path)
    reference = pin_teacher_grades(request, tmp_path)

    assert question == reference.question
    assert set(plain_output(question)) == {"question_id", "question", "model_answer", "dimensions", "answers"}
    assert all(set(answer) == {"student_id", "text"} for answer in plain_output(question)["answers"])
    assert verify_output("get_question", request, question, tmp_path)["valid"]
    assert verify_output("pin_teacher_grades", request, reference, tmp_path)["valid"]
    assert any(grade.mean_score % 1 for grade in reference.teacher_grades)


def test_evidence_matches_literal_phrases_once_and_requires_all_terms():
    dimension = Dimension("D1", "Data structures", ["", "", "", ""])
    answers = [
        StudentAnswer("S1", "STACK stack. Uses a PRIORITY\nqueue. O(V+E)."),
        StudentAnswer("S2", "stacked priority queue O(V+E)"),
        StudentAnswer("S3", "stack plus queue"),
    ]
    question = QuestionOutput(QuestionID.NQ007, "Question", "Model answer", [dimension], answers)
    rubric = [criterion("D1", [("stack",)], [("stack", "priority queue"), ("heap",)], [("O(V+E)",)])]

    assert [grade.score for grade in replay(question, rubric)] == [4, 2, 2]


def test_grade_question_replays_tool_output_and_compares_it_with_teacher_means(tmp_path):
    request = QuestionInput(QuestionID.NQ007)
    rubric = [
        criterion("D1", [("DFS", "BFS")], [("branch", "level"), ("branch", "depth")], [("backtracking", "neighbors")]),
        criterion("D2", [("stack",)], [("queue",)], [("explicitly",), ("FIFO",)]),
        criterion("D3", [("time complexity",)], [("O(V + E)",), ("O(V+E)",)], [("space complexity", "O(V)")]),
        criterion("D4", [("shortest path",)], [("cycle detection",), ("detecting cycles",)], [("topological sort",)]),
        criterion("D5", [("DFS", "BFS")], [("Time Complexity",)], [("advantages",), ("Applications",)]),
    ]
    arguments = GradeInput(request.question_id, rubric)
    assert verify_input("grade_answers", arguments)["valid"]
    reference = pin_teacher_grades(request, tmp_path)
    output = grade_answers(arguments, tmp_path)
    assert verify_output("grade_answers", arguments, output, tmp_path)["valid"]

    verdict = verify_task("grade-question", request, output, reference, tmp_path)
    assert verdict["valid"], verdict
    assert verdict["details"]["grades_compared"] == 25
    assert len(verdict["details"]["mean_absolute_error_by_dimension"]) == 5

    tampered = replace(output, grades=output.grades[:-1])
    assert not verify_task("grade-question", request, tampered, reference, tmp_path)["valid"]

    wrong_grades = [
        replace(grade, mean_score=1.0 if actual.score >= 3 else 4.0)
        for grade, actual in zip(
            sorted(reference.teacher_grades, key=lambda grade: (grade.student_id, grade.dimension_id)),
            output.grades,
            strict=True,
        )
    ]
    mismatch = verify_task("grade-question", request, output, replace(reference, teacher_grades=wrong_grades), tmp_path)
    assert not mismatch["valid"]
    assert mismatch["details"]["mean_absolute_error"] >= 2.0


def test_invalid_rubrics_are_rejected(tmp_path):
    incomplete = GradeInput(QuestionID.NQ007, [])
    assert not verify_input("grade_answers", incomplete)["valid"]
    with pytest.raises(ValueError, match="every dimension"):
        grade_answers(incomplete, tmp_path)

    duplicate_terms = [criterion(f"D{i}", [("stack",)], [(" STACK ",)], [("queue",)]) for i in range(1, 6)]
    assert not verify_input("grade_answers", GradeInput(QuestionID.NQ007, duplicate_terms))["valid"]
