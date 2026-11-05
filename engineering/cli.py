import argparse
import json
import os
from pathlib import Path
from .orchestrator import Orchestrator
from .providers import MockProvider
from .repository import GitHub, fixture
from .sandbox import run
from .store import Store

def main():
    parser = argparse.ArgumentParser(description='Approval-gated, mock-first engineering review')
    parser.add_argument('--db',default='artifacts/tasks.db')
    sub = parser.add_subparsers(dest='action',required=True)
    analyze = sub.add_parser('analyze'); analyze.add_argument('--fixture',default='fixtures/review.json')
    github = sub.add_parser('github'); github.add_argument('repository'); github.add_argument('pr',type=int)
    approve = sub.add_parser('approve'); approve.add_argument('task'); approve.add_argument('--reviewer',required=True)
    report = sub.add_parser('export'); report.add_argument('task')
    sandbox = sub.add_parser('test'); sandbox.add_argument('task'); sandbox.add_argument('repository')
    sub.add_parser('demo')
    args = parser.parse_args()
    Path(args.db).parent.mkdir(parents=True,exist_ok=True)
    store = Store(args.db); engine = Orchestrator(store,MockProvider())
    if args.action in ('analyze','demo'):
        task = engine.analyze(fixture(args.fixture if args.action=='analyze' else 'fixtures/review.json'))
        if args.action == 'demo':
            try:
                if task['state']=='analyzed':
                    engine.export(task['id'])
                    raise AssertionError('Approval gate failed')
            except ValueError:
                print('Approval gate verified: report export denied before human approval.')
            print('Demo explicitly simulates a human approval; production CLI requires approve --reviewer.')
            if task['state']=='analyzed': engine.approve(task['id'],'synthetic-demo-reviewer')
            print(engine.export(task['id']))
        else: print(json.dumps(task,indent=2))
    elif args.action=='github':
        print(json.dumps(engine.analyze(GitHub(os.environ.get('GITHUB_TOKEN')).pull_request(args.repository,args.pr),f'GitHub {args.repository} PR {args.pr}; patch-line coordinates'),indent=2))
    elif args.action=='approve': engine.approve(args.task,args.reviewer)
    elif args.action=='export': print(engine.export(args.task))
    elif args.action=='test':
        result = run(store,args.task,args.repository); print(json.dumps(result,indent=2)); raise SystemExit(result['exit_code'])

if __name__ == '__main__': main()
