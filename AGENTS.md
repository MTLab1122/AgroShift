# AgroShift — Permanent Development Rules

## 1. Project authority
- The approved original Module 03 five-phase specification is the source of truth.
- Approved architecture decisions and acceptance criteria must be preserved.
- Never silently reinterpret, remove, simplify, or replace requirements.
- If two requirements conflict, stop and report the exact conflict.

## 2. Phase boundaries
- Implement only the phase explicitly authorized by the user.
- Never begin a later phase without explicit user approval.
- Complete the current phase's acceptance criteria before declaring it complete.
- Stop after the phase completion report and wait for human review.

## 3. Before changing code
- Inspect the existing repository structure and relevant files.
- Inspect the current Git branch and working-tree status.
- Understand existing module responsibilities and interfaces.
- Reuse established project conventions where appropriate.
- Do not assume dependencies, database infrastructure, or files exist.

## 4. Change control
- Work only on the explicitly assigned task.
- Make small, logically isolated changes.
- Do not modify unrelated modules or files.
- Do not delete, rename, or change required fields without approval.
- Do not overwrite existing user work.
- Do not run destructive commands or reset Git history.
- Never commit, push, merge, or change branches without explicit approval.

## 5. Technical correctness
- Do not invent agricultural facts, sources, measurements, or validation results.
- Preserve unknown and uncertain data explicitly.
- Use portable database and SQL patterns unless the project explicitly requires otherwise.
- Maintain compatibility with existing modules and APIs.
- Do not add duplicate responsibilities already owned by other modules.

## 6. Verification
- Run relevant tests after each implementation batch.
- Run regression tests for existing functionality affected by changes.
- Report actual commands, exit codes, and test results.
- Never claim a test passed if it was not executed successfully.
- Never hide failures or replace failing tests with weaker tests.
- A task is not complete while its required acceptance checks are failing.

## 7. Reporting
Before finishing each assigned task, report:
1. Files created or changed.
2. Architectural decisions and dependencies.
3. Tests and exact results.
4. Requirements completed.
5. Requirements not completed.
6. Risks, limitations, and blockers.

## 8. Human approval
- Do not make architectural decisions that materially change approved requirements.
- Ask before proceeding when an ambiguity affects correctness.
- Treat user approval as mandatory for phase transitions and Git milestones.
- Do not declare a phase complete on your own authority.
