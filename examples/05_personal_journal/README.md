# Example 05 — The Personal Journal (anti-RAG recall, no embeddings)

**What this teaches:** the anti-RAG claim made concrete on personal
knowledge. A week of journal entries is ingested into the World Graph;
Hebbian consolidation wires what co-occurs ("coffee" + "deadline",
"run" + "slept well"). Recall is then a **walk** from cue concepts — it
surfaces *related* entries a keyword search can never find — and a
**burden guard** script shows an organism learning when NOT to nag.

**Run it:**

```bash
python examples/05_personal_journal/main.py
```

**What you should see:**

```
[ingest] 7 entries -> N nodes, M co-occurrence edges
[recall] "why was I tired on thursday?"
  walk found: tired, sleep, coffee, run, ...      <- the STORY, not the word
  keyword search found: (nothing)                 <- "tired" never appears
                                                      literally; "thursday?"
                                                      != "thursday"
[burden] the check-in nag fired only when its trigger crossed 0.20,
         and stopped entirely once the debt was paid (veto law in action)
```

**The point:** an embedding store answers "what is similar to this
string"; a world graph answers "what was going on around this". For
memory — as opposed to search — the second question is the one that
matters.
