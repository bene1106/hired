"""
Prompt loader: parses .md prompt files into structured PromptTemplate objects.

Usage:
    from backend.llm.prompts import load_prompt

    prompt = load_prompt("score_job", profile=profile, job=job)
    # prompt.system, prompt.user, prompt.schema, prompt.examples
"""

from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


def _prompts_dir() -> Path:
    """Resolve the prompts directory, matching the PyInstaller bundle layout."""
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS) / "prompts"
    return Path(__file__).parent.parent / "prompts"


PROMPTS_DIR = _prompts_dir()


@dataclass
class FewShotExample:
    label: str
    input_text: str
    output_text: str


@dataclass
class PromptTemplate:
    name: str
    version: int
    system: str
    user: str
    schema: dict | None = None
    examples: list[FewShotExample] = field(default_factory=list)

    def render(self, **kwargs: Any) -> RenderedPrompt:
        """Render the user template with the given kwargs."""
        return RenderedPrompt(
            system=self.system,
            user=_render_template(self.user, kwargs),
            schema=self.schema,
            examples=self.examples,
        )


@dataclass
class RenderedPrompt:
    system: str
    user: str
    schema: dict | None
    examples: list[FewShotExample]

    def to_messages(self) -> list[dict]:
        """Convert to a list of {role, content} messages for the Anthropic API."""
        messages = []
        # Insert few-shot examples as alternating user/assistant turns
        for ex in self.examples:
            messages.append({"role": "user", "content": ex.input_text})
            messages.append({"role": "assistant", "content": ex.output_text})
        messages.append({"role": "user", "content": self.user})
        return messages


_PROMPT_CACHE: dict[str, PromptTemplate] = {}


def load_prompt(name: str, **kwargs: Any) -> RenderedPrompt:
    """
    Load a prompt template by name and render it with the given kwargs.

    Looks up `backend/prompts/<name>.md`, parses it on first access,
    caches the parsed template, and renders fresh for each call.
    """
    if name not in _PROMPT_CACHE:
        path = PROMPTS_DIR / f"{name}.md"
        if not path.exists():
            raise FileNotFoundError(f"Prompt not found: {path}")
        _PROMPT_CACHE[name] = _parse_prompt_file(path)

    return _PROMPT_CACHE[name].render(**kwargs)


def reset_cache() -> None:
    """Clear the prompt cache. Used in tests after editing prompt files."""
    _PROMPT_CACHE.clear()


def _parse_prompt_file(path: Path) -> PromptTemplate:
    """Parse a prompt .md file into a PromptTemplate."""
    text = path.read_text(encoding="utf-8")

    # Extract version
    version_match = re.search(r"\*\*Version:\*\*\s*(\d+)", text)
    version = int(version_match.group(1)) if version_match else 1

    # Extract sections by their ## headers
    system = _extract_code_block_after(text, r"^##\s*System Prompt\s*$")
    user = _extract_code_block_after(text, r"^##\s*User Prompt Template\s*$")
    schema_text = _extract_code_block_after(text, r"^##\s*Output Schema\s*$", lang="json")

    schema = None
    if schema_text:
        try:
            schema = json.loads(schema_text)
        except json.JSONDecodeError:
            # Some prompts have prose where the schema would be (e.g., "Plain text")
            schema = None

    if not system or not user:
        raise ValueError(
            f"Prompt file {path} is missing System Prompt or User Prompt Template section"
        )

    examples = _extract_few_shot_examples(text)

    return PromptTemplate(
        name=path.stem,
        version=version,
        system=system,
        user=user,
        schema=schema,
        examples=examples,
    )


def _extract_code_block_after(
    text: str, header_pattern: str, lang: str | None = None
) -> str | None:
    """
    Find a header matching `header_pattern`, then extract the next ```-fenced code block.
    Returns the inner text of the code block, or None if not found.
    """
    header_re = re.compile(header_pattern, re.MULTILINE)
    match = header_re.search(text)
    if not match:
        return None

    # Search for next code block after the header
    after = text[match.end() :]
    # Match opening fence (with optional lang) then anything (non-greedy) until closing fence
    fence_re = re.compile(r"```(\w*)\n(.*?)\n```", re.DOTALL)
    block = fence_re.search(after)
    if not block:
        return None

    if lang and block.group(1) and block.group(1).lower() != lang.lower():
        # Wrong language; try the next one (rare case)
        next_after = after[block.end() :]
        block = fence_re.search(next_after)
        if not block:
            return None

    return block.group(2).strip()


_EXAMPLE_HEADER_RE = re.compile(r"^###\s*Example\s*\d*:?\s*(.*)$", re.MULTILINE)


def _extract_few_shot_examples(text: str) -> list[FewShotExample]:
    """
    Find all `### Example N: <label>` sections under `## Few-Shot Examples`.
    For each, extract the input(s) and the output as text.

    The format expected:
        ### Example 1: <label>
        **Input — <subtitle>:**
        ```
        ...
        ```
        ...
        **Output:**
        ```json
        ...
        ```
    """
    # Locate the Few-Shot Examples section
    fs_match = re.search(r"^##\s*Few-Shot Examples?\s*$", text, re.MULTILINE)
    if not fs_match:
        return []

    # Find the next ## heading after Few-Shot Examples to bound the section
    after_fs = text[fs_match.end() :]
    next_section = re.search(r"^##\s+(?!#)", after_fs, re.MULTILINE)
    section_text = after_fs[: next_section.start()] if next_section else after_fs

    examples: list[FewShotExample] = []
    # Split on Example headers
    example_chunks = re.split(_EXAMPLE_HEADER_RE, section_text)
    # First chunk is preamble; pairs after that are (label, content)
    if len(example_chunks) < 3:
        return []

    for i in range(1, len(example_chunks) - 1, 2):
        label = example_chunks[i].strip()
        content = example_chunks[i + 1]
        input_text, output_text = _split_input_output(content)
        if input_text and output_text:
            examples.append(
                FewShotExample(
                    label=label,
                    input_text=input_text.strip(),
                    output_text=output_text.strip(),
                )
            )

    return examples


def _split_input_output(content: str) -> tuple[str, str]:
    """
    Split an example's content into 'input' (everything before **Output:**)
    and 'output' (the first code block after **Output:**).
    """
    output_marker = re.search(r"\*\*Output(?:[^:]*)?:\*\*", content)
    if not output_marker:
        return "", ""

    input_part = content[: output_marker.start()].strip()
    output_part = content[output_marker.end() :]

    # Extract the first fenced code block in output_part as the literal output
    fence_re = re.compile(r"```(?:\w*)\n(.*?)\n```", re.DOTALL)
    output_block = fence_re.search(output_part)
    if not output_block:
        return input_part, ""

    return input_part, output_block.group(1)


def _render_template(template: str, params: dict) -> str:
    """
    Render a `{{key}}` template. We use double-braces explicitly to avoid
    confusion with JSON in the prompts.

    Nested keys via dot notation: {{job.title}} → params['job'].title or params['job']['title']
    """

    def replace(match: re.Match) -> str:
        key = match.group(1).strip()
        value = _lookup(key, params)
        if value is None:
            return ""
        if isinstance(value, (dict, list)):
            return json.dumps(value, indent=2, default=str)
        return str(value)

    return re.sub(r"\{\{\s*([^}]+?)\s*\}\}", replace, template)


def _lookup(key: str, params: dict) -> Any:
    """Look up a dotted key in nested dicts/objects."""
    parts = key.split(".")
    current: Any = params
    for part in parts:
        if current is None:
            return None
        current = current.get(part) if isinstance(current, dict) else getattr(current, part, None)
    return current
