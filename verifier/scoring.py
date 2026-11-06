"""Deterministic rubric rules used by both the grading tool and the verifier."""

import hashlib
import json
import re
import unicodedata
from dataclasses import asdict
from pathlib import Path

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
                terms = [normalize(term) for term in alternative]
                if not 1 <= len(terms) <= 8 or any(not term or len(term) > 100 for term in terms):
                    return f"{criterion.dimension_id}: each alternative needs 1 to 8 phrases, each 1 to 100 characters"
                key = frozenset(terms)
                if len(key) != len(terms) or key in used:
                    return f"{criterion.dimension_id}: evidence alternatives must be distinct"
                used.add(key)
    return None


def phrase_pattern(phrase):
    phrase = normalize(phrase)
    return re.compile(r"(?<!\w)" + re.escape(phrase) + r"(?!\w)")


def grade_answers(question, rubric):
    patterns = {
        criterion.dimension_id: [
            [[phrase_pattern(phrase) for phrase in alternative] for alternative in group.alternatives]
            for group in criterion.evidence
        ]
        for criterion in rubric
    }
    grades = []
    for answer in question.answers:
        text = normalize(answer.text)
        for dimension in question.dimensions:
            groups = patterns[dimension.dimension_id]
            score = 1 + sum(
                any(all(pattern.search(text) for pattern in alternative) for alternative in group) for group in groups
            )
            grades.append(Grade(answer.student_id, dimension.dimension_id, score))
    return grades


def receipt_path(workspace, output):
    content = json.dumps(
        {
            "question_id": output.question_id.value,
            "rubric": [asdict(criterion) for criterion in output.rubric],
            "grades": [asdict(grade) for grade in output.grades],
        },
        sort_keys=True,
    )
    digest = hashlib.sha256(content.encode()).hexdigest()
    return Path(workspace) / ".keyword-rubric" / digest
