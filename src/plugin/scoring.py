"""Deterministic rubric validation and scoring shared by the grading tool and verifier."""

import re
import unicodedata

from contract import Grade


def normalize(text):
    return " ".join(unicodedata.normalize("NFKC", text).casefold().split())


def rubric_problem(rubric):
    if not 1 <= len(rubric) <= 20:
        return "The rubric needs 1 to 20 keyword groups"
    used = set()
    for group in rubric:
        if not 1 <= len(group.alternatives) <= 20:
            return "each evidence group needs 1 to 20 alternatives"
        for alternative in group.alternatives:
            required = [normalize(term) for term in alternative.all_of]
            excluded = [normalize(term) for term in alternative.none_of]
            if (
                not 1 <= len(required) <= 8
                or len(excluded) > 8
                or any(not term or len(term) > 100 for term in required + excluded)
            ):
                return (
                    "each alternative needs 1 to 8 required phrases and 0 to 8 "
                    "excluded phrases, each 1 to 100 characters"
                )
            key = (frozenset(required), frozenset(excluded))
            if len(key[0]) != len(required) or len(key[1]) != len(excluded) or key in used:
                return "evidence alternatives must be distinct"
            if key[0] & key[1]:
                return "a phrase cannot be both required and excluded"
            used.add(key)
    return None


def phrase_pattern(phrase):
    phrase = normalize(phrase)
    return re.compile(r"(?<!\w)" + re.escape(phrase) + r"(?!\w)")


def grade_answers(question, rubric):
    return score_answers(question.answers, rubric)


def score_answers(answers, rubric):
    patterns = [
        [
            ([phrase_pattern(p) for p in alternative.all_of], [phrase_pattern(p) for p in alternative.none_of])
            for alternative in group.alternatives
        ]
        for group in rubric
    ]
    grades = []
    for answer in answers:
        text = normalize(answer.text)
        matched = sum(
            any(
                all(p.search(text) for p in required) and not any(p.search(text) for p in excluded)
                for required, excluded in group
            )
            for group in patterns
        )
        grades.append(Grade(answer.student_id, 1 + 3 * matched / len(patterns)))
    return grades
