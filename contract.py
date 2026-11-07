"""Typed tool and task contracts for the keyword rubric plugin."""

from dataclasses import dataclass
from enum import Enum
from typing import Annotated

from slimconfig import Output


class Tool(Enum):
    LIST_STUDENTS = "list_students"
    GET_STUDENT_RESPONSE = "get_student_response"
    GET_QUESTION = "get_question"
    GRADE_ANSWERS = "grade_answers"
    PIN_TEACHER_GRADES = "pin_teacher_grades"


class Task(Enum):
    LIST_STUDENTS = "list-students"
    GET_STUDENT_RESPONSE = "get-student-response"
    GENERATE_RUBRIC = "generate-rubric"
    GRADE_ANSWERS = "grade-answers"


class QuestionID(Enum):
    NQ004 = "NQ004"
    NQ007 = "NQ007"
    NQ008 = "NQ008"
    NQ009 = "NQ009"


@dataclass
class QuestionInput(Output):
    question_id: Annotated[QuestionID, "Dataset question for the rubric"]


@dataclass
class StudentAnswer(Output):
    student_id: str
    text: str


@dataclass
class StudentResponseInput(QuestionInput):
    student_id: Annotated[str, "Student ID returned by list_students for this question"]


@dataclass
class StudentListOutput(Output):
    question_id: QuestionID
    student_ids: list[str]


@dataclass
class StudentResponseOutput(Output):
    question_id: QuestionID
    answer: StudentAnswer


@dataclass
class QuestionContextOutput(Output):
    question_id: QuestionID
    question: str
    model_answer: str


@dataclass
class QuestionOutput(QuestionContextOutput):
    answers: list[StudentAnswer]


@dataclass
class PhraseAlternative(Output):
    all_of: Annotated[list[str], "Every listed literal phrase must occur in the answer."]
    none_of: Annotated[list[str], "No listed literal phrase may occur in the answer."]


@dataclass
class EvidenceGroup(Output):
    alternatives: Annotated[
        list[PhraseAlternative],
        "Any alternative qualifies when all its required phrases occur and no excluded phrase occurs.",
    ]


@dataclass
class RubricOutput(Output):
    question_id: QuestionID
    rubric: Annotated[list[EvidenceGroup], "1 to 20 equally weighted keyword groups; no teacher criteria required"]


@dataclass
class Grade(Output):
    student_id: str
    score: Annotated[float, "Overall score: 1 + 3 * matched groups / total groups"]


@dataclass
class GradeAnswersInput(RubricOutput):
    answers: Annotated[list[StudentAnswer], "Student answers to grade using the supplied rubric only"]


@dataclass
class GradeAnswersOutput(Output):
    question_id: QuestionID
    grades: list[Grade]


@dataclass
class TeacherGrade(Output):
    student_id: str
    dimension_id: str
    mean_score: Annotated[float, "Unrounded mean of the five teacher scores"]


@dataclass
class ReferenceOutput(Output):
    question: QuestionOutput
    teacher_grades: list[TeacherGrade]


TOOLS = {
    Tool.LIST_STUDENTS: (QuestionInput, StudentListOutput),
    Tool.GET_STUDENT_RESPONSE: (StudentResponseInput, StudentResponseOutput),
    Tool.GRADE_ANSWERS: (GradeAnswersInput, GradeAnswersOutput),
    Tool.GET_QUESTION: (QuestionInput, QuestionContextOutput),
    Tool.PIN_TEACHER_GRADES: (QuestionInput, ReferenceOutput),
}
TASKS = {
    Task.LIST_STUDENTS: (QuestionInput, StudentListOutput),
    Task.GET_STUDENT_RESPONSE: (StudentResponseInput, StudentResponseOutput),
    Task.GENERATE_RUBRIC: (QuestionInput, RubricOutput),
    Task.GRADE_ANSWERS: (GradeAnswersInput, GradeAnswersOutput),
}
