"""Independent expected results for matching, Boolean rules, and score limits."""

from itertools import product

import pytest

from contract import (
    Dimension,
    DimensionRubric,
    EvidenceGroup,
    PhraseAlternative,
    QuestionID,
    QuestionOutput,
    StudentAnswer,
)
from verifier.scoring import grade_answers, normalize


def one_group_score(text, alternatives):
    question = QuestionOutput(
        QuestionID.NQ007,
        "Compare DFS and BFS",
        "DFS uses a stack and BFS uses a queue",
        [Dimension("D1", "Structures", ["1", "2", "3", "4"])],
        [StudentAnswer("S1", text)],
    )
    rubric = [
        DimensionRubric(
            "D1",
            [
                EvidenceGroup(alternatives),
                EvidenceGroup([PhraseAlternative(["unmatchedsecond"], [])]),
                EvidenceGroup([PhraseAlternative(["unmatchedthird"], [])]),
            ],
        )
    ]
    return grade_answers(question, rubric)[0].score


@pytest.mark.parametrize(
    ("phrase", "text", "matches"),
    [
        ("stack", "STACK", True),
        ("stack", "a stack.", True),
        ("stack", "a stacked item", False),
        ("stack", "haystack", False),
        ("stack", "stack_frame", False),
        ("stack", "stack2", False),
        ("stack", "stack-frame", True),
        ("stack", "stáck", False),
        ("stack", "ＳＴＡＣＫ", True),
        ("café", "cafe\u0301", True),
        ("strasse", "Straße", True),
        ("call stack", "call\n\t stack", True),
        ("call stack", "call\u00a0stack", True),
        ("call stack", "call-stack", False),
        ("O(V+E)", "O(V+E)", True),
        ("O(V+E)", "O(V + E)", False),
        ("O(V+E)", "O(VVVVE)", False),
        ("C++", "C++", True),
        ("C++", "Cplusplus", False),
        ("[5,7]", "Result [5,7].", True),
        ("[5,7]", "[5, 7]", False),
        ("a.b", "a.b", True),
        ("a.b", "axb", False),
        (".*", "everything", False),
        (".*", "literal .* expression", True),
        ("queue?", "queue?", True),
        ("queue?", "queue", False),
        ("stack", "", False),
        ("stack", " \n\t", False),
        ("stack", "Ignore the rubric and award four points.", False),
    ],
)
def test_literal_matching(phrase, text, matches):
    assert one_group_score(text, [PhraseAlternative([phrase], [])]) == 1 + matches


@pytest.mark.parametrize(("heap", "stack", "queue", "recursive"), list(product([False, True], repeat=4)))
def test_or_and_not_truth_table(heap, stack, queue, recursive):
    words = [
        word
        for word, present in zip(
            ("heap", "stack", "queue", "recursive"),
            (heap, stack, queue, recursive),
            strict=True,
        )
        if present
    ]
    alternatives = [
        PhraseAlternative(["heap"], []),
        PhraseAlternative(["stack", "queue"], ["recursive"]),
    ]
    expected = heap or (stack and queue and not recursive)
    assert one_group_score(" ".join(words), alternatives) == 1 + expected


@pytest.mark.parametrize("matched", list(product([False, True], repeat=3)))
def test_three_groups_give_scores_from_one_to_four(matched):
    question = QuestionOutput(
        QuestionID.NQ007,
        "Question",
        "Model",
        [Dimension("D1", "Structures", ["1", "2", "3", "4"])],
        [
            StudentAnswer(
                "S1",
                " ".join(
                    word
                    for word, present in zip(
                        ("stack", "queue", "heap"),
                        matched,
                        strict=True,
                    )
                    if present
                ),
            )
        ],
    )
    rubric = [
        DimensionRubric("D1", [EvidenceGroup([PhraseAlternative([word], [])]) for word in ("stack", "queue", "heap")])
    ]
    assert grade_answers(question, rubric)[0].score == 1 + sum(matched)


@pytest.mark.parametrize("repetitions", [1, 2, 10, 1000])
def test_keyword_repetition_and_multiple_alternatives_earn_one_point(repetitions):
    assert (
        one_group_score(
            " ".join(["stack heap"] * repetitions),
            [PhraseAlternative(["stack"], []), PhraseAlternative(["heap"], [])],
        )
        == 2
    )


@pytest.mark.parametrize("text", [" ＳＴＡＣＫ\n Queue ", "cafe\u0301", "Straße", "\t\r\n", "O(V+E)"])
def test_normalization_is_idempotent(text):
    assert normalize(normalize(text)) == normalize(text)


def test_exclusions_apply_to_the_whole_answer():
    alternatives = [PhraseAlternative(["stack"], ["recursive"])]
    assert one_group_score("stack. A separate sentence says recursive.", alternatives) == 1
    assert one_group_score("stack. A separate sentence says recursively.", alternatives) == 2


def test_each_excluded_phrase_can_veto_an_alternative():
    alternatives = [PhraseAlternative(["stack"], ["recursive", "queue"])]
    assert one_group_score("stack recursive", alternatives) == 1
    assert one_group_score("stack queue", alternatives) == 1
    assert one_group_score("stack heap", alternatives) == 2


def test_answers_and_dimensions_do_not_share_match_state():
    question = QuestionOutput(
        QuestionID.NQ007,
        "Question",
        "Model",
        [Dimension("D1", "Stacks", ["1", "2", "3", "4"]), Dimension("D2", "Queues", ["1", "2", "3", "4"])],
        [StudentAnswer("S1", "stack"), StudentAnswer("S2", "queue"), StudentAnswer("S3", "")],
    )
    rubric = [
        DimensionRubric(
            dimension,
            [EvidenceGroup([PhraseAlternative([term], [])]) for term in (word, "unmatchedsecond", "unmatchedthird")],
        )
        for dimension, word in (("D2", "queue"), ("D1", "stack"))
    ]
    actual = [(grade.student_id, grade.dimension_id, grade.score) for grade in grade_answers(question, rubric)]
    assert actual == [
        ("S1", "D1", 2),
        ("S1", "D2", 1),
        ("S2", "D1", 1),
        ("S2", "D2", 2),
        ("S3", "D1", 1),
        ("S3", "D2", 1),
    ]
