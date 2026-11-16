import assert from 'node:assert/strict';
import fs from 'node:fs';
import{analyze,validate,scheduleCsv}from'../model.mjs';
const r=JSON.parse(fs.readFileSync(new URL('../demo.json',import.meta.url),'utf8')),result=analyze(r),[ref,slow,gap]=result.scenario_results;
assert.ok(Math.abs(ref.estimated_makespan_s-4.7)<1e-12);assert.ok(Math.abs(ref.uncontended_critical_path_s-3.6)<1e-12);assert.ok(Math.abs(slow.estimated_makespan_s-7.7)<1e-12);assert.equal(ref.peak_assumed_physical_qubits,20100);assert.equal(gap.capacity_status,'over-declared-capacity');assert.equal(gap.baseline_comparison.declared_runtime_ratio,null);
for(let scenario of result.scenario_results){let rows=Object.fromEntries(scenario.schedule.map(n=>[n.node_id,n]));for(let n of r.workflow)for(let dependency of n.depends_on)assert.ok(rows[n.id].start_s>=rows[dependency].end_s);let quantum=scenario.schedule.filter(n=>n.kind==='quantum').sort((a,b)=>a.start_s-b.start_s);for(let i=1;i<quantum.length;i++)assert.ok(quantum[i].start_s>=quantum[i-1].end_s)}
let reordered=structuredClone(r);reordered.workflow.reverse();assert.deepEqual(analyze(reordered),result);
for(let mutate of [r=>r.id='../escape',r=>r.workflow[0].depends_on=['postprocess'],r=>r.workflow[0].depends_on=['missing'],r=>r.workflow[1].logical_qubits=true,r=>r.scenarios[0].cycle_time_us=Infinity,r=>r.requirements[0].assessment='supported',r=>r.data_kind='experimental']){let bad=structuredClone(r);mutate(bad);assert.throws(()=>validate(bad))}
let missing=structuredClone(r);missing.scenarios[0].physical_capacity=null;assert.equal(analyze(missing).scenario_results[0].capacity_status,'physical-capacity-unknown');assert.equal(analyze(missing).scenario_results[0].baseline_comparison.declared_runtime_ratio,null);missing.classical_baseline=null;assert.equal(analyze(missing).scenario_results[0].baseline_comparison.status,'no-data');
let noQuality=structuredClone(r);noQuality.declared_quality.meets_criterion=false;assert.equal(analyze(noQuality).scenario_results[0].baseline_comparison.declared_runtime_ratio,null);
let overflow=structuredClone(r);overflow.workflow[1].logical_depth=1e12;assert.throws(()=>analyze(overflow),/precision/);
assert.ok(scheduleCsv(result).includes('"reference","quantum-a","quantum"'));assert.equal(result.qbit_status,'no-topic-selected');
console.log('Web scheduler, QPU/dependency invariants, scenario, capacity, validation, missing-data and CSV checks passed.');
