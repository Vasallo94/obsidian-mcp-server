# Security Policy

## Supported versions

Security fixes are prepared against the current `main` branch and the latest
published release.

## Reporting a vulnerability

Please report security issues privately through GitHub Security Advisories when
available. If that is unavailable, open a minimal issue asking for a private
security contact without including exploit details.

## Local MCP security model

This server runs locally with the user's permissions. Do not point
`OBSIDIAN_VAULT_PATH` at directories that contain unrelated secrets. The server
validates vault-relative paths and blocks configured private paths, but MCP hosts
do not sandbox local processes for you.
