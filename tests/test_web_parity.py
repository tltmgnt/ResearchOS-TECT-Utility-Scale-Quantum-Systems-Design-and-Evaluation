"""Keep the browser scheduler aligned with the Python planning engine."""
import copy
import json
from pathlib import Path
import shutil
import subprocess
import unittest
from researchos_systems.model import analyze
from researchos_systems.records import read_json

ROOT = Path(__file__).resolve().parents[1]


@unittest.skipUnless(shutil.which('node'), 'Node is required for web parity verification')
class WebParityTests(unittest.TestCase):
    def test_full_study_result_parity(self):
        base = read_json(ROOT/'examples/synthetic-system.json')
        cases = [base]
        r = copy.deepcopy(base)
        r['workflow'].reverse()
        cases.append(r)
        r = copy.deepcopy(base)
        r['scenarios'][0]['physical_capacity'] = None
        r['declared_quality'] = None
        r['classical_baseline'] = None
        cases.append(r)
        r = copy.deepcopy(base)
        r['workflow'] = [{'id':'a','description':'Fixture','kind':'classical','depends_on':[],'duration_s':0,'evidence_ids':[]}]
        cases.append(r)
        script = "import fs from 'node:fs';import{analyze}from './web/model.mjs';console.log(JSON.stringify(JSON.parse(fs.readFileSync(0,'utf8')).map(analyze)))"
        results = json.loads(subprocess.check_output(['node','--input-type=module','-e',script],input=json.dumps(cases),text=True,cwd=ROOT))
        def compare(actual,expected):
            if isinstance(expected,dict):
                self.assertEqual(actual.keys(),expected.keys())
                for k in expected:
                    compare(actual[k],expected[k])
            elif isinstance(expected,list):
                self.assertEqual(len(actual),len(expected))
                for a,b in zip(actual,expected):
                    compare(a,b)
            elif type(expected) is float:
                self.assertAlmostEqual(actual,expected,places=12)
            else:
                self.assertEqual(actual,expected)
        for i,(r,web) in enumerate(zip(cases,results)):
            with self.subTest(variant=i):
                compare(web,analyze(r))
