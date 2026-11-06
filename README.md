# Keyword Rubric Grader

Ask NanoAgent to grade a dataset question using a keyword rubric. The plugin includes NQ004 (stacks in recursion), NQ007 (DFS and BFS), NQ008 (arrays and linked lists), and NQ009 (merge sort for records stored on disk).

For example, ask “Build a keyword rubric and grade the five answers for NQ007.”

1. NanoAgent pins the unrounded teacher means with the private reference tool.
2. The agent reads the question, model answer, teacher criteria, and five ungraded student answers using `get_question`.
3. The agent writes one rubric for the question and calls `grade_answers`. Each of the five dimensions starts at 1 and earns one point for each of three evidence groups. A group matches when any of its alternatives matches. An alternative requires all its literal words or phrases to appear. Matching ignores case, normalizes Unicode and whitespace, and uses word boundaries.
4. The agent submits the grading result. The verifier checks that it came from the grading tool, replays the rubric on the pinned answers, and compares all 25 scores with the teacher means. The initial pass threshold is a mean absolute error of 0.75 points on the 1–4 scale. The verifier also reports the error by dimension and the best constant integer baseline for context.

Teacher means come from the mean-score workbook. The question workbook supplies the text and criteria, and the CSV is a dataset export that includes rounded scores. The question tool exposes only ungraded materials. Since the agent can use the answers to build the rubric, the result measures agreement on those answers.

## Development

```sh
uv sync --extra dev
uv run pytest
```
