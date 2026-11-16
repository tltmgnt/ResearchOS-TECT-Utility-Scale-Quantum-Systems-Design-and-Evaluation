# Single-QPU workflow planning v1

## Scope

This is a deterministic planning model driven by declared task and architecture values. It neither runs an application nor derives a fault-tolerant architecture. Scenario parameters require independent justification. All example values are fictional.

## Durations and resources

Classical task duration is the supplied `duration_s`. For each quantum task and architecture:

- Cycles per shot = logical depth × cycles per layer.
- Duration = setup seconds + shots × cycles per shot × cycle time in microseconds × 10⁻⁶.
- Assumed allocated physical qubits = task logical qubits × physical qubits per logical + factory physical qubits.
- Logical-qubit-cycle locations = logical qubits × cycles per shot × shots.

Shots are sequential. Setup is once per task and reserves the QPU. QPU reservation includes setup; logical-error locations exclude setup. Peak logical and physical allocation is the maximum across quantum tasks, since only one runs at a time. This ignores persistent quantum state between tasks, memory lifetimes, architecture switching, communications, retries and external queuing. Factory allocation is a supplied qubit count, not a factory throughput/scheduling model. Classical cores, memory and communication are unlimited/zero-overhead unless included explicitly as task durations.

The conditional failure union bound is `min(1, sum(locations) × logical_error_per_qubit_cycle)`. It is a bound only if the declared value validly bounds every included per-location event. It requires no independence but excludes unmodeled events, setup, idle memory and classical failures. No relationship to physical error, code distance, decoding or application correctness is derived.

## Scheduling

A node becomes eligible when every predecessor has been scheduled. Its dependency-ready time is the maximum predecessor finish time, or zero for a root. A classical node can start then; a quantum node starts at the maximum of that time and QPU availability. Among eligible nodes, choose the earliest computed start, breaking ties by lexicographic node ID. Update QPU availability after each quantum node. This is deterministic list scheduling, not an optimal scheduler.

Classical work may overlap classical and quantum work. Dependencies always constrain starts; QPU reservations never overlap. Input array order does not break ties. Cycles, missing/self dependencies and duplicate IDs are rejected. Limits are 1–1,000 nodes and 1–50 scenarios.

Estimated makespan is the maximum scheduled finish time. Uncontended critical path uses the same durations and dependency graph with no QPU contention. It is a dependency-based lower bound, not an alternative executable schedule. QPU utilization is total quantum reservation time / makespan; an all-zero-duration classical workflow yields zero utilization and no runtime ratio.

## Capacity and comparison

Logical capacity is required. Physical capacity may be null; this yields `physical-capacity-unknown` unless logical capacity is already exceeded. Arithmetic capacity excess is `over-declared-capacity`. Hypothetical schedules are still emitted to diagnose such gaps; they are not executable claims.

A declared-runtime ratio is emitted only when baseline and quality declarations exist, their comparison/quality flags are true, declared logical and physical capacities are not exceeded, and makespan is positive. The ratio is declared classical total seconds / estimated workflow makespan. It is not measured speedup, a utility test, or independent validation of comparability. The same workload count, problem instance, quality criterion and timing boundary must be established outside the scheduler.

## Traceability

Requirement assessments are owner labels: `unassessed`, `gap`, or `supported`. Supported labels require at least one evidence reference, but the software does not interpret evidence content. Qualitative risk likelihood/impact labels have no inferred probability or numerical risk score. Topic references do not establish eligibility or submit anything.

## Reproduction

Run bundles capture exact input/evidence bytes, derived artifacts, SHA-256 digests and Python version. Verification recomputes JSON results, report and CSV in the current runner. Floating-point/version differences may reject old bundles; preserve the runner revision and runtime for long-lived studies. Bundles are ordinary writable files, not signed or append-only audit records. Replacing all records and hashes can forge a self-consistent bundle.
