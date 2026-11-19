# ЛР3 — независимый documentation and risk review DVC reproducibility workflow

- Issue: [#33](https://github.com/ESKoVV/T26_MLOps/issues/33)
- Review role: documentation and risk reviewer
- Review scope: GitHub-visible state of `ESKoVV/T26_MLOps`, branch `student-04`
- Reviewed base commit: `c0341095f8df196dad6e693eed6e029d97bd4648`
- Review type: docs-only; no DVC commands or local data restoration were executed

## 1. Executive summary

The reviewed `student-04` snapshot contains a useful data card, a small synthetic flight sample, a DVC evidence-card template, and ignore rules for DVC cache and MLflow artifacts. However, the inspected tree does not contain DVC configuration or tracked DVC metadata. Therefore, the repository snapshot does not yet provide Git-verifiable evidence of dataset versioning or of restoring versions v1/v2.

This review assesses documentation and repository-visible evidence only. It does not claim that DVC is absent from every developer's local environment, that a remote is empty, or that any restore operation succeeded or failed.

## 2. Findings

### R1 — HIGH: DVC workflow is documented as an evidence target, but DVC metadata is absent from the reviewed branch

**Observation.** The GitHub tree at the reviewed commit contains no `.dvc/` directory, no `.dvc` pointer files, and no DVC configuration. The evidence-card template asks the student to record DVC hashes and demonstrate version switching/restoration, but those artifacts are not present in this snapshot.

**Risk.** A reviewer cannot map a Git commit to a specific DVC-tracked dataset version or independently verify that the documented workflow is reproducible from the repository.

**Recommendation.** Add the intended DVC setup in a dedicated change: commit the DVC project configuration (excluding credentials), the relevant `.dvc` pointer file(s) or DVC-tracked directory metadata, and a documented remote configuration strategy. Record the dataset version's DVC object/hash and the corresponding Git commit in the evidence card. Do not commit DVC cache contents or secrets.

### R2 — HIGH: v1/v2 restoration is a planned evidence step, not a demonstrated result in the reviewed snapshot

**Observation.** `docs/evidence/lr3-evidence-card.md` provides fields for switching Git revisions and running `dvc pull` / `dvc checkout`, with hashes and validation details. The reviewed branch does not include a completed individual evidence record showing the exact commits, DVC object identifiers, SHA-256 values, or validator output for both versions.

**Risk.** The existence of command examples or an empty evidence template can be mistaken for proof that both versions can be restored. A remote may be unavailable, incomplete, or configured differently on another machine.

**Recommendation.** For each version, record: Git commit SHA; DVC pointer/object hash; remote identity (without credentials); exact command sequence; resulting file SHA-256; data-contract/validator result; and the observed outcome. Mark each step as locally executed, independently reproduced, or not tested. Only claim successful restoration after the commands have actually completed in a controlled environment.

### R3 — MEDIUM: the distinction between Git revision, DVC pointer, cache, and remote needs an explicit operational explanation

**Observation.** The evidence template references Git switching and DVC restoration commands, while `.gitignore` excludes `.dvc/cache/`. The inspected documentation does not provide a complete, self-contained explanation of which artifacts are committed to Git and which data objects must be fetched from a DVC remote.

**Risk.** A user may switch Git revisions and assume the dataset has changed, or expect `dvc checkout` alone to retrieve objects that are not present in the local cache.

**Recommendation.** Add a short command-oriented section explaining: Git stores the DVC metadata/pointer and project configuration; the DVC cache stores local object content; the remote stores shared objects; `dvc pull` fetches the required data from the configured remote and updates the workspace; `dvc checkout` materializes data from the local cache for the currently checked-out metadata. State prerequisites and expected outputs, and avoid presenting the commands as interchangeable.

### R4 — MEDIUM: integrity evidence should distinguish file checksum, DVC object identity, and data-contract validation

**Observation.** The evidence-card template requests SHA-256 and a validator/contract version. The data card describes a 24-row synthetic sample at `data/flights_sample.csv`, contract at `data/contract.json`, chronological 60/20/20 split, and target `ArrDelay >= 15`. The template does not itself establish that a recorded checksum was computed from the restored file or that the contract validator was run against each version.

**Risk.** A DVC hash, a SHA-256 checksum, and a schema/semantic validation result can be conflated, although they answer different questions: object/version identity, byte-level integrity, and data correctness.

**Recommendation.** Record these as separate fields. Compute SHA-256 after restoration; run the documented contract validator against the restored dataset; record the validator command/version and result for each version. Include row count and relevant contract expectations where they help detect accidental changes.

### R5 — MEDIUM: ignore rules are useful but do not by themselves prove that DVC data is safely and reproducibly managed

**Observation.** `.gitignore` excludes `.dvc/cache/`, MLflow tracking/artifact directories, local database files, and `.env`. This is appropriate for avoiding large local artifacts and secrets in Git, but it does not document how a teammate obtains the required DVC objects or how remote credentials are supplied.

**Risk.** A clean Git checkout may be insufficient to reproduce the dataset state, while a developer may try to solve the problem by committing cache contents or credentials.

**Recommendation.** Document a safe remote bootstrap procedure using environment variables or the supported credential helper; provide a non-secret remote example or setup instructions; explain how to verify remote access; and ensure that a fresh clone can retrieve the expected data without adding cache or secrets to Git.

## 3. Positive aspects

- `docs/evidence/lr3-evidence-card.md` already prompts for individual contribution, peer review, Git/DVC version identifiers, SHA-256, contract/validator details, and a negative scenario.
- `docs/data-card.md` identifies the sample as synthetic and small, documents the target definition and chronological split, and warns against using the target as a feature.
- `.gitignore` excludes local DVC cache and common MLflow artifacts and secret-bearing environment files.
- The README points to the optional data/tracking/orchestration dependency group needed for the broader lab workflow.
- CONTRIBUTING establishes the Issue → branch → PR → review workflow, supporting traceability for the corrective work.

## 4. Evidence boundary and limitations

**Verified from the GitHub-visible `student-04` snapshot:**
- `data/flights_sample.csv` exists and its header is `FlightDate,DepHour,IsWeekend,ArrDelay`.
- The data card describes a 24-row synthetic sample, `data/contract.json`, chronological 60/20/20 split, and target `ArrDelay >= 15`.
- The DVC evidence-card template contains fields for version restoration, DVC hash, SHA-256, contract/validator, and a failure scenario.
- `.gitignore` excludes `.dvc/cache/`, `mlruns/`, `mlartifacts/`, `mlflow.db`, and `.env`.
- The reviewed tree at commit `c0341095f8df196dad6e693eed6e029d97bd4648` contains no `.dvc/` directory or `.dvc` pointer files.

**Not verified by this review:**
- DVC installation or configuration on any contributor's workstation.
- Existence, contents, availability, or permissions of an external DVC remote.
- Successful `dvc add`, `dvc push`, `dvc pull`, `dvc checkout`, or v1/v2 restoration.
- SHA-256 values of restored historical versions or successful contract-validator runs.
- Completion or ownership of another contributor's evidence card, CI run, or local experiment.

No local tests, DVC commands, or data-restoration operations were run as part of this documentation review.

## 5. Suggested verification checklist for the implementation PR

1. [ ] DVC project configuration and pointer metadata are committed; no cache or credentials are committed.
2. [ ] Remote setup is documented without exposing secrets.
3. [ ] A fresh checkout can retrieve the required data using the documented steps.
4. [ ] v1 and v2 are each restored from their recorded Git revisions and DVC metadata.
5. [ ] SHA-256 is computed on each restored file and recorded separately from the DVC object hash.
6. [ ] The data contract validator is run against each restored version and its result is recorded.
7. [ ] A negative scenario (for example, unavailable remote/object or invalid contract) is documented with the actual observed result.
8. [ ] The evidence card clearly distinguishes personally executed steps from peer-reviewed or not-yet-tested steps.

## 6. Review conclusion

The documentation provides a useful checklist and data context, but the reviewed branch does not yet contain the DVC metadata needed to substantiate the versioning and restoration workflow. Treat v1/v2 reproducibility as **not demonstrated in this snapshot** until the implementation artifacts and locally executed evidence are added. This review is not an approval of DVC functionality or a substitute for the required peer review and CI checks.
