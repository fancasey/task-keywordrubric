"""Independent deterministic rubric validation and scoring for verification."""

import re
import unicodedata

from contract import Grade


def normalize(text):
    return " ".join(unicodedata.normalize("NFKC", text).casefold().split())


def rubric_problem(rubric, dimension_ids):
    ids = [criterion.dimension_id for criterion in rubric]
    if sorted(ids) != sorted(dimension_ids):
        return "The rubric must cover every dimension exactly once"
    for criterion in rubric:
        if len(criterion.evidence) != 3:
            return f"{criterion.dimension_id} must have exactly three evidence groups"
        used = set()
        for group in criterion.evidence:
            if not 1 <= len(group.alternatives) <= 20:
                return f"{criterion.dimension_id}: each evidence group needs 1 to 20 alternatives"
            for alternative in group.alternatives:
                required = [normalize(term) for term in alternative.all_of]
                excluded = [normalize(term) for term in alternative.none_of]
                if (
                    not 1 <= len(required) <= 8
                    or len(excluded) > 8
                    or any(not term or len(term) > 100 for term in required + excluded)
                ):
                    return (
                        f"{criterion.dimension_id}: each alternative needs 1 to 8 required phrases and 0 to 8 "
                        "excluded phrases, each 1 to 100 characters"
                    )
                key = (frozenset(required), frozenset(excluded))
                if len(key[0]) != len(required) or len(key[1]) != len(excluded) or key in used:
                    return f"{criterion.dimension_id}: evidence alternatives must be distinct"
                if key[0] & key[1]:
                    return f"{criterion.dimension_id}: a phrase cannot be both required and excluded"
                used.add(key)
    return None


def phrase_pattern(phrase):
    phrase = normalize(phrase)
    return re.compile(r"(?<!\w)" + re.escape(phrase) + r"(?!\w)")


def grade_answers(question, rubric):
    return score_answers(question.answers, rubric, [dimension.dimension_id for dimension in question.dimensions])


def score_answers(answers, rubric, dimension_ids):
    patterns = {
        criterion.dimension_id: [
            [
                (
                    [phrase_pattern(phrase) for phrase in alternative.all_of],
                    [phrase_pattern(phrase) for phrase in alternative.none_of],
                )
                for alternative in group.alternatives
            ]
            for group in criterion.evidence
        ]
        for criterion in rubric
    }
    grades = []
    for answer in answers:
        text = normalize(answer.text)
        for dimension_id in dimension_ids:
            groups = patterns[dimension_id]
            score = 1 + sum(
                any(
                    all(pattern.search(text) for pattern in required)
                    and not any(pattern.search(text) for pattern in excluded)
                    for required, excluded in group
                )
                for group in groups
            )
            grades.append(Grade(answer.student_id, dimension_id, score))
    return grades
