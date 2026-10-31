# Example 01 — The 60-Second Heartbeat (zero LLM, zero keys)

**What this teaches:** the minimal loop of the kernel — a WHY, a drive,
two scripts, an attention market — plus the one law that makes this
project different: **purpose is conserved**. You will kill the organism's
purpose, watch everything stop *without anything being deleted*, and then
bring it back.

**Run it:**

```bash
python examples/01_zero_llm_heartbeat/main.py
```

No API keys. No network. No dependencies beyond the kernel itself.

**What you should see:**

```
tick  attention  ran
   1     0.049   observe
   2     0.065   observe
   ...
-- killing the root WHY --
after: alive=0 dead=1 unknown=1  invariant_ok=True
ticks 11-15: nothing runs (purpose is QUESTIONABLE, not gone)
-- resurrecting with new evidence --
tick 16 onward: life resumes
necrology: 3 records. nothing was ever deleted.
```

**The point:** most agent frameworks lose their purpose when a prompt is
edited or a context window evaporates. Here purpose is a conserved
quantity with an audit trail. Read `main.py` top to bottom — it is about
80 lines and every line maps to a layer.
