"""Deterministic one-QPU list scheduling and declared architecture accounting."""
import math
from .records import dumps, require, topological_order, validate

LIMITATIONS = (
    "Declared-assumption planning only. One exclusive QPU and unlimited classical "
    "parallelism are assumed. No circuit execution, fault-tolerant compilation, "
    "noise simulation, decoder/factory scheduling, queueing, economic utility "
    "validation or hardware integration is implemented. Capacity checks and runtime "
    "ratios do not establish physical feasibility, quantum advantage or DARPA compliance."
)


def evaluate(nodes, architecture):
    a = architecture
    durations, physical, locations = {}, {}, {}
    for n in nodes:
        if n["kind"] == "classical":
            durations[n["id"]] = n["duration_s"]
        else:
            cycles = n["logical_depth"] * a["cycles_per_layer"]
            durations[n["id"]] = n["setup_s"] + n["shots"] * cycles * a["cycle_time_us"] * 1e-6
            physical[n["id"]] = n["logical_qubits"] * a["physical_qubits_per_logical"] + a["factory_physical_qubits"]
            locations[n["id"]] = n["logical_qubits"] * cycles * n["shots"]
            require(math.isfinite(durations[n["id"]]) and durations[n["id"]] > 0, "quantum duration overflow/underflow")
    remaining = {n["id"]: n for n in nodes}
    finish, schedule, qpu_free = {}, [], 0.0
    while remaining:
        ready = []
        for key, node in remaining.items():
            if all(dep in finish for dep in node["depends_on"]):
                earliest = max((finish[d] for d in node["depends_on"]), default=0.0)
                start = max(earliest, qpu_free) if node["kind"] == "quantum" else earliest
                ready.append((start, key, node))
        require(bool(ready), "workflow cycle")
        start, key, node = min(ready, key=lambda x: (x[0], x[1]))
        end = start + durations[key]
        require(math.isfinite(end), "schedule duration overflow")
        finish[key] = end
        schedule.append({"node_id": key, "kind": node["kind"], "start_s": start, "end_s": end, "duration_s": durations[key]})
        if node["kind"] == "quantum":
            qpu_free = end
        del remaining[key]
    lookup = {n["id"]: n for n in nodes}
    path_finish = {}
    for key in topological_order(nodes):
        path_finish[key] = max((path_finish[d] for d in lookup[key]["depends_on"]), default=0.0) + durations[key]
    makespan = max(finish.values())
    peak = max(physical.values(), default=0)
    max_logical = max((n["logical_qubits"] for n in nodes if n["kind"] == "quantum"), default=0)
    physical_known = a.get("physical_capacity") is not None
    logical_met = max_logical <= a["logical_capacity"]
    physical_met = peak <= a["physical_capacity"] if physical_known else None
    capacity = "over-declared-capacity" if not logical_met or physical_met is False else ("within-declared-capacity" if physical_known else "physical-capacity-unknown")
    active = sum(durations[n["id"]] for n in nodes if n["kind"] == "quantum")
    result = {"scenario_id": a["id"], "architecture": a["architecture"], "schedule": schedule,
              "estimated_makespan_s": makespan, "uncontended_critical_path_s": max(path_finish.values()),
              "qpu_reserved_s": active, "qpu_utilization_fraction": active/makespan if makespan else 0,
              "peak_assumed_physical_qubits": peak, "peak_logical_qubits": max_logical,
              "capacity_status": capacity, "logical_capacity_met": logical_met, "physical_capacity_met": physical_met,
              "logical_qubit_cycle_locations": sum(locations.values()),
              "conditional_failure_union_bound": min(1.0, sum(locations.values()) * a["logical_error_per_qubit_cycle"])}
    dumps(result)
    return result


def analyze(record):
    r = validate(record)
    scenarios = []
    for a in r["scenarios"]:
        result = evaluate(r["workflow"], a)
        ratio, status = None, "no-data"
        baseline, quality = r.get("classical_baseline"), r.get("declared_quality")
        if baseline is not None and quality is not None:
            status = "not-comparable"
            if (baseline["same_workload_and_timing_scope"] and baseline["meets_quality_criterion"]
                    and quality["meets_criterion"] and result["capacity_status"] == "within-declared-capacity"
                    and result["estimated_makespan_s"] > 0):
                ratio = baseline["runtime_s"] / result["estimated_makespan_s"]
                require(math.isfinite(ratio), "runtime ratio overflow")
                status = "declared-comparable"
        result["baseline_comparison"] = {"status": status, "declared_runtime_ratio": ratio,
                                         "interpretation": "Declared classical time / estimated workflow time; not measured speedup"}
        scenarios.append(result)
    return {"analysis": "single-qpu-workflow-planning-v1", "runner_version": "0.1.0",
            "input_data_kind": r["data_kind"], "qbit_status": "topic-reference-recorded" if r.get("qbit") else "no-topic-selected",
            "scenario_results": scenarios,
            "requirements": [{"id": req["id"], "owner_assessment": req["assessment"], "evidence_ids": req["evidence_ids"]} for req in r["requirements"]],
            "risks": r["risks"], "limitations": LIMITATIONS}
