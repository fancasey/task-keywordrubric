"""Grade caller-supplied answers using a validated keyword rubric."""

from contract import GradeAnswersOutput, QuestionOutput
from plugin.questions import get_question
from plugin.scoring import grade_answers as score_answers
from plugin.scoring import rubric_problem


def grade_answers(arguments, workspace):
    context = get_question(arguments, workspace)
    problem = rubric_problem(arguments.rubric, [d.dimension_id for d in context.dimensions])
    if problem:
        raise ValueError(problem)
    ids = [answer.student_id for answer in arguments.answers]
    if any(not student_id.strip() for student_id in ids) or len(set(ids)) != len(ids):
        raise ValueError("Student IDs must be nonempty and unique")
    question = QuestionOutput(
        context.question_id, context.question, context.model_answer, context.dimensions, arguments.answers
    )
    return GradeAnswersOutput(arguments.question_id, score_answers(question, arguments.rubric))
