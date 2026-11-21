---
trigger: model_decision
description: "Apply whenever encountering an actionable, reproducible bug, defect, or missing fix in an upstream dependency, library, or upstream repository."
---

# Submit Pull Requests for Actionable Upstream Issues

When debugging or development uncovers a reproducible, actionable defect in an upstream repository or open-source dependency:

1. **Verify and Deduplicate Upstream**: Check the upstream repository's open issues and pull requests first to confirm the defect reproduces on the latest upstream branch and lacks an active fix pull request.
2. **Prepare a Minimal Tested Patch**: Clone or fork the upstream repository cleanly, implement a focused fix following upstream coding conventions and `CONTRIBUTING.md`, and run regression tests locally.
3. **Submit and Verify**: Confirm the target third-party repository and diff summary with the user prior to pushing or running `gh pr create` unless already authorized for that repository, include reproduction steps and test verification in the pull request description, and check upstream CI status after submission.
