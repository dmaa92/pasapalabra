# Claude Skills

This directory is intentionally empty of repo-specific skills at
template creation time. Only add a Claude-specific skill here when a
workflow genuinely cannot stay tool-neutral — prefer a tool-neutral skill
under `.agents/skills/` instead, so it also works with other agent
tooling.

Shared, organization-wide skills (create-adr, implement-issue,
review-change, security-review) should be provided centrally and
symlinked or copied in here — not hand-authored per project.
