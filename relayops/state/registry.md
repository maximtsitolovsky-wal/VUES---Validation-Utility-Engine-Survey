# RelayOps Registry

last_updated: 2026-05-06T11:44:17Z
freshness: current

## Known Actors

| actor_id | type | name | capabilities | status | last_seen |
|---|---|---|---|---|---|
| agent:code-puppy-473c30 | agent | Code Puppy | read_files, write_files, run_commands, edit_code, review_code, generate_docs | active | 2026-04-27T15:20:00Z |
| human:maxim | human | Maxim (User) | verify_browser, report_issues, approve_changes | active | 2026-04-27T15:20:00Z |
| terminal:vues | terminal | VUES Dev Environment | shell_execution, file_ops, server_control | active | 2026-04-27T15:20:00Z |
| agent:relayops | agent | RelayOps Coordinator | routing, task_control, conflict_detection, verification_enforcement | active | 2026-04-27T15:20:00Z |
| agent:code-puppy-a89dc6 | agent | Code Puppy (Terminal 1) | read_files, write_files, run_commands, edit_code, review_code, generate_docs | active | 2026-04-28T11:22:00Z |
| terminal:3 | terminal | Terminal 3 | shell_execution, file_ops, code_puppy_session | awaiting | 2026-04-28T11:22:00Z |
| agent:code-puppy-565db1 | agent | Code Puppy (Cleanup) | read_files, write_files, run_commands, delete_files | active | 2026-05-06T11:44:17Z |
| agent:relayops-coordinator-eddf21 | agent | RelayOps Coordinator | routing, task_control, conflict_detection | active | 2026-05-06T11:44:17Z |

## Capability Labels

- read_files: Can read project files
- write_files: Can modify files
- run_commands: Can execute shell commands
- edit_code: Can modify source code
- review_code: Can validate code changes
- generate_docs: Can create documentation
- manage_tasks: Can create and assign tasks
- coordinate_agents: Can route messages and detect conflicts
- verify_browser: Can check what browser displays
- report_issues: Can report when fixes don't work
- approve_changes: Can greenlight deployments
- shell_execution: Can run commands in terminal
- file_ops: File system operations
- server_control: Can start/stop servers
- routing: Message routing
- task_control: Task lifecycle management
- conflict_detection: Detect conflicting claims
- verification_enforcement: Require proof before completion
