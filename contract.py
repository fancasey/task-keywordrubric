"""Typed tool and task contracts for the keyword rubric plugin."""

from dataclasses import dataclass
from enum import Enum
from typing import Annotated

from slimconfig import Output


class Tool(Enum):
    GET_QUESTION = "get_question"
    GRADE_ANSWERS = "grade_answers"
    PIN_TEACHER_GRADES = "pin_teacher_grades"


class Task(Enum):
    GENERATE_RUBRIC = "generate-rubric"


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
class Dimension(Output):
    dimension_id: str
    name: str
    levels: Annotated[list[str], "Teacher descriptions for scores 1, 2, 3, and 4, in order"]


@dataclass
class QuestionContextOutput(Output):
    question_id: QuestionID
    question: str
    model_answer: str
    dimensions: list[Dimension]


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
class DimensionRubric(Output):
    dimension_id: str
    evidence: Annotated[
        list[EvidenceGroup], "Exactly three distinct evidence groups. Each matching group earns one point above 1."
    ]


@dataclass
class RubricOutput(Output):
    question_id: QuestionID
    rubric: list[DimensionRubric]


@dataclass
class Grade(Output):
    student_id: str
    dimension_id: str
    score: Annotated[int, "Keyword rubric score from 1 to 4"]


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
    Tool.GRADE_ANSWERS: (GradeAnswersInput, GradeAnswersOutput),
    Tool.GET_QUESTION: (QuestionInput, QuestionContextOutput),
    Tool.PIN_TEACHER_GRADES: (QuestionInput, ReferenceOutput),
}
TASKS = {Task.GENERATE_RUBRIC: (QuestionInput, RubricOutput)}
