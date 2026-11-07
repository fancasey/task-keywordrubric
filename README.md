# Keyword Rubric Grader

Ask NanoAgent to generate a deterministic keyword rubric for a dataset question. The plugin includes NQ004 (stacks in recursion), NQ007 (DFS and BFS), NQ008 (arrays and linked lists), and NQ009 (merge sort for records stored on disk).

For example, ask “Build a keyword rubric for NQ007.”

1. NanoAgent pins the unrounded teacher means with the private reference tool.
2. The agent reads the question, model answer, and teacher criteria using `get_question`. Only the verifier receives the private student responses.
3. The agent submits one rubric for the question. Each of the five dimensions starts at 1 and earns one point for each of three evidence groups. A group matches when any of its alternatives matches. An alternative requires all its `all_of` literal words or phrases to appear and every `none_of` phrase to be absent. Exclusions apply only to their own alternative. Matching ignores case, normalizes Unicode and whitespace, and uses word boundaries.
4. The verifier applies the submitted rubric to the pinned answers and compares all 25 scores with the teacher means. The initial pass threshold is a mean absolute error of 0.75 points on the 1–4 scale. The verifier also reports the error by dimension and the best constant integer baseline for context.

Teacher means come from the mean-score workbook. The question workbook supplies the text and criteria, and the CSV is a dataset export that includes rounded scores. The result measures agreement with teachers on responses the agent did not see while writing the rubric.

## Phrase combinations

Each alternative contains `all_of` (1–8 required phrases) and `none_of` (0–8 excluded phrases). Use an empty `none_of` list for a positive-only alternative. A group accepts any matching alternative and earns at most one point.

For example, this evidence group accepts **"heap" OR ("stack" AND "queue" AND NOT "recursive")**:

```json
{
  "alternatives": [
    {"all_of": ["heap"], "none_of": []},
    {"all_of": ["stack", "queue"], "none_of": ["recursive"]}
  ]
}
```

The answer "heap recursive" still qualifies through the first alternative. The answer "stack queue recursive" does not. Exclusions use the same literal matching and word boundaries as required phrases; they check the whole answer, not the meaning of a sentence.

Each group allows 1–20 alternatives, with phrases of 1–100 normalized characters. Empty required lists, duplicate alternatives within a dimension, repeated phrases within a list, and phrases that are both required and excluded are rejected. Alternatives now use these explicit objects in place of the previous phrase lists.

## Tools

| Tool | Purpose |
| --- | --- |
| `grade_answers` | Grade supplied answers using a specified rubric; returns a score per student and dimension. |
| `get_question` | Return the question, model answer, and teacher criteria. |
| `pin_teacher_grades` | Supply the question data and unrounded teacher means as the private verifier reference. |

Call `grade_answers` with `question_id`, the complete `rubric` (same format as the task output), and `answers` as a list of `{ "student_id": "S1", "text": "..." }` objects. It validates the rubric against the question's five dimensions and rejects duplicate or blank student IDs. Empty answer text earns the base score of 1. It returns `question_id` and `grades`, each containing `student_id`, `dimension_id`, and `score`. It does not load private student answers or teacher grades.

Use this tool for all grading; do not assign grades by hand. The verifier also calls this tool's implementation for private submissions.

### Tasks

| Task | Purpose |
| --- | --- |
| `generate-rubric` | Generate a keyword rubric for NQ004, NQ007, NQ008, or NQ009. The verifier grades the private submissions and compares the grades with pinned teacher means. |

## Layout

- `nanoagent.yaml` defines the plugin, tools, and grading task. `contract.py` defines their data types.
- `src/plugin/` contains the MCP server, tool implementations, and dataset.
- `verifier/` contains the rubric scoring and verification logic. `tests/test_verifier.py` exercises both.
- `product/` and `ui/` contain the product definition and display assets.

## Develop and run

```sh
uv sync --extra dev
uv run pytest
```

NanoAgent launches the MCP server with `uv run --frozen python -m plugin` and sets `NANOAGENT_WORKSPACE` to the plugin's writable workspace.
