"""Exercise rubric constraints at and beyond each supported boundary."""

from dataclasses import replace

import pytest

from contract import DimensionRubric, EvidenceGroup, PhraseAlternative
from verifier.scoring import rubric_problem


def valid_rubric():
    return [
        DimensionRubric("D1", [EvidenceGroup([PhraseAlternative([word], [])]) for word in ("stack", "queue", "heap")])
    ]


@pytest.mark.parametrize("ids", [[], ["D2"], ["D1", "D1"], ["D1", "D2"]])
def test_dimension_coverage(ids):
    rubric = [replace(valid_rubric()[0], dimension_id=dimension) for dimension in ids]
    assert rubric_problem(rubric, ["D1"]) == "The rubric must cover every dimension exactly once"


@pytest.mark.parametrize("count", [0, 1, 2, 4])
def test_group_count(count):
    rubric = valid_rubric()
    rubric[0].evidence = [EvidenceGroup([PhraseAlternative([f"word{i}"], [])]) for i in range(count)]
    assert "exactly three" in rubric_problem(rubric, ["D1"])


@pytest.mark.parametrize(("count", "valid"), [(0, False), (1, True), (20, True), (21, False)])
def test_alternative_count_limits(count, valid):
    rubric = valid_rubric()
    rubric[0].evidence[0].alternatives = [PhraseAlternative([f"word{i}"], []) for i in range(count)]
    assert (rubric_problem(rubric, ["D1"]) is None) == valid


@pytest.mark.parametrize(("count", "valid"), [(0, False), (1, True), (8, True), (9, False)])
def test_required_phrase_count_limits(count, valid):
    rubric = valid_rubric()
    rubric[0].evidence[0].alternatives = [PhraseAlternative([f"word{i}" for i in range(count)], [])]
    assert (rubric_problem(rubric, ["D1"]) is None) == valid


@pytest.mark.parametrize(("count", "valid"), [(0, True), (1, True), (8, True), (9, False)])
def test_excluded_phrase_count_limits(count, valid):
    rubric = valid_rubric()
    rubric[0].evidence[0].alternatives = [PhraseAlternative(["stack"], [f"word{i}" for i in range(count)])]
    assert (rubric_problem(rubric, ["D1"]) is None) == valid


@pytest.mark.parametrize("field", ["all_of", "none_of"])
@pytest.mark.parametrize(
    ("phrase", "valid"),
    [
        ("", False),
        (" \t\n ", False),
        ("x", True),
        ("x" * 100, True),
        ("x" * 101, False),
        ("  x  ", True),
        ("x" * 99 + "ß", False),
        ("Ｓ" * 100, True),
    ],
)
def test_normalized_phrase_length(field, phrase, valid):
    rubric = valid_rubric()
    alternative = replace(PhraseAlternative(["stack"], []), **{field: [phrase]})
    rubric[0].evidence[0].alternatives = [alternative]
    assert (rubric_problem(rubric, ["D1"]) is None) == valid


@pytest.mark.parametrize("field", ["all_of", "none_of"])
def test_duplicate_normalized_phrases_in_one_alternative(field):
    rubric = valid_rubric()
    rubric[0].evidence[0].alternatives = [
        replace(PhraseAlternative(["stack"], []), **{field: ["queue", " ＱＵＥＵＥ "]})
    ]
    assert "distinct" in rubric_problem(rubric, ["D1"])


@pytest.mark.parametrize("same_group", [True, False])
def test_duplicate_alternatives_ignore_phrase_order_and_case(same_group):
    rubric = valid_rubric()
    first = PhraseAlternative(["stack", "queue"], ["heap", "recursive"])
    duplicate = PhraseAlternative([" QUEUE ", "ＳＴＡＣＫ"], ["RECURSIVE", "heap"])
    rubric[0].evidence[0].alternatives = [first]
    if same_group:
        rubric[0].evidence[0].alternatives.append(duplicate)
    else:
        rubric[0].evidence[1].alternatives = [duplicate]
    assert "distinct" in rubric_problem(rubric, ["D1"])


def test_same_terms_with_different_exclusions_are_distinct():
    rubric = valid_rubric()
    rubric[0].evidence[0].alternatives = [
        PhraseAlternative(["stack"], ["heap"]),
        PhraseAlternative(["stack"], ["recursive"]),
    ]
    assert rubric_problem(rubric, ["D1"]) is None


def test_the_same_evidence_can_apply_to_different_dimensions():
    criterion = valid_rubric()[0]
    rubric = [criterion, replace(criterion, dimension_id="D2")]
    assert rubric_problem(rubric, ["D1", "D2"]) is None
