"""Apply a rubric to the dataset and record the result in the run workspace."""

from contract import GradeOutput
from verifier.scoring import grade_answers as score_answers
from verifier.scoring import receipt_path, rubric_problem

from .questions import get_question


def grade_answers(arguments, workspace):
    question = get_question(arguments, workspace)
    problem = rubric_problem(arguments.rubric, [dimension.dimension_id for dimension in question.dimensions])
    if problem:
        raise ValueError(problem)
    output = GradeOutput(arguments.question_id, arguments.rubric, score_answers(question, arguments.rubric))
    receipt = receipt_path(workspace, output)
    receipt.parent.mkdir(exist_ok=True)
    receipt.touch()
    return output
