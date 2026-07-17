---
name: play-mud
description: Connects to and actively plays the tbaMUD (a CircleMUD/DikuMUD-derived text adventure) running at localhost:4000, logging in as the character "dummy". Explores rooms, fights monsters, picks up objects, and completes quests, while maintaining three persistent logs (actions.md, world.md, player.md) so progress survives across sessions. Use this skill whenever the user asks to play the MUD, connect to tbaMUD, log in as dummy, explore the game world, keep playing, resume MUD exploration, check on quest/combat/inventory progress, or asks what happened last time they played — even if they don't use the word "MUD" explicitly and just say something like "go explore some more" or "how's my character doing."
---

# Play MUD

Plays tbaMUD (a CircleMUD-based text MUD) as a real, persistent player would:
connect, log in, look around, act on what's there, and remember what happened
for next time. The three log files are the memory that makes this possible —
a MUD has no save-game file you can inspect; the logs *are* the save state.

## Connection details

- Server: `localhost:4000`, raw TCP (not real telnet — `nc` is used, so ignore
  stray `�` characters in the output; they're unprocessed telnet negotiation
  bytes, not game content)
- Login: username `dummy`, password `helloworld`
- Only one connection can be logged in as `dummy` at a time. If a stale
  session is still connected, the server will say "You take over your own
  body, already in use!" and drop straight into the game — that's normal,
  not an error.

## Session lifecycle

A MUD connection is stateful and long-lived (the server remembers where you
are, what you're carrying, mid-combat, etc.), but each of your tool calls is
a fresh process. `scripts/mud_client.py` bridges that gap with a detached
`tmux` session that keeps the connection open between calls:

```bash
python3 scripts/mud_client.py start            # opens the connection (safe to call if already running)
python3 scripts/mud_client.py send "look"      # sends one line, prints only the NEW output since last send
python3 scripts/mud_client.py send "" --wait 1.5   # send a bare Enter, e.g. to get past a "PRESS RETURN" screen
python3 scripts/mud_client.py status           # "running" or "stopped"
python3 scripts/mud_client.py stop             # closes the connection — always do this at the end of a session
```

Always run these from the skill's own directory (or pass its full path) so
the `state/` bookkeeping file resolves correctly. `--wait` defaults to 0.8s;
bump it for slow actions (combat rounds, movement) if output looks truncated
— if a `send` ever returns suspiciously empty, the server just hadn't
replied yet, not that nothing happened; retry the same `send ""` to read
further.

### Login flow

After `start`, login is a short fixed sequence, but the path branches once
you're past the password:

1. `send "dummy"` — username prompt
2. `send "helloworld"` — password prompt
3. One of two things happens next:
   - **Resume**: straight into the game ("You take over your own body...")
     — you're done.
   - **Menu**: a "PRESS RETURN" screen, then a numbered menu (`0) Exit`,
     `1) Enter the game`, ...). Send `""` for the press-return, then
     `send "1"` to enter the game.

Check which one you got before assuming either path — don't blindly send
`"1"` after password, since on the resume path that would be interpreted as
a game command.

## Logs — read first, write as you go

Three files live in `../../../mud-logs/` (relative to this skill, i.e. at
the top level of `02_agent_skills/`): `actions.md`, `world.md`, `player.md`.
**Read all three before connecting** so you resume from where the character
actually is, rather than assuming a fresh start.

- **actions.md** — chronological log of what you did and what happened.
  Append one entry per meaningful action (not every keystroke — group a
  short exchange like "look, then move" into one bullet if nothing
  noteworthy happened). New entries go under a `## Session N — <date>`
  heading; start a new session heading each time you connect.
- **world.md** — the map, as a catalog of rooms. One `###` heading per room,
  with its exits and what's notable there. This is what lets you navigate
  purposefully instead of wandering — before exploring, check if the room
  you're in (or a neighboring one) is already logged, and head toward
  unmapped exits first. Record exits even when you don't yet know where
  they lead (`- w: unexplored`), and fill them in once you do.
- **player.md** — current character state (level, HP/mana/move, exp, gold,
  quest points, quests completed/in-progress, notable inventory/equipment).
  This one you *overwrite* the stat block each session rather than append to
  (it's current state, not history) — keep a short "recent milestones" list
  below it if something noteworthy happened (leveled up, finished a quest).

Update all three incrementally *during* play, not just at the end — if the
session gets interrupted, the logs should still reflect real progress.

## Playing the game

This is a CircleMUD derivative, so standard Diku-family commands apply:
`look`/`l`, `north`/`n`, `south`/`s`, `east`/`e`, `west`/`w`, `up`/`u`,
`down`/`d`, `examine`/`exa <thing>`, `get <item>`, `drop <item>`,
`inventory`/`i`, `score`/`sc`, `wear <item>`, `wield <item>`, `kill <target>`,
`flee`, `rest`, `stand`, `who`. Don't assume beyond that, though — this
server has its own content and quest system on top of the base engine, and
guessing wrong just wastes a round. When unsure, `help <topic>` is cheap and
the server will suggest the right word if you're close (e.g. `help quest`
suggests `quests`, `quit`). Use `help quests` if you need a refresher on how
autoquests work: visit a questmaster NPC in the world and `quest join` an
available quest, rather than a global `quest list`.

General loop for a session:
1. Read the three logs to know where the character stands.
2. Connect, log in (handling both login paths above).
3. `look` to confirm current location matches world.md's last entry — if it
   doesn't (e.g., a "resume" landed somewhere unexpected), reconcile before
   proceeding.
4. Explore toward unmapped exits, engage with what you find (NPCs, items,
   quest hooks), and update the three logs as you go.
5. Before ending, `quit` cleanly from inside the game (don't just kill the
   connection — that leaves the character logged in and blocks the next
   session with "already in use"), then `stop` the tmux session.
6. Write a short wrap-up in actions.md and finalize player.md's stat block.

Stay confined to this skill's own files and `mud-logs/` — there's no need to
touch anything outside `02_agent_skills/` to do any of this.
