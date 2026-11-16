# Systems evaluation roadmap

This independent workspace helps make architecture assumptions and evidence gaps reviewable. It does not claim to construct a utility-scale quantum computer.

| Stage | Deliverable | Acceptance evidence | Status |
| --- | --- | --- | --- |
| Planning foundation | Workflow DAGs, one-QPU schedules, scenario comparisons, capacity checks and evidence bundles | Tests, packaged CLI and synthetic study | Implemented |
| Application specification | Matched problem instance, useful output criterion and complete workflow | Reviewed workload and timing scope | Planned |
| Architecture grounding | Fault-tolerant compiler, error model, decoder, factory and interconnect assumptions | Independent model benchmarks and feasibility review | Not integrated |
| Hardware/baseline acquisition | Calibrated timings, repeatability, uncertainty and raw evidence | Versioned acquisition records and independent review | No hardware integration/data |
| End-to-end utility evaluation | Value, total operating cost, risk and feasibility under matched quality | Application-specific economic/scientific assessment | Not implemented |
| QBIT engagement | Selected topic, exact requirements and submission instructions | Live notice/amendment review and requirements trace | No topic selected |

## Next gate

Choose a real application and architecture, establish a strong classical baseline, ground resource inputs in an independently checked model, and populate requirements/risks with evidence. Extend scheduling to the actual classical/QPU/memory/communication constraints before using it for operational planning. Validate all uncertainty and omitted costs separately.

The synthetic reference, slower-cycle and undersized scenarios demonstrate sensitivity and missing-capacity reporting, not system performance or program compliance. No submission is made by this tool.
