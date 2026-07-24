"""Typed schemas for every action the model may request.

The model never calls Python functions directly. Its JSON output must match one
of these bounded schemas before an executor can see it.
"""

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

ShortText = Annotated[str, Field(min_length=1, max_length=1_000)]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class OpenAppArgs(StrictModel):
    name: Annotated[str, Field(min_length=1, max_length=80)]


class ClickArgs(StrictModel):
    x: Annotated[int, Field(ge=0, le=20_000)]
    y: Annotated[int, Field(ge=0, le=20_000)]


class TypeArgs(StrictModel):
    text: Annotated[str, Field(max_length=50_000)]


class ScrollArgs(StrictModel):
    amount: Annotated[int, Field(ge=-10_000, le=10_000)]


class WaitArgs(StrictModel):
    seconds: Annotated[float, Field(ge=0, le=30)]


class SaveFileArgs(StrictModel):
    filename: Annotated[str, Field(max_length=255)] = ""


class BrowserOpenArgs(StrictModel):
    url: Annotated[str, Field(min_length=1, max_length=2_048)]


class BrowserSearchArgs(StrictModel):
    query: ShortText


class BrowserClickArgs(StrictModel):
    selector: ShortText


class BrowserScrollArgs(StrictModel):
    amount: Annotated[int, Field(ge=-10_000, le=10_000)]


class BrowserExtractArgs(StrictModel):
    goal: ShortText


class StopArgs(StrictModel):
    success: bool = True
    reason: Annotated[str, Field(max_length=500)] = ""


class OpenAppAction(StrictModel):
    action: Literal["open_app"]
    args: OpenAppArgs


class ClickAction(StrictModel):
    action: Literal["click"]
    args: ClickArgs


class TypeAction(StrictModel):
    action: Literal["type"]
    args: TypeArgs


class ScrollAction(StrictModel):
    action: Literal["scroll"]
    args: ScrollArgs


class WaitAction(StrictModel):
    action: Literal["wait"]
    args: WaitArgs


class VSCodeOpenAction(StrictModel):
    action: Literal["vscode_open"]
    args: StrictModel = Field(default_factory=StrictModel)


class VSCodeNewFileAction(StrictModel):
    action: Literal["vscode_new_file"]
    args: StrictModel = Field(default_factory=StrictModel)


class VSCodeSaveFileAction(StrictModel):
    action: Literal["vscode_save_file"]
    args: SaveFileArgs = Field(default_factory=SaveFileArgs)


class BrowserOpenAction(StrictModel):
    action: Literal["browser_open"]
    args: BrowserOpenArgs


class BrowserSearchAction(StrictModel):
    action: Literal["browser_search"]
    args: BrowserSearchArgs


class BrowserClickAction(StrictModel):
    action: Literal["browser_click"]
    args: BrowserClickArgs


class BrowserScrollAction(StrictModel):
    action: Literal["browser_scroll"]
    args: BrowserScrollArgs


class BrowserExtractAction(StrictModel):
    action: Literal["browser_extract"]
    args: BrowserExtractArgs


class StopAction(StrictModel):
    action: Literal["stop"]
    args: StopArgs = Field(default_factory=StopArgs)


AgentAction = (
    OpenAppAction
    | ClickAction
    | TypeAction
    | ScrollAction
    | WaitAction
    | VSCodeOpenAction
    | VSCodeNewFileAction
    | VSCodeSaveFileAction
    | BrowserOpenAction
    | BrowserSearchAction
    | BrowserClickAction
    | BrowserScrollAction
    | BrowserExtractAction
    | StopAction
)

ACTION_TYPES: dict[str, type[AgentAction]] = {
    "open_app": OpenAppAction,
    "click": ClickAction,
    "type": TypeAction,
    "scroll": ScrollAction,
    "wait": WaitAction,
    "vscode_open": VSCodeOpenAction,
    "vscode_new_file": VSCodeNewFileAction,
    "vscode_save_file": VSCodeSaveFileAction,
    "browser_open": BrowserOpenAction,
    "browser_search": BrowserSearchAction,
    "browser_click": BrowserClickAction,
    "browser_scroll": BrowserScrollAction,
    "browser_extract": BrowserExtractAction,
    "stop": StopAction,
}


def parse_action(action_dict: dict) -> AgentAction:
    """Parse untrusted model output into one supported, bounded action."""
    action_name = action_dict.get("action")
    action_class = ACTION_TYPES.get(action_name)
    if action_class is None:
        raise ValueError(f"Unknown action: {action_name}")
    return action_class.model_validate(action_dict)
