"""Check dataset lookups against a verifier-owned response snapshot."""

from contract import StudentAnswer, StudentListOutput, StudentResponseOutput

from .student_answers import STUDENT_ANSWERS


def student_answers(question_id):
    return STUDENT_ANSWERS[question_id.value]


def list_students(arguments, workspace):
    return StudentListOutput(arguments.question_id, list(student_answers(arguments.question_id)))


def get_student_response(arguments, workspace):
    answers = student_answers(arguments.question_id)
    if arguments.student_id not in answers:
        raise ValueError(f"Unknown student ID for {arguments.question_id.value}: {arguments.student_id}")
    return StudentResponseOutput(
        arguments.question_id, StudentAnswer(arguments.student_id, answers[arguments.student_id])
    )
