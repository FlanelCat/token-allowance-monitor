# Development Roadmap

This is the durable planning document for Token Allowance Monitor. **Read this file before proposing or implementing new features.** It records user-observed VS Code Codex controls, desired functionality, unresolved technical questions, and release scope. Treat UI labels and current selections as observations, **not** verified stable APIs or universal settings.

## Current baseline: v0.1.0

The CLI and KDE Plasma widget display live five-hour and weekly Codex allowance usage via the Codex app-server `account/rateLimits/read` request. Historical per-request token statistics remain optional. Preserve the existing `codex-usage --json` contract and robust handling of unavailable data.

**Note:** The existing README may still describe the older JSONL allowance source; update documentation when working on the next release.

## Guiding principles

- Monitor first: v0.2.0 should **display** information, not modify Codex configuration, approval policy, or active sessions.
- **Scope is critical.** A user may have multiple VS Code windows, Codex instances, workspaces, and conversations. Determine whether each value is account-wide, per-process, per-workspace, per-thread/conversation, or a UI-only preference. Do not present one instance's setting as global.
- Identify the source and scope of each reported value, along with its freshness and whether it is verified or inferred.
- Use documented or locally discoverable read-only APIs when possible. Avoid brittle scraping of VS Code UI, undocumented private storage, or files containing credentials.
- Preserve existing CLI/JSON/widget compatibility; add fields without silently changing the meaning of current keys. Unknown or unavailable must not be displayed as a definite setting.
- Keep sensitive context private: never log authentication data, source files, IDE selections, prompts, or complete raw responses.
- Prefer incremental changes with tests, clear errors, and no extra background polling beyond what is needed.

## v0.2.0 — Codex Environment & Status

**Goal:** Show the active Codex environment and relevant session settings next to allowance usage, reducing the need to hunt through VS Code menus.

### 1. Execution location / mode

**Observed UI:** A dropdown near the bottom of the Codex panel offers:
- `Continue in Local`
- `Connect Codex Web`
- `Cloud` (disabled in the observed installation)

**Current user observation:** “Work locally.”

**Desired display:** Current execution location/mode and, where meaningful, availability of other modes. Investigate what “Connect Codex Web” does and whether “Cloud” availability depends on authentication, plan, workspace, or extension version. Do not infer availability solely from the displayed subscription plan.

### 2. Approval and permissions mode

**Observed UI:** `Change permissions`, with options:
- `Ask for approval`
- `Approve for me`
- `Full Access`

**Current user observation:** “Approve for me.”

**Desired display:** Effective approval/permission mode for the relevant Codex instance or conversation. Determine whether the UI label maps to an app-server configuration field, and distinguish approval policy from sandbox/filesystem/network access. This is **display-only** in v0.2.0; do not provide a control that escalates privileges.

### 3. Model, reasoning effort, and speed

**Observed UI:** `Select effort` with:
- A `1.5x more speed` control
- `Light`, `Medium`, `High`, `Extra High`, `Ultra`

**Current user observation:** “GPT-Astra Light.”

**Desired display:** Active model, selected effort level, and speed option/status if it is a distinct setting. Verify the meaning and availability of “1.5x more speed” rather than assuming it is a permanent model property. Capture the scope of model and effort selection; different conversations or instances may differ. UI labels and options may change between Codex versions.

### 4. IDE context inclusion

**Observed UI:** A button whose tooltip says: “Include context from IDE such as selection state and open files. `/ide` to toggle”.

**Current user observation:** Purpose and effective state not yet understood.

**Research first:** Determine what enabling this feature actually shares with Codex, whether it includes only metadata or also selected/open-file contents, how it is toggled, and whether its state is per-message, per-conversation, or per-workspace.

**Desired display:** A clearly labeled IDE-context state (`enabled`, `disabled`, or `unknown`) **only if a reliable read-only source exists**. Never read or store IDE context contents merely to show the toggle state.

### 5. Subscription / account plan

**Observed UI:** The user's `Plus` subscription level is not readily visible in the main Codex panel.

**Desired display:** Show the plan (for example, `Plus`) near allowance usage. The live allowance API already exposes `rateLimits.planType`; reuse this field and handle missing values. Distinguish subscription plan from model availability, cloud eligibility, and quota buckets.

## Cross-cutting investigation: multiple Codex instances

Before implementing v0.2.0 settings reporting:

1. Inventory relevant read-only sources: Codex app-server protocol/schema, Codex CLI configuration, VS Code extension interfaces, and any safe per-instance identifiers.
2. Create a **scope matrix** for every proposed field: account / app-server process / VS Code window / workspace / thread / transient UI state.
3. Test with at least two VS Code windows or Codex conversations using deliberately different settings, if possible.
4. Decide how the CLI and Plasma widget select a target instance. If the active instance cannot be determined reliably, use explicit selection or label values as global/unknown rather than claiming they belong to the focused VS Code window.
5. Define sensible fallback behavior when VS Code is closed or a setting is inaccessible.
6. Document which fields are verified by an API and which are unavailable; do not invent settings from defaults.

**Acceptance criteria for v0.2.0:**
- Existing allowance readings, historical token display, CLI modes, and Plasma widget still work.
- Plan is shown when available, independently of other settings.
- Each additional setting is accurate for a clearly identified scope, or explicitly marked unknown/unavailable.
- No accidental privilege changes, IDE-content capture, credentials exposure, or session modification.
- Automated tests cover multiple-instance ambiguity, missing settings, API failures, and backward-compatible JSON output.
- CLI and widget remain usable if no VS Code Codex instance is running.

## v0.3.0 — Advanced Codex Settings & Integration (deferred)

**Observed UI:** The cog-wheel at the top of the Codex panel leads to a settings view containing:
- General
- Configuration
- Personalization
- Usage & billing
- MCP servers
- Hooks
- Plugins
- Account

**Long-term goal:** Bring useful status and configuration information from these deeper screens into an accessible monitor view, avoiding duplication where Codex already exposes good information.

**Research questions:**
- Which settings are most useful at a glance, and which should remain in the native Codex settings UI?
- Which can be read safely through supported interfaces?
- Which are global versus workspace- or conversation-specific?
- Can the monitor link to native settings rather than reimplementing them?
- What privacy, security, maintenance, and UI complexity costs would each integration introduce?
- Would an expanded view fit the Plasma widget, or should the project offer a separate detailed interface?

**Out of scope until explicitly approved:** Changing account/billing settings, managing MCP servers/plugins/hooks, writing configuration files, or modifying approval and sandbox policies.

## Suggested implementation workflow for future Codex sessions

1. Read this roadmap, the current README, the existing backend/widget code, and tests.
2. Check current Codex CLI/extension capabilities; do not assume the UI or app-server schema is unchanged.
3. Produce a concise feasibility report and a per-field source/scope matrix **before editing code**.
4. Propose the smallest v0.2.0 increment, with JSON fields, CLI/widget presentation, tests, and failure behavior.
5. **Wait for user approval** before implementing.
6. Implement incrementally, run the full test suite, inspect diffs, and verify against actual VS Code settings.
7. Do not commit, push, or publish without explicit approval for that step.

## Open decisions

- Should the Plasma widget show only a compact summary, with details in a tooltip/popover, or provide a separate expanded view?
- How should a user choose among multiple Codex windows/conversations?
- Should the monitor show the current setting, the effective setting, or both when they differ?
- Is “1.5x more speed” a persistent preference, a temporary mode, or an account capability?
- Can the IDE-context toggle state be observed without accessing IDE content?

## Notes for future maintainers

The labels and current selections above were recorded from the user's VS Code Codex UI in October 2026. They are requirements and research leads, not proof of API support. Prioritize correctness, transparent unknown states, and backward compatibility over showing every setting.
