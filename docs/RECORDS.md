# Study record contract v1

The executable contract is `researchos_systems/records.py`. Unknown metadata is retained. Duplicate JSON keys, NaN and Infinity are rejected. Numeric fields cannot be booleans. IDs use 1–80 lowercase letters/digits/underscores/hyphens, starting alphanumeric.

| Field | Content |
| --- | --- |
| `schema_version` | Integer 1 |
| `id` | Unique study identifier |
| `title`, `owner`, `hypothesis`, `workload_reference` | Nonempty strings |
| `data_kind` | synthetic, simulation, or experimental; describes inputs, not execution by this tool |
| `qbit` | Null when unselected; otherwise topic_id, source_url and submission_instructions_reference |
| `workflow` | 1–1,000 task objects |
| `scenarios` | 1–50 architecture-assumption objects |
| `declared_quality` | Null or metric/criterion/reference, boolean meets_criterion and evidence_ids |
| `classical_baseline` | Null or timing/quality/comparability declaration |
| `requirements` | Array of requirement traceability objects, possibly empty |
| `risks` | Array of qualitative risk objects, possibly empty |
| `evidence` | Evidence declarations, possibly empty for nonexperimental inputs |

## Workflow nodes

Every node has unique `id`, nonempty `description`, `kind` (classical/quantum), a `depends_on` array of existing node IDs, and `evidence_ids`. Dependencies must be unique, acyclic and exclude self-links.

Classical nodes have nonnegative finite `duration_s`. Quantum nodes have positive integer `logical_qubits`, `logical_depth`, `shots`, plus nonnegative finite `setup_s`. Quantum resource integers are limited to 10¹². Node descriptions/reference metadata should explain whether durations are measured, simulated or assumed and provide their uncertainty and timing scope.

## Architecture scenarios

Every scenario has unique `id`, nonempty `architecture`, `assumption_reference` and `evidence_ids`.

| Field | Contract |
| --- | --- |
| logical_capacity | Positive integer available logical qubits |
| physical_capacity | Null or positive integer available physical qubits |
| physical_qubits_per_logical | Positive integer assumed overhead |
| factory_physical_qubits | Nonnegative integer assumed additional allocation |
| cycles_per_layer | Positive integer |
| cycle_time_us | Positive finite microseconds |
| logical_error_per_qubit_cycle | Finite probability in [0,1], conditionally assumed per-location bound |

All resource integer inputs are limited to 10¹². Derived nonfinite schedule results and zero/underflowed quantum durations are rejected. Scenario capacity is checked, not assumed to fit the workflow.

## Baseline and quality

`classical_baseline` has positive finite `runtime_s`, nonempty `method` and `reference`, boolean `same_workload_and_timing_scope`, boolean `meets_quality_criterion`, and `evidence_ids`. `declared_quality` describes the workflow's application criterion with a boolean owner assessment. Neither is computed or experimentally checked by this tool. Record uncertainty, hardware/software revision and acquisition conditions in metadata or evidence. Do not mix synthetic and experimental input values under an experimental label.

## Requirements and risks

Each requirement has unique `id`, nonempty `text`, `source_reference`, `rationale`, `assessment` (unassessed/gap/supported), and `evidence_ids`. Supported assessments require references. Distinguish owner requirements from actual QBIT requirements and cite the exact applicable section/amendment.

Each risk has unique `id`, nonempty `description` and `mitigation`, `likelihood` and `impact` (low/medium/high), and `evidence_ids`. Assessments remain qualitative owner judgments.

## Evidence

Each declaration has unique `id`, unique relative `path`, lowercase 64-character `sha256` and nonempty `description`. Use `researchos-systems hash <file>`. Paths must remain inside the record directory after symlink resolution; traversal, absolute and drive paths are rejected. The runner captures the verified bytes and generates evidence filenames/mappings in its bundle.

Experimental studies require evidence references on each workflow node and scenario, and on supplied quality/baseline declarations. This is a traceability rule, not proof of measurement authenticity. Source protocols, calibration, uncertainty, timing scope and independent review remain essential scientific work.
