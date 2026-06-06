# Agent Feedback Protocol

This repository opts in to the Agent Feedback Protocol (AFP) for out-of-band
feedback from AI agents that use the Obsidian MCP server.

AFP is not an MCP tool and this server does not expose a feedback tool. The MCP
server only declares its identity and preferred feedback sink in `afp.json`.
Agents and harnesses generate AFP reports outside the MCP tool call path with
the AFP CLI or SDK.

## When to Report

Create an AFP report when an agent's plan was blocked or degraded by the MCP
server, for example:

- a tool response was confusing or missing actionable detail,
- a tool contract did not match the agent's expectation,
- a required capability was missing,
- an integration failure forced a shell or filesystem workaround.

Do not include secrets, vault-private content, personal data, or raw note
contents. Summarize the friction with the minimum context needed to reproduce
or understand it.

## Subject URIs

Use the repository-level subject when the issue applies to the whole server:

```text
mcp://github.com/Vasallo94/obsidian-mcp-server
```

Use a fragment when the friction is tied to one MCP tool:

```text
mcp://github.com/Vasallo94/obsidian-mcp-server#notes.create
mcp://github.com/Vasallo94/obsidian-mcp-server#notes.patch
mcp://github.com/Vasallo94/obsidian-mcp-server#client.roots
```

## Draft-First Flow

During dogfooding, create local drafts first. Do not auto-open GitHub issues
until the draft has been reviewed.

Create a partial report:

```json
{
  "subject_uri": "mcp://github.com/Vasallo94/obsidian-mcp-server#notes.patch",
  "goal": "Patch a note after reading the exact section heading",
  "expectation": "notes.patch would suggest close matches when the old text was not found",
  "observed": "The tool returned a generic text-not-found error, so the agent retried by guessing the Unicode emoji",
  "friction_type": "confusing_interface",
  "fault_domain": "ambiguous_contract",
  "severity": "degraded",
  "plan_step": "After reading the note, replace a heading with normalized text",
  "workaround": "Reread the note and retried with a different exact-match string"
}
```

Generate and validate the full AFP report:

```bash
uv run afp report --from partial.json --out report.json
```

Deposit it as a local draft from the repository root:

```bash
uv run afp submit report.json --dir . --sink draft
```

The draft is written under `.afp/drafts/`. Review the JSON before opening a
GitHub issue.

## Converting a Draft to an Issue

After review, create an issue manually:

```bash
gh issue create \
  --repo Vasallo94/obsidian-mcp-server \
  --label afp-report \
  --title "[AFP/confusing_interface] notes.patch exact-match near miss" \
  --body-file report.json
```

Remote submission may be enabled later once several drafts have been reviewed
and the redaction/minimization flow is trusted.
