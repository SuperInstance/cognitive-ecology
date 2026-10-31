# Example 04 — Elder Merle, a NPC Who Remembers You (persistence across restarts)

**What this teaches:** the difference between an agent with a context
window and an *organism with a life*. Elder Merle is a tavern keeper in a
game world. Players come and go; the **server restarts**; Merle's world
graph, WHY tree, commitments and script track-records persist. Run this
example twice — or watch it save, "restart" (fresh Runtime), and load —
and Merle still knows what you asked him last time.

**Run it:**

```bash
python examples/04_game_npc/main.py            # visit 1, then save + reload
python examples/04_game_npc/main.py --fresh    # wipe the save, start over
```

**What you should see:**

```
[visit 1] player asks about the old mill -> Merle gossips, remembers
[restart] fresh Runtime, state loaded from runs/merle/
[visit 2] "you asked me about the mill yesterday" — relation edges
          persisted, gossip script's success rate persisted
```

**The point:** `Runtime.save()` / `Runtime.load()` split the organism
cleanly: *behavior lives in code, history lives in state files*. The
same pattern gives any long-running agent (game NPC, DevOps responder,
lab notebook) a memory that survives deploys, crashes and reboots.
