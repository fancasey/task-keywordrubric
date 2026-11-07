"""Exercise the plugin through its real MCP stdio entry point."""

import asyncio
import os
import sys
from pathlib import Path

import pytest
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from contract import QuestionID
from plugin import __main__ as server_module


def test_real_mcp_question_tools_and_invalid_requests(tmp_path):
    async def exercise():
        parameters = StdioServerParameters(
            command=sys.executable,
            args=["-m", "plugin"],
            cwd=str(Path(__file__).resolve().parents[1]),
            env={**os.environ, "NANOAGENT_WORKSPACE": str(tmp_path)},
        )
        async with stdio_client(parameters) as (read, write), ClientSession(read, write) as session:
            await session.initialize()
            listed = await session.list_tools()
            assert {tool.name for tool in listed.tools} == {"get_question", "pin_teacher_grades", "grade_answers"}
            for question_id in QuestionID:
                request = {"question_id": question_id.value}
                public = await session.call_tool("get_question", request)
                private = await session.call_tool("pin_teacher_grades", request)
                assert not public.isError and not private.isError
                assert set(public.structuredContent) == {"question_id", "question", "model_answer"}
                assert public.structuredContent["question_id"] == question_id.value
                reference = private.structuredContent
                assert len(reference["teacher_grades"]) == 25
                assert len(reference["question"]["answers"]) == 5
                assert {key: value for key, value in reference["question"].items() if key != "answers"} == (
                    public.structuredContent
                )

            rubric = [{"alternatives": [{"all_of": [word], "none_of": []}]} for word in ("stack", "queue", "heap")]
            grading_request = {
                "question_id": "NQ007",
                "rubric": rubric,
                "answers": [{"student_id": "custom", "text": "STACK queue"}],
            }
            graded = await session.call_tool("grade_answers", grading_request)
            assert not graded.isError
            assert graded.structuredContent == {
                "question_id": "NQ007",
                "grades": [{"student_id": "custom", "score": 3}],
            }
            for changes in (
                {"rubric": []},
                {"answers": [{"student_id": "", "text": "stack"}]},
                {"answers": grading_request["answers"] * 2},
            ):
                rejected = await session.call_tool("grade_answers", {**grading_request, **changes})
                assert rejected.isError

            for name, arguments in [
                ("get_question", {}),
                ("get_question", {"question_id": "NQ001"}),
                ("get_question", {"question_id": None}),
                ("get_question", {"question_id": 7}),
                ("pin_teacher_grades", {"question_id": "NQ012"}),
                ("unknown_tool", {"question_id": "NQ007"}),
            ]:
                response = await session.call_tool(name, arguments)
                assert response.isError, (name, arguments)

    asyncio.run(exercise())
    assert list(tmp_path.iterdir()) == []


def test_server_requires_workspace_environment(monkeypatch):
    monkeypatch.delenv("NANOAGENT_WORKSPACE", raising=False)
    with pytest.raises(SystemExit, match="NANOAGENT_WORKSPACE is not set"):
        server_module.main()


def test_server_requires_an_implementation_for_each_tool(monkeypatch, tmp_path):
    monkeypatch.setenv("NANOAGENT_WORKSPACE", str(tmp_path))
    monkeypatch.setattr(server_module, "IMPLEMENTATIONS", {})
    with pytest.raises(SystemExit, match="IMPLEMENTATIONS must implement every"):
        server_module.main()


def test_server_rejects_an_implementation_returning_the_wrong_contract(monkeypatch, tmp_path):
    from contract import Tool

    monkeypatch.setenv("NANOAGENT_WORKSPACE", str(tmp_path))
    monkeypatch.setitem(server_module.IMPLEMENTATIONS, Tool.GET_QUESTION, lambda arguments, workspace: None)
    with pytest.raises(TypeError, match="get_question returned NoneType"):
        asyncio.run(server_module.call_tool("get_question", {"question_id": "NQ007"}))


def test_every_contract_field_is_required():
    from dataclasses import MISSING, fields

    from slimconfig import Output, build_output

    import contract

    for declaration in vars(contract).values():
        if isinstance(declaration, type) and issubclass(declaration, Output) and declaration is not Output:
            for field in fields(declaration):
                assert field.default is MISSING, (declaration.__name__, field.name)
                assert field.default_factory is MISSING, (declaration.__name__, field.name)

    for given, made in (*contract.TOOLS.values(), *contract.TASKS.values()):
        assert given.__name__.endswith("Input")
        assert made.__name__.endswith("Output")

    # Required exclusions can still be an explicitly empty list.
    alternative = build_output({"all_of": ["stack"], "none_of": []}, contract.PhraseAlternative)
    assert alternative.none_of == []
