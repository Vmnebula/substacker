# Security Policy

## Supported versions

Substacker is pre-1.0. Security fixes are applied to the `main` branch and released in
the next tagged version. Older tags do not receive backported fixes.

| Version | Supported |
| ------- | --------- |
| `main`  | Yes       |
| < 0.1   | No        |

## Reporting a vulnerability

Please do not open a public issue for security problems.

Report vulnerabilities through GitHub's private vulnerability reporting:

1. Go to the [Security tab](https://github.com/Vmnebula/substacker/security).
2. Select **Report a vulnerability**.
3. Describe the issue, the affected version or commit, and the steps to reproduce it.

You will receive an acknowledgement within 5 business days. Once the report is
confirmed, a fix and a disclosure timeline will be agreed with you before any
public advisory is published.

## Scope

In scope:

- Authentication and authorisation flaws
- Injection, deserialisation, and path traversal issues
- Secret or credential leakage through logs, responses, or repository history
- Dependency vulnerabilities that are reachable from application code

Out of scope:

- Findings that require a compromised host or a privileged local account
- Denial of service caused by unbounded input that the operator controls
- Vulnerabilities in third-party services that this project only integrates with

## Handling credentials

Never include real API keys, tokens, or customer data in an issue, pull request,
or test fixture. Copy `.env.example` to `.env` for local configuration; `.env` is
excluded from version control.
