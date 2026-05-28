## 1. Workflow Restructuring

- [x] 1.1 Keep the existing Linux Python or web checks in the main CI workflow and add concurrency cancellation for superseded pushes
- [x] 1.2 Move the macOS Swift verification into a dedicated workflow that only runs for Swift-related paths, workflow edits, or manual dispatch
- [x] 1.3 Add a bounded timeout to the Swift workflow so hangs fail fast instead of burning unbounded macOS minutes

## 2. Public Automation Surface

- [x] 2.1 Update the root README badges and verification section to reflect the split workflows and Swift trigger scope
- [x] 2.2 Update the durable roadmap context to describe the new cost-control behavior of public repository automation

## 3. Validation

- [x] 3.1 Validate the workflow YAML shape and the OpenSpec artifacts after the split