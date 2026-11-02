"""Shared fixtures for the agentic runtime tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from agentic.config import Settings
from agentic.runtime import Runtime


@pytest.fixture
def make_runtime(tmp_path: Path):
    """Build a Runtime in a temp directory that uses the given provider for every head."""
    created: list[Runtime] = []

    def factory(provider, *, approver=None, overrides=None, **settings_fields) -> Runtime:
        settings = Settings(root=tmp_path, **settings_fields)
        runtime = Runtime(
            settings,
            approver=approver,
            provider_factory=lambda name, config: provider,
            permission_overrides=overrides,
        )
        created.append(runtime)
        return runtime

    yield factory
    for runtime in created:
        runtime.close()
        runtime.store.close()
