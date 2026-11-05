import hashlib
import json
from concurrent.futures import ThreadPoolExecutor
from .models import Finding
from .repository import validate_files

class Orchestrator:
    def __init__(self, store, provider):
        self.store, self.provider = store, provider

    def analyze(self, files, source='synthetic fixture'):
        validate_files(files)
        identity = json.dumps({'files':files,'source':source,'workflow':'review-v1','provider':type(self.provider).__name__},sort_keys=True)
        task_id = hashlib.sha256(identity.encode()).hexdigest()[:24]
        # Immutable content-addressed task: repeated analysis returns the recorded result.
        try:
            return self.store.get(task_id)
        except ValueError:
            pass
        agents = ['security', 'reliability']
        with ThreadPoolExecutor(max_workers=2) as pool:
            completions = list(pool.map(lambda agent:self.provider.review(agent, files), agents))
        findings, usage = [], []
        for agent, completion in zip(agents, completions):
            if completion.tool != 'submit_findings' or set(completion.arguments) != {'findings'}:
                raise ValueError('Unapproved tool call')
            values = completion.arguments['findings']
            if not isinstance(values, list) or len(values) > 100:
                raise ValueError('Finding budget exceeded')
            if any(type(v) is not int or v < 0 for v in (completion.input_tokens,completion.output_tokens,completion.cost_microusd)):
                raise ValueError('Invalid usage')
            if completion.input_tokens + completion.output_tokens > 100_000:
                raise ValueError('Token budget exceeded')
            findings.extend(Finding.parse(value,files,agent).json() for value in values)
            usage.append(dict(agent=agent,input_tokens=completion.input_tokens,output_tokens=completion.output_tokens,cost_microusd=completion.cost_microusd,estimated=completion.estimated))
        return self.store.create(task_id, dict(source=source,findings=findings,usage=usage,source_digest=hashlib.sha256(json.dumps(files,sort_keys=True).encode()).hexdigest()))

    def approve(self, task_id, reviewer):
        if not reviewer.strip() or len(reviewer)>100:
            raise ValueError('Named human reviewer required')
        self.store.transition(task_id,'analyzed','approved','human.approved',{'reviewer':reviewer})

    def export(self, task_id):
        task = self.store.get(task_id)
        if task['state'] != 'approved':
            raise ValueError('Human approval required before export')
        self.store.event(task_id,'report.exported',{'finding_count':len(task['findings'])})
        self.store.db.commit()
        return json.dumps(task,indent=2)
