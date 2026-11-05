"""Providers return structured tool calls, never executable commands."""
from dataclasses import dataclass
import json
from typing import Protocol

@dataclass(frozen=True)
class Completion:
    tool: str
    arguments: dict
    input_tokens: int
    output_tokens: int
    cost_microusd: int
    estimated: bool = True

class Provider(Protocol):
    def review(self, agent: str, files: dict[str, str]) -> Completion: ...

class MockProvider:
    """Deterministic fixture-friendly reviewer. Token counts are estimates, cost is zero."""
    def review(self, agent, files):
        findings = []
        for path, content in sorted(files.items()):
            for number, line in enumerate(content.splitlines(), 1):
                if agent == 'security' and 'shell=True' in line:
                    findings.append(dict(severity='high', path=path, line=number, evidence=line.strip()[:500], message='Shell interpretation may allow command injection. Pass an argument vector and keep shell=False.'))
                if agent == 'reliability' and 'except: pass' in line:
                    findings.append(dict(severity='medium', path=path, line=number, evidence=line.strip()[:500], message='Swallowed failures hide operational problems. Handle specific errors and record context.'))
        return Completion('submit_findings', {'findings': findings}, max(1, len(json.dumps(files)) // 4), max(1, len(json.dumps(findings)) // 4), 0)

class JsonReplayProvider:
    """Adapter for captured model output; validates it at the same trust boundary.

    Real hosted providers can implement Provider without changing orchestration.
    No paid provider/API key is required or implicitly selected.
    """
    def __init__(self, completions: dict):
        self.completions = completions

    def review(self, agent, files):
        value = self.completions[agent]
        return Completion(**value)
