# Telegram Control Surface Design For TradingAgents-MultiMarket

**Date:** 2026-04-09

**Status:** Approved design, pending implementation plan

## Goal

Add a Telegram control surface for `TradingAgents-MultiMarket` so Jin can configure and run analyses from Telegram while preserving the existing CLI and keeping the runtime Docker-friendly.

The Telegram experience should preserve the CLI's option-driven workflow, but it should do so in a Telegram-native way with inline buttons and short text prompts rather than trying to drive the current interactive terminal UI remotely.

## Constraints

- The current CLI remains supported.
- Telegram must not drive the existing `questionary` / `rich live` terminal flow through a pseudo-terminal.
- Runtime stays Docker-safe and self-contained.
- The Telegram path should reuse the core TradingAgents graph and report-writing behavior instead of forking analysis logic.
- Telegram must render provider, model, and provider-setting options from shared catalogs rather than maintaining a Telegram-only copy.
- First version is private, single-user, and single-active-job only.
- When a job is already running and Jin starts a new one, the bot must prompt to cancel the current job and switch rather than silently queueing or running both.
- Telegram should remember the last successful configuration and use it as the next default.
- Full CLI-equivalent configuration must be available in Telegram:
  - ticker
  - analysis date
  - output language
  - analyst selection
  - research depth
  - LLM provider
  - quick model
  - deep model
  - provider-specific effort / thinking settings

## Scope

### In Scope

- Add a Telegram bot service to `docker-compose.yml`.
- Add a Telegram-native configuration flow using inline keyboards plus limited text entry.
- Introduce a shared non-interactive analysis runner used by both CLI and Telegram.
- Persist last-used successful settings for the Telegram user.
- Support `/analyze`, `/status`, and `/cancel`.
- Deliver final analysis summary plus `complete_report.md` back to Telegram.
- Preserve partial logs and report artifacts on failure or cancellation.
- Add tests for configuration state, task control, result delivery, and runner reuse.

### Out Of Scope

- Multi-user support.
- Telegram group-chat support.
- Webhook deployment in the first version.
- Parallel jobs, queues, or a job scheduler.
- Order execution, broker integration, or authenticated trading actions.
- Rebuilding the TradingAgents graph or analyst topology.
- Replacing the existing CLI.

## Recommended Architecture

Use a shared non-interactive runner beneath two frontends:

- CLI frontend
- Telegram frontend

The current CLI mixes three concerns in one flow:

- collecting user selections
- streaming analysis progress to the terminal
- writing reports and logs

The Telegram design should separate those concerns so both frontends can reuse the same execution path.

### Why This Approach

- It avoids the brittle mistake of trying to remote-control a terminal UI from Telegram.
- It keeps analysis behavior in one place.
- It preserves the CLI while making Telegram a first-class entrypoint.
- It makes cancellation, status reporting, and default-setting persistence much easier to implement cleanly.

## Target Module Shape

### Shared Runner Layer

Add a non-interactive runner module that accepts a structured configuration and returns structured execution state.

Recommended responsibilities:

- validate a complete analysis request
- build the TradingAgents config object
- create result directories
- run the graph
- expose stage updates for UI consumers
- write logs and report artifacts
- return final state, decision, artifact paths, and failure details

Recommended module split:

- `tradingagents/app/analysis_request.py`
  - request schema and validation helpers
- `tradingagents/app/analysis_runner.py`
  - shared execution entrypoint used by CLI and Telegram
- `tradingagents/app/job_state.py`
  - job-state serialization helpers

The exact file names can change during implementation, but the runner must be independent from Telegram and independent from terminal rendering.

### CLI Frontend

The CLI continues to gather options interactively, then hands the resulting request to the shared runner.

The CLI-specific code keeps:

- `questionary` prompts
- `rich` live display
- local terminal formatting

The CLI should stop owning the core run loop directly.

### Telegram Frontend

The Telegram bot owns:

- command handling
- draft configuration editing
- inline keyboard rendering
- status messages
- cancellation prompts
- result delivery

The bot should not contain TradingAgents analysis logic beyond translating Telegram selections into a shared analysis request.
It should also read provider/model option data from shared application-layer catalogs so future provider additions appear in Telegram without Telegram-specific rewiring, as long as they fit the existing option shape.

## Telegram Interaction Design

### Supported Commands

- `/analyze`
- `/status`
- `/cancel`

### `/analyze` Entry Behavior

When Jin starts `/analyze`, the bot should:

1. Load the last successful configuration if one exists.
2. Create or refresh a draft session from that configuration.
3. Show a configuration summary message with inline keyboard controls.

The summary message should include:

- ticker
- analysis date
- output language
- selected analysts
- research depth
- LLM provider
- quick model
- deep model
- provider-specific thinking / effort settings

Buttons should include:

- edit ticker
- edit date
- edit language
- edit analysts
- edit depth
- edit provider
- edit quick model
- edit deep model
- edit provider-specific settings
- start analysis
- restore last successful config
- reset to defaults

### Input Method Rules

Use two input styles:

- inline keyboard selections for bounded option sets
- text input only where free-form entry is genuinely needed

Text input is appropriate for:

- ticker
- analysis date
- custom model ID where the provider supports arbitrary model names

Inline keyboard selection is appropriate for:

- analyst toggles
- output language
- research depth
- provider
- provider-specific effort / thinking settings
- common quick/deep model options

### Provider And Model Rules

The Telegram flow must preserve compatibility constraints:

- provider is selected first
- quick/deep models are selected within the current provider
- changing provider invalidates incompatible model selections
- changing provider also invalidates incompatible provider-specific effort settings

If the provider supports arbitrary custom IDs, the flow may offer:

- common preset buttons
- a custom entry path

### Running Job Conflict Rule

If `/analyze` is invoked while a job is already running, the bot must not start a second job immediately.

Instead it should show a confirmation prompt with:

- `Cancel current and switch`
- `Keep current job`

If Jin confirms switch:

- cancel the running job
- keep the newly edited draft
- start the new job after cancellation completes

## State Model

Because this is a private single-user bot, the first version can use small local persisted files rather than a database.

Three state buckets are sufficient:

### 1. Last Successful Preferences

Purpose:

- default values for the next `/analyze`

Suggested contents:

- full successful analysis configuration
- timestamp

### 2. Draft Session

Purpose:

- current Telegram-side edits before the next run starts

Suggested contents:

- in-progress analysis configuration
- message IDs used for updating the config summary
- whether the bot is waiting for text input for a specific field

### 3. Active Job

Purpose:

- runtime control and status reporting

Suggested contents:

- job ID
- process ID or worker handle
- configuration snapshot
- started-at timestamp
- current status
- current stage
- result directory
- last status message metadata
- terminal outcome: completed, failed, cancelled

## Execution Model

The Telegram bot should run the analysis in a child process or similarly isolated worker owned by the bot service.

Requirements:

- exactly one active job at a time
- the bot retains enough handle information to stop the worker on `/cancel`
- cancellation is explicit and operator-visible
- partial outputs remain on disk

The runner should write artifacts under the existing results layout so Telegram and CLI share the same report convention.

## Status And Result Delivery

### `/status`

`/status` should return a concise structured summary with:

- state: `idle`, `drafting`, `running`, `cancelling`, `failed`, `completed`, or `cancelled`
- ticker
- analysis date
- research depth
- provider plus quick/deep model
- current stage
- elapsed time
- result directory if available

### Start Message

When a job starts, the bot should send a single launch message containing:

- ticker
- analysis date
- research depth
- model summary

This message may be updated as progress changes, or the bot may send a small number of follow-up progress messages. The implementation should favor restraint over chat spam.

### Completion Message

When a job completes successfully, the bot should send:

- a short summary
- the final decision
- `complete_report.md` as a Telegram document

Optional future enhancements can attach additional section files, but the first version only needs the complete report.

### Failure Message

When a job fails, the bot should send:

- failure stage
- concise error summary
- whether partial artifacts were written
- a retry action that restores the last attempted configuration into the draft

### Cancellation Message

When a job is cancelled, the bot should say so explicitly and preserve the partial result path if anything was already written.

Cancellation should not be mislabeled as failure.

## Error Handling Rules

- Invalid ticker: reject before starting the job.
- Invalid date or future date: reject before starting the job.
- Incompatible provider/model combination: reject before starting the job.
- Missing required API key for the chosen provider: reject before starting the job.
- Telegram send failure: keep the analysis result on disk and mark delivery as needing retry.
- Runtime data-provider or LLM failure: mark the job as failed, preserve logs and partial artifacts.
- Cancellation: mark the job as cancelled and preserve any artifacts already written.

## Deployment Design

Add a separate `telegram-bot` service to `docker-compose.yml`.

The service should:

- build from the same project source
- use the same `.env`
- mount the same `results` directory
- read a Telegram bot token from environment

The first version should use Telegram polling rather than webhooks.

Why polling first:

- less infrastructure
- easier local and VM deployment
- enough for a private single-user control surface

## Security And Access Model

The first version is private-use only.

Minimum safeguards:

- allow commands only from Jin's Telegram user ID or chat ID
- reject all other senders
- do not execute outbound actions other than replying in Telegram

This is not a multi-tenant design.

## Testing Strategy

### Configuration State Tests

- loads last successful config into a new draft
- preserves draft changes across Telegram callbacks
- clears incompatible model fields when provider changes
- clears incompatible provider-specific settings when provider changes

### Task Control Tests

- starts a single job from a valid request
- `/analyze` during an active job triggers the cancel-or-keep decision path
- `/cancel` terminates the active worker and writes cancelled state

### Result Delivery Tests

- successful run sends summary plus `complete_report.md`
- Telegram send failure does not destroy local artifacts
- retry path reuses the previous failed request

### Shared Runner Tests

- shared runner converts structured selections into TradingAgents config correctly
- shared runner writes into the existing results directory structure
- CLI and Telegram can both call the same runner interface

## Design Decisions Locked By This Spec

- Telegram gets the full option set, not a reduced MVP configuration.
- The Telegram UX is Telegram-native, not a remote-controlled terminal UI.
- The system is single-user and single-active-job in the first version.
- A new `/analyze` during a running job prompts for cancel-and-switch.
- The bot remembers the last successful configuration and uses it as the default next time.
- Telegram deployment is a separate polling service in Docker Compose.

## Non-Goals For This Phase

- multi-user roles
- chatroom collaboration
- queueing multiple jobs
- webhook infrastructure
- account trading actions
- broad workflow automation beyond analysis control
