"""Deterministic verification of keyword grading and agreement with teacher means."""

from math import isfinite
from statistics import mean

from contract import GradeAnswersOutput, Task, Tool
from plugin.questions import get_student_response, list_students

from .scoring import grade_answers, rubric_problem, score_answers

DIMENSION_IDS = ("D1", "D2", "D3", "D4", "D5")
STUDENT_IDS = ("S1", "S2", "S3", "S4", "S5")
MAX_MEAN_ERROR = 0.75


def result(valid, message, *, score=None, **details):
    return {
        "valid": valid,
        "score": float(valid) if score is None else score,
        "message": message,
        "details": details,
    }


def verify_input(tool, value):
    Tool(tool)
    return result(True, "Valid tool input")


def question_problem(question, question_id):
    if question.question_id != question_id or not question.question.strip() or not question.model_answer.strip():
        return "Question data is missing or refers to the wrong question"
    return None


def teacher_means(reference):
    return {(grade.student_id, grade.dimension_id): grade.mean_score for grade in reference.teacher_grades}


def reference_problem(reference, question_id):
    problem = question_problem(reference.question, question_id)
    if problem:
        return problem
    if [answer.student_id for answer in reference.question.answers] != list(STUDENT_IDS):
        return "Question must contain all five student answers"
    means = teacher_means(reference)
    expected = {(student, dimension) for student in STUDENT_IDS for dimension in DIMENSION_IDS}
    if len(reference.teacher_grades) != len(expected) or means.keys() != expected:
        return "Teacher reference must contain one mean per student and dimension"
    if any(not isfinite(score) or not 1 <= score <= 4 for score in means.values()):
        return "Teacher means must be between 1 and 4"
    return None


def verify_output(tool, input_value, output_value, workspace):
    tool = Tool(tool)
    if tool is Tool.LIST_STUDENTS:
        problem = None if output_value == list_students(input_value, workspace) else "Student list does not match dataset"
    elif tool is Tool.GET_STUDENT_RESPONSE:
        try:
            expected = get_student_response(input_value, workspace)
            problem = None if output_value == expected else "Student response does not match dataset"
        except ValueError as error:
            problem = str(error)
    elif tool is Tool.GET_QUESTION:
        problem = question_problem(output_value, input_value.question_id)
    elif tool is Tool.PIN_TEACHER_GRADES:
        problem = reference_problem(output_value, input_value.question_id)
    elif tool is Tool.GRADE_ANSWERS:
        problem = rubric_problem(input_value.rubric)
        ids = [answer.student_id for answer in input_value.answers]
        if not problem and (any(not student_id.strip() for student_id in ids) or len(set(ids)) != len(ids)):
            problem = "Student IDs must be nonempty and unique"
        if not problem:
            expected = GradeAnswersOutput(
                input_value.question_id, score_answers(input_value.answers, input_value.rubric)
            )
            problem = None if output_value == expected else "Grades do not match the supplied rubric"
    return result(not problem, problem or "Valid tool output")


def verify_task(task, arguments, output, reference, workspace):
    task = Task(task)
    lookup_tools = {
        Task.LIST_STUDENTS: Tool.LIST_STUDENTS,
        Task.GET_STUDENT_RESPONSE: Tool.GET_STUDENT_RESPONSE,
    }
    if task in lookup_tools:
        return verify_output(lookup_tools[task], arguments, output, workspace)
    if task is Task.GRADE_ANSWERS:
        return verify_output(Tool.GRADE_ANSWERS, arguments, output, workspace)
    if reference is None:
        return result(False, "The pinned teacher reference is missing")
    problem = reference_problem(reference, arguments.question_id)
    if not problem:
        problem = rubric_problem(output.rubric)
    if problem:
        return result(False, problem)
    if output.question_id != arguments.question_id:
        return result(False, "The submission refers to a different question")
    grades = grade_answers(reference.question, output.rubric)

    criterion_means = teacher_means(reference)
    means = {
        student: mean(criterion_means[student, dimension] for dimension in DIMENSION_IDS) for student in STUDENT_IDS
    }
    errors = [abs(grade.score - means[grade.student_id]) for grade in grades]
    error = mean(errors)
    baseline = min(mean(abs(score - gold) for gold in means.values()) for score in range(1, 5))
    return result(
        error <= MAX_MEAN_ERROR,
        f"Mean absolute error: {error:.3f} points (limit {MAX_MEAN_ERROR:.2f})",
        score=1 - error / 3,
        mean_absolute_error=round(error, 3),
        max_mean_absolute_error=MAX_MEAN_ERROR,
        teacher_overall_scores=means,
        grades=[{"student_id": grade.student_id, "score": grade.score} for grade in grades],
        best_constant_baseline=round(baseline, 3),
        grades_compared=len(grades),
    )
