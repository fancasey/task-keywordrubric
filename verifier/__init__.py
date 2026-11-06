"""Deterministic verification of keyword grading and agreement with teacher means."""

from math import isfinite
from statistics import mean

from contract import Tool

from .scoring import grade_answers, receipt_path, rubric_problem

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
    if Tool(tool) is Tool.GRADE_ANSWERS:
        problem = rubric_problem(value.rubric, DIMENSION_IDS)
        if problem:
            return result(False, problem)
    return result(True, "Valid tool input")


def question_problem(question, question_id):
    if question.question_id != question_id or not question.question.strip() or not question.model_answer.strip():
        return "Question data is missing or refers to the wrong question"
    if [answer.student_id for answer in question.answers] != list(STUDENT_IDS):
        return "Question must contain all five student answers"
    if [dimension.dimension_id for dimension in question.dimensions] != list(DIMENSION_IDS):
        return "Question must contain all five rubric dimensions"
    if any(len(dimension.levels) != 4 for dimension in question.dimensions):
        return "Every dimension needs four level descriptions"
    return None


def teacher_means(reference):
    return {(grade.student_id, grade.dimension_id): grade.mean_score for grade in reference.teacher_grades}


def reference_problem(reference, question_id):
    problem = question_problem(reference.question, question_id)
    if problem:
        return problem
    means = teacher_means(reference)
    expected = {(student, dimension) for student in STUDENT_IDS for dimension in DIMENSION_IDS}
    if len(reference.teacher_grades) != len(expected) or means.keys() != expected:
        return "Teacher reference must contain one mean per student and dimension"
    if any(not isfinite(score) or not 1 <= score <= 4 for score in means.values()):
        return "Teacher means must be between 1 and 4"
    return None


def verify_output(tool, input_value, output_value, workspace):
    tool = Tool(tool)
    if tool is Tool.GET_QUESTION:
        problem = question_problem(output_value, input_value.question_id)
    elif tool is Tool.PIN_TEACHER_GRADES:
        problem = reference_problem(output_value, input_value.question_id)
    else:
        problem = grading_problem(input_value, output_value, workspace)
    return result(not problem, problem or "Valid tool output")


def grading_problem(input_value, output, workspace):
    if output.question_id != input_value.question_id or output.rubric != input_value.rubric:
        return "The grading tool must return its question ID and rubric unchanged"
    problem = rubric_problem(output.rubric, DIMENSION_IDS)
    if problem:
        return problem
    keys = {(grade.student_id, grade.dimension_id) for grade in output.grades}
    expected = {(student, dimension) for student in STUDENT_IDS for dimension in DIMENSION_IDS}
    if len(output.grades) != len(expected) or keys != expected:
        return "The grades must cover every student and dimension exactly once"
    if any(not 1 <= grade.score <= 4 for grade in output.grades):
        return "Every grade must be between 1 and 4"
    if not receipt_path(workspace, output).is_file():
        return "Submit the result returned by grade_answers"
    return None


def verify_task(task, arguments, output, reference, workspace):
    if reference is None:
        return result(False, "The pinned teacher reference is missing")
    problem = reference_problem(reference, arguments.question_id)
    if not problem:
        problem = grading_problem(output, output, workspace)
    if problem:
        return result(False, problem)
    if output.question_id != arguments.question_id:
        return result(False, "The submission refers to a different question")
    if output.grades != grade_answers(reference.question, output.rubric):
        return result(False, "Submitted grades do not match the rubric when replayed")

    means = teacher_means(reference)
    errors = {dimension: [] for dimension in DIMENSION_IDS}
    for grade in output.grades:
        errors[grade.dimension_id].append(abs(grade.score - means[grade.student_id, grade.dimension_id]))
    error = round(mean(error for values in errors.values() for error in values), 3)
    baseline = min(mean(abs(score - gold) for gold in means.values()) for score in range(1, 5))
    return result(
        error <= MAX_MEAN_ERROR,
        f"Mean absolute error: {error:.3f} points (limit {MAX_MEAN_ERROR:.2f})",
        score=1 - error / 3,
        mean_absolute_error=error,
        max_mean_absolute_error=MAX_MEAN_ERROR,
        mean_absolute_error_by_dimension={dimension: round(mean(values), 3) for dimension, values in errors.items()},
        best_constant_baseline=round(baseline, 3),
        grades_compared=len(output.grades),
    )
