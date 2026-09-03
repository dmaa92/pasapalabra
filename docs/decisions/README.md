# Architecture Decision Records

Use an ADR for a decision with real future consequence — something a
later contributor would otherwise have to re-derive or, worse,
accidentally re-litigate. Do **not** create one for:

- an open question that hasn't been decided yet (put it in
  `docs/product.md`'s Open Questions instead),
- a routine implementation detail with no lasting architectural weight.

## Filename and title

`NNNN-kebab-case-title.md`, zero-padded, sequential, never reused or
renumbered — even if a later decision supersedes an earlier one (mark the
old one superseded in place; don't delete or renumber it).

Title: `# ADR-NNNN: <decision, stated as a sentence>` — not a noun
phrase.

## Template

```markdown
# ADR-NNNN: <decision statement>

# Context
<What forced a decision to be made. Facts, not opinions.>

# Alternatives
a. **<option>** — Descartada: <why not>
b. **<option>** — Elegida.

# Decision
<The decision, stated plainly, one paragraph.>

# Rationale
<Why this alternative, weighed against the quality attributes that
actually matter for this project.>

# Consequences
## Positivas
- <benefit>
## Negativas y riesgos
- <accepted trade-off — write it down, don't hide it>
```

An optional trailing `# Follow-up` section may link to the issue or repo
where the decision gets executed.

See `0001-adopt-template-baseline.md` for a worked example.
