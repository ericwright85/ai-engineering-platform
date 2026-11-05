"""Verify the approved sandbox contract against synthetic test code only."""
import tempfile
from pathlib import Path
from .orchestrator import Orchestrator
from .providers import MockProvider
from .repository import fixture
from .sandbox import run
from .store import Store

def main():
    with tempfile.TemporaryDirectory() as temporary:
        store = Store(Path(temporary)/'sandbox.db')
        try:
            engine = Orchestrator(store,MockProvider())
            task = engine.analyze(fixture('fixtures/review.json'))
            engine.approve(task['id'],'synthetic-sandbox-demo')
            result = run(store,task['id'],'fixtures/sandbox')
            print(result['output'])
            if result['exit_code'] != 0 or 'Ran 2 tests' not in result['output']:
                raise RuntimeError('Sandbox fixture failed: '+str(result))
        finally:
            store.db.close()

if __name__ == '__main__': main()
