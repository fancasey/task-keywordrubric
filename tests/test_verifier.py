"""Exercise rubric generation contracts and deterministic verifier grading."""

from dataclasses import replace

import pytest
from slimconfig import plain_output

from contract import (
    Dimension,
    DimensionRubric,
    EvidenceGroup,
    PhraseAlternative,
    QuestionID,
    QuestionInput,
    QuestionOutput,
    RubricOutput,
    StudentAnswer,
)
from plugin.questions import get_question, pin_teacher_grades
from verifier import verify_output, verify_task
from verifier.scoring import grade_answers as replay
from verifier.scoring import rubric_problem


def criterion(dimension_id, *groups):
    return DimensionRubric(
        dimension_id, [EvidenceGroup([PhraseAlternative(list(terms), []) for terms in group]) for group in groups]
    )


@pytest.mark.parametrize("question_id", list(QuestionID))
def test_dataset_and_reference_align(question_id, tmp_path):
    request = QuestionInput(question_id)
    question = get_question(request, tmp_path)
    reference = pin_teacher_grades(request, tmp_path)

    reference_question = plain_output(reference.question)
    answers = reference_question.pop("answers")
    assert set(plain_output(question)) == {"question_id", "question", "model_answer", "dimensions"}
    assert plain_output(question) == reference_question
    assert len(answers) == 5
    assert all(set(answer) == {"student_id", "text"} for answer in answers)
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


def test_alternatives_combine_required_and_excluded_phrases():
    dimension = Dimension("D1", "Traversal", ["", "", "", ""])
    texts = [
        "heap",  # One phrase satisfies the first alternative.
        "stack and queue",  # Both phrases satisfy the second alternative.
        "stack",  # Only half of the second alternative.
        "stack and queue, recursive call",  # An exclusion vetoes that alternative.
        "heap, recursive call",  # The exclusion belongs only to the second alternative.
        "ＳＴＡＣＫ and QUEUE, RECURSIVE\n CALL",  # Exclusions use the same normalization.
        "stack and queue, recursive caller",  # Exclusions respect word boundaries.
    ]
    question = QuestionOutput(
        QuestionID.NQ007,
        "Question",
        "Model",
        [dimension],
        [StudentAnswer(str(i), text) for i, text in enumerate(texts)],
    )
    rubric = [
        DimensionRubric(
            "D1",
            [
                EvidenceGroup(
                    [
                        PhraseAlternative(["heap"], []),
                        PhraseAlternative(["stack", "queue"], ["recursive call", "depth first"]),
                    ]
                ),
                EvidenceGroup([PhraseAlternative(["unmatched two"], [])]),
                EvidenceGroup([PhraseAlternative(["unmatched three"], [])]),
            ],
        )
    ]
    assert rubric_problem(rubric, ["D1"]) is None
    assert [grade.score for grade in replay(question, rubric)] == [2, 2, 1, 1, 2, 1, 2]
    question.answers = [StudentAnswer("both", "heap stack queue"), StudentAnswer("veto", "stack queue depth first")]
    assert [grade.score for grade in replay(question, rubric)] == [2, 1]


@pytest.mark.parametrize(
    "alternative",
    [
        PhraseAlternative([], ["stack"]),
        PhraseAlternative(["stack"], [" ＳＴＡＣＫ "]),
        PhraseAlternative(["stack"], ["queue", " QUEUE "]),
        PhraseAlternative(["stack"], [" "]),
        PhraseAlternative(["stack"], ["x" * 101]),
        PhraseAlternative(["stack"], [str(i) for i in range(9)]),
    ],
)
def test_invalid_phrase_conditions_are_rejected(alternative):
    rubric = [criterion("D1", [("one",)], [("two",)], [("three",)])]
    rubric[0].evidence[0] = EvidenceGroup([alternative])
    assert rubric_problem(rubric, ["D1"]) is not None


def test_alternative_identity_includes_exclusions_and_ignores_order():
    rubric = [criterion("D1", [("one",)], [("two",)], [("three",)])]
    alternatives = [
        PhraseAlternative(["stack", "queue"], ["recursive", "heap"]),
        PhraseAlternative(["stack", "queue"], ["recursive"]),
    ]
    rubric[0].evidence[0] = EvidenceGroup(alternatives)
    assert rubric_problem(rubric, ["D1"]) is None
    alternatives.append(PhraseAlternative([" QUEUE ", "stack"], ["HEAP", "recursive"]))
    assert rubric_problem(rubric, ["D1"]) is not None


def test_verifier_applies_submitted_rubric_and_compares_with_teacher_means(tmp_path):
    request = QuestionInput(QuestionID.NQ007)
    rubric = [
        criterion("D1", [("DFS", "BFS")], [("branch", "level"), ("branch", "depth")], [("backtracking", "neighbors")]),
        criterion("D2", [("stack",)], [("queue",)], [("explicitly",), ("FIFO",)]),
        criterion("D3", [("time complexity",)], [("O(V + E)",), ("O(V+E)",)], [("space complexity", "O(V)")]),
        criterion("D4", [("shortest path",)], [("cycle detection",), ("detecting cycles",)], [("topological sort",)]),
        criterion("D5", [("DFS", "BFS")], [("Time Complexity",)], [("advantages",), ("Applications",)]),
    ]
    output = RubricOutput(request.question_id, rubric)
    assert set(plain_output(output)) == {"question_id", "rubric"}
    reference = pin_teacher_grades(request, tmp_path)
    verdict = verify_task("generate-rubric", request, output, reference, tmp_path)
    assert verdict["valid"], verdict
    assert verdict["details"]["grades_compared"] == 25
    assert len(verdict["details"]["mean_absolute_error_by_dimension"]) == 5

    tampered = replace(output, rubric=output.rubric[:-1])
    assert not verify_task("generate-rubric", request, tampered, reference, tmp_path)["valid"]

    wrong_grades = [
        replace(grade, mean_score=1.0 if actual.score >= 3 else 4.0)
        for grade, actual in zip(
            sorted(reference.teacher_grades, key=lambda grade: (grade.student_id, grade.dimension_id)),
            replay(reference.question, output.rubric),
            strict=True,
        )
    ]
    mismatch = verify_task(
        "generate-rubric", request, output, replace(reference, teacher_grades=wrong_grades), tmp_path
    )
    assert not mismatch["valid"]
    assert mismatch["details"]["mean_absolute_error"] >= 2.0


def test_invalid_rubrics_are_rejected(tmp_path):
    request = QuestionInput(QuestionID.NQ007)
    reference = pin_teacher_grades(request, tmp_path)
    incomplete = RubricOutput(request.question_id, [])
    assert not verify_task("generate-rubric", request, incomplete, reference, tmp_path)["valid"]

    duplicate_terms = [criterion(f"D{i}", [("stack",)], [(" STACK ",)], [("queue",)]) for i in range(1, 6)]
    output = RubricOutput(request.question_id, duplicate_terms)
    assert not verify_task("generate-rubric", request, output, reference, tmp_path)["valid"]


def test_agent_has_grading_tool():
    from contract import TASKS, TOOLS, Task, Tool
    from plugin.__main__ import IMPLEMENTATIONS

    assert {tool.value for tool in TOOLS} == {"get_question", "pin_teacher_grades", "grade_answers"}
    assert set(IMPLEMENTATIONS) == set(Tool)
    assert TASKS[Task.GENERATE_RUBRIC] == (QuestionInput, RubricOutput)


def test_wrong_question_and_missing_reference_are_rejected(tmp_path):
    request = QuestionInput(QuestionID.NQ007)
    reference = pin_teacher_grades(request, tmp_path)
    rubric = [criterion(f"D{i}", [("stack",)], [("queue",)], [("graph",)]) for i in range(1, 6)]
    output = RubricOutput(QuestionID.NQ004, rubric)
    assert not verify_task("generate-rubric", request, output, reference, tmp_path)["valid"]
    assert not verify_task("generate-rubric", request, output, None, tmp_path)["valid"]
