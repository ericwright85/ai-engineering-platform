import json
import tempfile
import unittest
from pathlib import Path
from engineering.orchestrator import Orchestrator
from engineering.providers import Completion, MockProvider
from engineering.repository import GitHub, fixture, validate_files
from engineering.sandbox import command, run
from engineering.store import Store

class WorkflowTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.store = Store(Path(self.temp.name)/'test.db')
        self.addCleanup(self.store.db.close)
        self.engine = Orchestrator(self.store,MockProvider())
        self.files = fixture('fixtures/review.json')

    def test_agents_evidence_usage_and_approval(self):
        task = self.engine.analyze(self.files)
        self.assertEqual({'security','reliability'}, {f['agent'] for f in task['findings']})
        self.assertEqual(2,len(task['findings']))
        self.assertEqual(0,sum(u['cost_microusd'] for u in task['usage']))
        with self.assertRaises(ValueError): self.engine.export(task['id'])
        with self.assertRaises(ValueError): run(self.store,task['id'],'fixtures/sandbox')
        self.engine.approve(task['id'],'Human Reviewer')
        self.assertEqual('approved',json.loads(self.engine.export(task['id']))['state'])
        self.assertIn('human.approved',[e['kind'] for e in self.store.events(task['id'])])

    def test_replay_and_persistence(self):
        task = self.engine.analyze(self.files)
        self.assertEqual(task,self.engine.analyze(self.files))
        other = Store(Path(self.temp.name)/'test.db')
        self.addCleanup(other.db.close)
        self.assertEqual(task,other.get(task['id']))
        self.assertEqual(1,len(self.store.events(task['id'])))

    def test_prompt_injection_cannot_select_tool(self):
        class Hostile:
            def review(self,*args): return Completion('execute_shell',{'command':'echo unsafe'},1,1,0)
        with self.assertRaisesRegex(ValueError,'Unapproved tool'):
            Orchestrator(self.store,Hostile()).analyze(self.files)

    def test_fabricated_evidence_is_rejected(self):
        class Hostile:
            def review(self,*args): return Completion('submit_findings',{'findings':[dict(severity='high',path='example.py',line=1,evidence='fabricated',message='bad')]},1,1,0)
        with self.assertRaisesRegex(ValueError,'Evidence'):
            Orchestrator(self.store,Hostile()).analyze(self.files)

    def test_path_traversal_and_budget(self):
        for value in ({'../secret':'x'},{'/secret':'x'},{'x':'a'*200001}):
            with self.assertRaises(ValueError): validate_files(value)

    def test_approval_transition_not_replayed(self):
        task = self.engine.analyze(self.files)
        self.engine.approve(task['id'],'Human')
        with self.assertRaises(ValueError): self.engine.approve(task['id'],'Other')

    def test_container_policy(self):
        argv = command('fixtures/sandbox')
        for flag in ('--network=none','--read-only','--cap-drop=ALL','--user=65534:65534','--pull=never'):
            self.assertIn(flag,argv)
        self.assertNotIn('/var/run/docker.sock',' '.join(argv))

    def test_github_adapter_uses_patch_line_evidence(self):
        class FakeGitHub(GitHub):
            def _get(self,path):
                self.path=path
                return [dict(filename='demo.py',patch='+subprocess.run(cmd, shell=True)')]
        github = FakeGitHub()
        files = github.pull_request('fictional/demo',12)
        task = self.engine.analyze(files,'patch coordinates')
        self.assertEqual(1,task['findings'][0]['line'])
        self.assertIn('/pulls/12/files',github.path)

    def test_github_rejects_truncated_or_binary_patch(self):
        class Binary(GitHub):
            def _get(self,path): return [dict(filename='blob')]
        with self.assertRaises(ValueError): Binary().pull_request('fiction/demo',1)
