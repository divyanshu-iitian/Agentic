"""Tests for computer use: drawing geometry, vision plumbing, the failsafe, and the browser."""

import asyncio
import http.server
import importlib.util
import threading

import pytest

from agentic.llm.base import ImagePart, Message, ToolSpec
from agentic.llm.providers import AnthropicProvider, OllamaProvider, OpenAICompatibleProvider
from agentic.llm.scripted import ScriptedProvider, tool_reply
from agentic.tools.base import Tool, ToolContext, ToolError, ToolOutput, schema
from agentic.tools.desktop import densify, grid_lines, shape_paths

PIXEL = ImagePart("iVBORw0KGgo=")


def test_shapes_map_into_a_region_and_circles_stay_round() -> None:
    region = (100, 200, 1100, 700)  # 1000 x 500 px canvas
    rect, circle = shape_paths(
        [
            {"type": "rect", "x": 100, "y": 100, "w": 800, "h": 800},
            {"type": "circle", "cx": 500, "cy": 500, "r": 200},
        ],
        region,
    )
    assert rect == [(200, 250), (1000, 250), (1000, 650), (200, 650), (200, 250)]
    xs = [x for x, _ in circle]
    ys = [y for _, y in circle]
    # r=200 units on the smaller axis (500 px) is 100 px in both directions.
    assert (max(xs) - min(xs), max(ys) - min(ys)) == (200, 200)
    assert circle[0] == circle[-1]  # closed


def test_shapes_are_clamped_inside_the_region() -> None:
    (line,) = shape_paths(
        [{"type": "line", "points": [[-500, -500], [5000, 5000]]}], (0, 0, 100, 100)
    )
    assert line == [(2, 2), (97, 97)]


def test_polygon_closes_and_absolute_mode_uses_pixels() -> None:
    (triangle,) = shape_paths([{"type": "polygon", "points": [[10, 10], [50, 10], [30, 40]]}])
    assert triangle == [(10, 10), (50, 10), (30, 40), (10, 10)]


@pytest.mark.parametrize(
    "shapes",
    [[], [{"type": "spiral"}], [{"type": "rect", "x": 1}], [{"type": "line", "points": [[1, 2]]}],
     ["not a shape"], [{"type": "line", "points": [[0, 0], [1, 1]]}] * 61],
)  # fmt: skip
def test_invalid_shapes_are_explained(shapes) -> None:
    with pytest.raises(ToolError):
        shape_paths(shapes)


def test_densify_limits_step_length() -> None:
    dense = densify([(0, 0), (30, 0)], max_step=6)
    assert dense[0] == (0, 0) and dense[-1] == (30, 0)
    assert all(b[0] - a[0] <= 6 for a, b in zip(dense, dense[1:]))
    assert densify([(5, 5)]) == [(5, 5)]


def test_grid_lines_are_screen_aligned() -> None:
    assert grid_lines(0, 350, 100) == [0, 100, 200, 300]
    assert grid_lines(150, 300, 100) == [200, 300, 400]


def test_screenshot_annotation_downscales_and_draws_grid() -> None:
    Image = pytest.importorskip("PIL.Image")

    from agentic.tools.desktop import annotate

    image = Image.new("RGB", (1920, 1080), "white")
    annotated, scale = annotate(image, (0, 0), 960, grid=True)
    assert annotated.size == (960, 540) and scale == 0.5
    assert annotated.getpixel((50, 300)) != (255, 255, 255)  # the x=100 grid line
    plain, _ = annotate(image, (0, 0), 960, grid=False)
    assert plain.getpixel((50, 300)) == (255, 255, 255)


def test_vision_tools_are_hidden_from_blind_models(make_runtime) -> None:
    offered = []

    def responder(messages, tools):
        offered.append({tool.name for tool in tools or []})
        return "ok"

    blind = make_runtime(ScriptedProvider(responder=responder))
    asyncio.run(blind.run("look", head="operator"))
    assert "desktop_ui_tree" in offered[0] and "desktop_screenshot" not in offered[0]

    seeing = make_runtime(ScriptedProvider(responder=responder),
                          providers={"local": {"vision": True}})  # fmt: skip
    asyncio.run(seeing.run("look", head="operator"))
    assert "desktop_screenshot" in offered[1] and "desktop_draw" in offered[1]


def test_tool_images_reach_vision_models_and_old_ones_are_pruned(make_runtime) -> None:
    provider = ScriptedProvider(
        [tool_reply("snap"), tool_reply("snap", n=2), tool_reply("snap", n=3), "I can see it."]
    )
    runtime = make_runtime(provider, providers={"local": {"vision": True}})
    runtime.tools.register(
        Tool("snap", "screenshot", schema({"n": {"type": "integer"}}), "read",
             lambda args, ctx: ToolOutput("captured", [PIXEL]))
    )  # fmt: skip
    outcome = asyncio.run(runtime.run("look three times"))

    assert outcome.output == "I can see it."
    final = provider.calls[-1]
    with_images = [m for m in final if m.images]
    assert len(with_images) == 2  # KEEP_IMAGES
    assert with_images[-1].content.startswith("Image(s) returned by snap")
    assert sum("[older image removed" in m.content for m in final) == 1


def test_consecutive_repeats_only(make_runtime) -> None:
    replies = []
    for _ in range(4):  # observe, act, observe, act ... is not a loop
        replies += [tool_reply("list_dir"), tool_reply("recall", query="x")]
    runtime = make_runtime(ScriptedProvider([*replies, "done"]), limits={"max_steps": 20})
    outcome = asyncio.run(runtime.run("alternate"))
    results = [e for e in runtime.store.events(outcome.run_id) if e["type"] == "tool.result"]
    assert not any("Skipped" in e["data"]["output"] for e in results)


def test_failsafe_halts_the_run(make_runtime) -> None:
    def tripped(args, ctx: ToolContext):
        ctx.runtime.halt("the mouse was moved to a screen corner (failsafe)")
        raise ToolError("Emergency stop")

    provider = ScriptedProvider([tool_reply("trip"), tool_reply("list_dir"), "never reached"])
    runtime = make_runtime(provider)
    runtime.tools.register(Tool("trip", "trips", schema({}), "read", tripped))
    outcome = asyncio.run(runtime.run("move the mouse"))

    assert not outcome.ok and outcome.output.startswith("Stopped: the mouse was moved")
    assert len(provider.calls) == 1
    asyncio.run(runtime.run("next run resets the halt"))
    assert runtime.halt_reason is None


def test_providers_send_images_in_their_own_formats() -> None:
    message = Message("user", "what is this?", images=[PIXEL])
    assert OllamaProvider._message(message)["images"] == ["iVBORw0KGgo="]
    openai = OpenAICompatibleProvider._message(message)["content"]
    assert openai[1]["image_url"]["url"] == "data:image/png;base64,iVBORw0KGgo="
    blocks = AnthropicProvider._messages([Message("tool", "ok", tool_call_id="t1"), message])[0][
        "content"
    ]
    assert [b["type"] for b in blocks] == ["tool_result", "image", "text"]
    assert blocks[1]["source"]["data"] == "iVBORw0KGgo="


def test_ollama_vision_detection(monkeypatch) -> None:
    from agentic.config import ProviderConfig

    provider = OllamaProvider("local", ProviderConfig())

    class Response:
        ok = True

        def json(self):
            return {"capabilities": ["completion", "vision", "tools"]}

    monkeypatch.setattr(provider.session, "post", lambda *a, **k: Response())
    assert provider.supports_vision()


PAGE = b"""<!doctype html><title>Signup</title>
<form onsubmit="document.getElementById('out').textContent='Hello '+this.n.value;return false">
<input name="n" placeholder="Your name"><select name="c"><option>Red</option><option>Blue</option>
</select><button>Send</button><input type="password" value="secret"></form>
<p id="out">waiting</p><a href="/two">Next page</a>"""


@pytest.mark.skipif(not importlib.util.find_spec("playwright"), reason="needs playwright")
def test_browser_session_end_to_end(make_runtime) -> None:
    class Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            body = PAGE if self.path == "/" else b"<title>Two</title><p>Second page</p>"
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *args):
            pass

    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    url = f"http://127.0.0.1:{server.server_address[1]}/"
    runtime = make_runtime(
        ScriptedProvider(),
        overrides={"browser": "auto"},
        network={"allow_private_hosts": True},
        computer={"browser_headless": True, "browser_persistent_profile": False},
    )

    async def scenario():
        ctx = ToolContext(runtime, "r1", "navigator")

        async def call(name, **args):
            result = await runtime.tools.call(name, args, ctx, runtime.gate, 60, 20_000)
            assert result.ok, result.content
            return result.content

        try:
            opened = await call("browser_open", url=url)
            assert "Page: Signup" in opened and '"Your name"' in opened
            assert "secret" not in opened  # password values are never echoed
            ref = {line.split('"')[1]: line.split("]")[0][1:] for line in opened.splitlines()
                   if line.startswith("[") and '"' in line}  # fmt: skip
            await call("browser_type", ref=int(ref["Your name"]), text="Ada")
            await call("browser_select", ref=int(ref["Red Blue"]), option="Blue")
            clicked = await call("browser_click", ref=int(ref["Send"]))
            assert "Clicked" in clicked
            assert "Hello Ada" in await call("browser_snapshot")
            moved = await call("browser_click", ref=int(ref["Next page"]))
            assert "Page: Two" in moved
            assert "Page: Signup" in await call("browser_back")
        finally:
            await runtime.aclose()

    try:
        asyncio.run(scenario())
    except ToolError as exc:  # Chromium binary not installed on this machine
        pytest.skip(str(exc))
    finally:
        server.shutdown()


def test_browser_actions_need_the_browser_permission(make_runtime) -> None:
    runtime = make_runtime(ScriptedProvider())
    ctx = ToolContext(runtime, "r1", "navigator")
    result = asyncio.run(
        runtime.tools.call("browser_click", {"ref": 1}, ctx, runtime.gate, 5, 1000)
    )
    assert not result.ok and "'browser' approval" in result.content


def test_prompt_mode_keeps_images() -> None:
    from agentic.llm.providers import PromptToolProvider

    inner = ScriptedProvider(["fine"])
    PromptToolProvider(inner).complete(
        [Message("user", "see", images=[PIXEL])], [ToolSpec("x", "x", {"type": "object"})]
    )
    assert inner.calls[0][-1].images == [PIXEL]
