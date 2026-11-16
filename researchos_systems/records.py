"""Systems-study record contract and strict JSON handling."""
import hashlib
import json
import math
import re
from pathlib import Path


class ValidationError(ValueError):
    pass


def require(ok, message):
    if not ok:
        raise ValidationError(message)


def dumps(value):
    return json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + "\n"


def parse_json(data):
    def constant(value):
        raise ValidationError(f"non-finite JSON constant: {value}")
    def unique(pairs):
        result = {}
        for k, v in pairs:
            require(k not in result, f"duplicate JSON key: {k}")
            result[k] = v
        return result
    return json.loads(data, parse_constant=constant, object_pairs_hook=unique)


def read_json(path):
    return parse_json(Path(path).read_text(encoding="utf-8"))


def sha(data):
    return hashlib.sha256(data).hexdigest()


def text(v, name):
    require(isinstance(v, str) and bool(v.strip()), f"{name} must be a nonempty string")


def integer(v, name, minimum=0, maximum=10**12):
    require(type(v) is int and minimum <= v <= maximum, f"{name} must be an integer in [{minimum}, {maximum}]")


def number(v, name, positive=False):
    require(type(v) in (int, float), f"{name} must be numeric")
    try:
        finite = math.isfinite(v)
    except OverflowError:
        finite = False
    require(finite and (v > 0 if positive else v >= 0), f"{name} must be finite and {'positive' if positive else 'nonnegative'}")


def safe_path(value):
    text(value, "evidence path")
    require(not Path(value).is_absolute() and "\\" not in value and not re.match(r"^[A-Za-z]:", value)
            and not any(p in (".", "..") for p in value.split("/")), "evidence path must be relative without traversal")
    return Path(value)


def evidence_bytes(root, path):
    root = Path(root).resolve()
    dest = (root / safe_path(path)).resolve()
    require(dest.is_relative_to(root), "evidence resolves outside record directory")
    return dest.read_bytes()


def identifier(value, name):
    require(isinstance(value, str) and bool(re.fullmatch(r"[a-z0-9][a-z0-9_-]{0,79}", value)), f"invalid {name}")


def topological_order(nodes):
    remaining = {n["id"]: set(n["depends_on"]) for n in nodes}
    ordered = []
    while remaining:
        ready = sorted(k for k, deps in remaining.items() if not deps)
        require(bool(ready), "workflow contains a dependency cycle")
        ordered.extend(ready)
        for key in ready:
            del remaining[key]
        for deps in remaining.values():
            deps.difference_update(ready)
    return ordered


def validate(r):
    require(isinstance(r, dict), "study must be an object")
    require(type(r.get("schema_version")) is int and r["schema_version"] == 1, "schema_version must be integer 1")
    identifier(r.get("id"), "study id")
    for k in ("title", "owner", "hypothesis", "workload_reference"):
        text(r.get(k), k)
    require(r.get("data_kind") in ("synthetic", "simulation", "experimental"), "invalid data_kind")
    evidence = r.get("evidence")
    require(isinstance(evidence, list), "evidence must be an array")
    refs, paths = set(), set()
    for e in evidence:
        require(isinstance(e, dict), "evidence must contain objects")
        identifier(e.get("id"), "evidence id")
        text(e.get("description"), "evidence description")
        safe_path(e.get("path"))
        require(e["id"] not in refs and e["path"] not in paths, "duplicate evidence id/path")
        refs.add(e["id"])
        paths.add(e["path"])
        require(isinstance(e.get("sha256"), str) and bool(re.fullmatch(r"[a-f0-9]{64}", e["sha256"])), "invalid evidence sha256")
    def links(item, required=False):
        value = item.get("evidence_ids")
        require(isinstance(value, list) and all(isinstance(x, str) and x in refs for x in value), "invalid evidence reference")
        require(not required or bool(value), "experimental inputs or supported assessments require evidence references")
    require(r["data_kind"] != "experimental" or bool(evidence), "experimental studies require evidence")
    topic = r.get("qbit")
    if topic is not None:
        require(isinstance(topic, dict), "qbit must be an object or null")
        for k in ("topic_id", "source_url", "submission_instructions_reference"):
            text(topic.get(k), f"qbit.{k}")
    nodes = r.get("workflow")
    require(isinstance(nodes, list) and 1 <= len(nodes) <= 1000, "workflow must contain 1–1000 nodes")
    ids = set()
    for node in nodes:
        require(isinstance(node, dict), "workflow node must be an object")
        identifier(node.get("id"), "node id")
        require(node["id"] not in ids, "duplicate node id")
        ids.add(node["id"])
        text(node.get("description"), "node description")
        require(node.get("kind") in ("classical", "quantum"), "node kind must be classical or quantum")
        deps = node.get("depends_on")
        require(isinstance(deps, list) and all(isinstance(x, str) for x in deps) and len(deps) == len(set(deps)), "invalid/duplicate dependencies")
        links(node, r["data_kind"] == "experimental")
        if node["kind"] == "classical":
            number(node.get("duration_s"), "duration_s")
        else:
            for k in ("logical_qubits", "logical_depth", "shots"):
                integer(node.get(k), k, 1)
            number(node.get("setup_s"), "setup_s")
    for node in nodes:
        require(node["id"] not in node["depends_on"] and all(x in ids for x in node["depends_on"]), "unknown/self dependency")
    topological_order(nodes)
    scenarios = r.get("scenarios")
    require(isinstance(scenarios, list) and 1 <= len(scenarios) <= 50, "provide 1–50 architecture scenarios")
    seen = set()
    for a in scenarios:
        require(isinstance(a, dict), "scenario must be an object")
        identifier(a.get("id"), "scenario id")
        require(a["id"] not in seen, "duplicate scenario id")
        seen.add(a["id"])
        text(a.get("architecture"), "architecture")
        text(a.get("assumption_reference"), "assumption_reference")
        for k in ("logical_capacity", "physical_qubits_per_logical", "cycles_per_layer"):
            integer(a.get(k), k, 1)
        integer(a.get("factory_physical_qubits"), "factory_physical_qubits")
        if a.get("physical_capacity") is not None:
            integer(a["physical_capacity"], "physical_capacity", 1)
        number(a.get("cycle_time_us"), "cycle_time_us", True)
        number(a.get("logical_error_per_qubit_cycle"), "logical_error_per_qubit_cycle")
        require(a["logical_error_per_qubit_cycle"] <= 1, "logical error must be <= 1")
        links(a, r["data_kind"] == "experimental")
    quality = r.get("declared_quality")
    if quality is not None:
        require(isinstance(quality, dict), "declared_quality must be an object or null")
        for k in ("metric", "criterion", "reference"):
            text(quality.get(k), k)
        require(type(quality.get("meets_criterion")) is bool, "quality assessment must be boolean")
        links(quality, r["data_kind"] == "experimental")
    baseline = r.get("classical_baseline")
    if baseline is not None:
        require(isinstance(baseline, dict), "classical_baseline must be an object or null")
        number(baseline.get("runtime_s"), "baseline runtime", True)
        for k in ("method", "reference"):
            text(baseline.get(k), k)
        for k in ("same_workload_and_timing_scope", "meets_quality_criterion"):
            require(type(baseline.get(k)) is bool, f"{k} must be boolean")
        links(baseline, r["data_kind"] == "experimental")
    requirements = r.get("requirements")
    require(isinstance(requirements, list), "requirements must be an array")
    seen = set()
    for req in requirements:
        require(isinstance(req, dict), "requirement must be an object")
        identifier(req.get("id"), "requirement id")
        require(req["id"] not in seen, "duplicate requirement id")
        seen.add(req["id"])
        for k in ("text", "source_reference", "rationale"):
            text(req.get(k), k)
        require(req.get("assessment") in ("unassessed", "gap", "supported"), "invalid requirement assessment")
        links(req, req["assessment"] == "supported")
    risks = r.get("risks")
    require(isinstance(risks, list), "risks must be an array")
    seen = set()
    for risk in risks:
        require(isinstance(risk, dict), "risk must be an object")
        identifier(risk.get("id"), "risk id")
        require(risk["id"] not in seen, "duplicate risk id")
        seen.add(risk["id"])
        for k in ("description", "mitigation"):
            text(risk.get(k), k)
        for k in ("likelihood", "impact"):
            require(risk.get(k) in ("low", "medium", "high"), f"invalid risk {k}")
        links(risk)
    return r
