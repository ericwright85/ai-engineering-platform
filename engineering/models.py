from dataclasses import asdict, dataclass
from typing import Literal

@dataclass(frozen=True)
class Finding:
    severity: Literal['low', 'medium', 'high', 'critical']
    path: str
    line: int
    evidence: str
    message: str
    agent: str

    @classmethod
    def parse(cls, value: dict, files: dict[str, str], agent: str):
        if set(value) != {'severity', 'path', 'line', 'evidence', 'message'}:
            raise ValueError('Unexpected finding fields')
        if value['severity'] not in ('low', 'medium', 'high', 'critical'):
            raise ValueError('Invalid severity')
        path, line, evidence = value['path'], value['line'], value['evidence']
        if not isinstance(path, str) or path not in files or type(line) is not int or line < 1:
            raise ValueError('Invalid source location')
        source = files[path].splitlines()
        if line > len(source) or not isinstance(evidence, str) or not evidence or len(evidence) > 500 or evidence not in source[line - 1]:
            raise ValueError('Evidence must match the cited source line')
        if not isinstance(value['message'], str) or not 1 <= len(value['message']) <= 1000:
            raise ValueError('Invalid message')
        return cls(**value, agent=agent)

    def json(self):
        return asdict(self)
