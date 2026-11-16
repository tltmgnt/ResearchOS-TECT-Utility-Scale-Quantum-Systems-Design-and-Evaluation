import copy
import itertools
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from researchos_systems.model import analyze, evaluate
from researchos_systems.records import ValidationError, dumps, read_json, sha, validate
from researchos_systems.workflow import run, verify_bundle, verify_evidence

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT/'examples/synthetic-system.json'


class SystemsTests(unittest.TestCase):
    def setUp(self):
        self.r = read_json(EXAMPLE)

    def test_known_schedule_and_resources(self):
        result = analyze(self.r)
        ref,slow,gap = result['scenario_results']
        self.assertAlmostEqual(ref['estimated_makespan_s'],4.7)
        self.assertAlmostEqual(ref['uncontended_critical_path_s'],3.6)
        self.assertAlmostEqual(slow['estimated_makespan_s'],7.7)
        self.assertEqual(ref['peak_assumed_physical_qubits'],20100)
        self.assertEqual(ref['logical_qubit_cycle_locations'],50000000)
        self.assertAlmostEqual(ref['conditional_failure_union_bound'],.005)
        self.assertEqual(ref['capacity_status'],'within-declared-capacity')
        self.assertEqual(gap['capacity_status'],'over-declared-capacity')
        self.assertIsNone(gap['baseline_comparison']['declared_runtime_ratio'])

    def test_dependency_and_exclusive_qpu_invariants(self):
        for scenario in analyze(self.r)['scenario_results']:
            schedule = {n['node_id']:n for n in scenario['schedule']}
            for node in self.r['workflow']:
                for dependency in node['depends_on']:
                    self.assertGreaterEqual(schedule[node['id']]['start_s'],schedule[dependency]['end_s'])
            quantum = sorted((n for n in schedule.values() if n['kind']=='quantum'),key=lambda n:n['start_s'])
            for left,right in zip(quantum,quantum[1:]):
                self.assertGreaterEqual(right['start_s'],left['end_s'])

    def test_classical_parallelism_and_order_independence(self):
        expected = analyze(self.r)
        for permutation in itertools.permutations(self.r['workflow']):
            r = copy.deepcopy(self.r)
            r['workflow'] = list(permutation)
            self.assertEqual(analyze(r),expected)
        r = copy.deepcopy(self.r)
        r['workflow'] = [{'id':'a','kind':'classical','description':'Fixture','depends_on':[],'duration_s':2,'evidence_ids':[]},
                         {'id':'b','kind':'classical','description':'Fixture','depends_on':[],'duration_s':3,'evidence_ids':[]}]
        result = analyze(r)['scenario_results'][0]
        self.assertEqual(result['estimated_makespan_s'],3)
        self.assertEqual(result['qpu_utilization_fraction'],0)

    def test_zero_duration_and_failure_bound(self):
        r = copy.deepcopy(self.r)
        r['workflow'] = [{'id':'a','kind':'classical','description':'Fixture','depends_on':[],'duration_s':0,'evidence_ids':[]}]
        result = analyze(r)['scenario_results'][0]
        self.assertEqual(result['estimated_makespan_s'],0)
        self.assertIsNone(result['baseline_comparison']['declared_runtime_ratio'])
        self.r['scenarios'][0]['logical_error_per_qubit_cycle'] = 1
        self.assertEqual(analyze(self.r)['scenario_results'][0]['conditional_failure_union_bound'],1)

    def test_no_data_and_comparability_gates(self):
        self.r['classical_baseline'] = None
        self.assertEqual(analyze(self.r)['scenario_results'][0]['baseline_comparison']['status'],'no-data')
        self.r = read_json(EXAMPLE)
        self.r['scenarios'][0]['physical_capacity'] = None
        result = analyze(self.r)['scenario_results'][0]
        self.assertEqual(result['capacity_status'],'physical-capacity-unknown')
        self.assertIsNone(result['baseline_comparison']['declared_runtime_ratio'])
        self.r = read_json(EXAMPLE)
        self.r['declared_quality']['meets_criterion'] = False
        self.assertIsNone(analyze(self.r)['scenario_results'][0]['baseline_comparison']['declared_runtime_ratio'])
        self.assertEqual(analyze(self.r)['qbit_status'],'no-topic-selected')

    def test_invalid_graphs_and_records(self):
        mutations = [lambda r:r.update(schema_version=True),lambda r:r.update(id='../escape'),
                     lambda r:r['workflow'][0].update(depends_on=['unknown']),
                     lambda r:r['workflow'][0].update(depends_on=['postprocess']),
                     lambda r:r['workflow'][0].update(depends_on=['prepare']),
                     lambda r:r['workflow'][1].update(logical_qubits=True),
                     lambda r:r['workflow'][0].update(duration_s=-1),
                     lambda r:r['scenarios'][0].update(cycle_time_us=float('inf')),
                     lambda r:r['scenarios'].append(copy.deepcopy(r['scenarios'][0])),
                     lambda r:r['requirements'][0].update(assessment='supported'),
                     lambda r:r['risks'][0].update(likelihood='certain'),
                     lambda r:r.update(data_kind='experimental')]
        for mutate in mutations:
            r = copy.deepcopy(self.r)
            mutate(r)
            with self.subTest(record=r),self.assertRaises(ValidationError):
                validate(r)

    def test_strict_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp)/'bad.json'
            for data in ('{"x":1,"x":2}','{"x":NaN}'):
                p.write_text(data)
                with self.assertRaises(ValidationError):
                    read_json(p)

    def test_evidence_requirements_and_portability(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            data = b'fixture only; not experimental evidence'
            (root/'raw').write_bytes(data)
            self.r['evidence'] = [{'id':'raw','path':'raw','sha256':sha(data),'description':'Test fixture'}]
            self.r['data_kind'] = 'experimental'
            for node in self.r['workflow']+self.r['scenarios']+[self.r['declared_quality'],self.r['classical_baseline']]:
                node['evidence_ids'] = ['raw']
            self.r['requirements'][0].update(assessment='supported',evidence_ids=['raw'])
            validate(self.r)
            p = root/'record.json'
            p.write_text(dumps(self.r))
            run(p,root/'run')
            (root/'raw').unlink()
            verify_bundle(root/'run')
            (root/'run/evidence/0000.bin').write_bytes(b'changed')
            with self.assertRaises(ValidationError):
                verify_bundle(root/'run')

    def test_evidence_paths_and_checksum_mismatch(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root/'raw').write_bytes(b'actual')
            self.r['evidence'] = [{'id':'raw','path':'raw','sha256':sha(b'wrong'),'description':'Fixture'}]
            with self.assertRaises(ValidationError):
                verify_evidence(validate(self.r),root)
            for path in ('../outside','/etc/passwd','C:\\outside'):
                self.r['evidence'][0]['path'] = path
                with self.assertRaises(ValidationError):
                    validate(self.r)
            (root/'link').symlink_to(root.parent)
            self.r['evidence'][0]['path'] = 'link/outside'
            with self.assertRaises(ValidationError):
                verify_evidence(validate(self.r),root)

    def test_bundle_reproduction_and_no_overwrite(self):
        with tempfile.TemporaryDirectory() as tmp:
            a,b = Path(tmp)/'a',Path(tmp)/'b'
            run(EXAMPLE,a)
            run(EXAMPLE,b)
            self.assertEqual({p.relative_to(a):p.read_bytes() for p in a.rglob('*') if p.is_file()},
                             {p.relative_to(b):p.read_bytes() for p in b.rglob('*') if p.is_file()})
            verify_bundle(a)
            with self.assertRaises(ValidationError):
                run(EXAMPLE,a)
            result = read_json(a/'results.json')
            result['scenario_results'][0]['estimated_makespan_s'] = 999
            (a/'results.json').write_text(dumps(result))
            manifest = read_json(a/'manifest.json')
            manifest['files']['results.json'] = sha((a/'results.json').read_bytes())
            (a/'manifest.json').write_text(dumps(manifest))
            with self.assertRaises(ValidationError):
                verify_bundle(a)

    def test_cli_end_to_end(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = str(Path(tmp)/'run')
            for args in (['validate',str(EXAMPLE)],['run',str(EXAMPLE),'--output',output],['verify',output],['report',output]):
                result = subprocess.run([sys.executable,'-m','researchos_systems',*args],capture_output=True,text=True)
                self.assertEqual(result.returncode,0,result.stderr)
            failed = subprocess.run([sys.executable,'-m','researchos_systems','validate',str(Path(tmp)/'missing')],capture_output=True,text=True)
            self.assertEqual(failed.returncode,1)
            self.assertIn('error:',failed.stderr)


if __name__ == '__main__':
    unittest.main()
