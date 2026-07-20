# Cat

An animated running cat for the Noctalia v5 bar. The cat's pace reflects
your CPU usage — idle systems get a sleeping cat, busy systems get a
sprinting one. Inspired by [RunCat](https://kyome.io/runcat/); the cat is
drawn from a small custom icon font (`fonts/catwalk2.otf`, traced from the
MIT-licensed [CatWalk](https://store.kde.org/p/2055225) plasmoid by
Driglu4it) so it can be colored like any other bar text.

## Installing from source

This works whether or not the plugin is ever accepted into
[community-plugins](https://github.com/noctalia-dev/community-plugins) — it's
how to run it straight from a clone.

**Requirements:** Noctalia v5 installed and running (`noctalia --version`),
`git`.

```bash
git clone https://github.com/DotNetRob/CatNoctaliaV5Plugin.git
mkdir -p ~/.local/share/noctalia/plugins
ln -s "$(pwd)/CatNoctaliaV5Plugin" ~/.local/share/noctalia/plugins/cat
```

A symlink (rather than a copy) means `git pull` inside the clone is picked up
without reinstalling — `.luau` edits hot-reload, `plugin.toml` edits need
`noctalia msg config-reload` (see [Debugging](#debugging)).

Then enable it:

```bash
noctalia msg plugins enable dotnetrob/cat
```

## Running it

Add the widget to a bar with **Settings → Bar: \<name\> → Add Widget → Cat**.
Click the widget in the bar to show a notification with the current CPU
percentage.

To add it without the UI (useful over SSH, or for scripting a test setup),
edit `~/.local/state/noctalia/settings.toml` directly: add `"cat"` to one of
`bar.<name>.start` / `.center` / `.end`, and add a matching section so the
Settings UI can find its settings sheet —

```toml
[bar.default]
start = [ "launcher", "cat" ]   # or center / end

[widget.cat]
type = "dotnetrob/cat:cat"
```

— then `noctalia msg config-reload`. The `[widget.cat]` section is what makes
the gear/settings icon show up on the widget's card in **Settings → Bar**;
without it the widget still renders, but there's nothing to click to
configure it (this tripped me up during development — see
[noctalia's widget_settings_registry.cpp](https://github.com/noctalia-dev/noctalia/blob/main/src/shell/settings/widget_settings_registry.cpp)
if you're curious why).

## Settings

- **Cat Size** — sprite size in the bar (12–48px, default 24)
- **Show CPU Percentage** — display the percentage next to the cat
- **Walk Threshold** — CPU % at which the cat wakes up and starts walking (default 15%)
- **Run Threshold** — CPU % at which the cat breaks into a run (default 60%)
- **CPU Poll Interval** — how often to sample CPU usage, in seconds (default 2)
- **Cat Color** — Match Theme (uses the palette's `secondary` role and tracks
  theme changes) or Custom (pick a fixed color)
- **Custom Color** — used when Cat Color is set to Custom

Clicking the widget shows a notification with the current CPU percentage.

## Debugging

**Logs:** `~/.cache/noctalia/noctalia.log`. Errors from the widget's Luau
script show up as `[ERR] [luau]`; a warning like `disabled after repeated
timeouts` means the widget crashed on `update()` and got benched — check the
log line just above it for the actual error.

**Reload behavior** — how much you need to poke the shell after an edit
depends on what changed:

| You changed | What to run |
| --- | --- |
| `cat.luau` | Nothing — it hot-reloads on save. |
| `plugin.toml` (existing keys) | `noctalia msg config-reload` |
| `plugin.toml` (added/renamed/removed a setting *key*) | Full reload — see below |
| `fonts/*.otf` contents | New filename required — see [Rebuilding the font](#rebuilding-the-font) |

For a full reload:

```bash
noctalia msg plugins disable dotnetrob/cat
noctalia msg plugins enable dotnetrob/cat
```

This one is worth knowing up front: `config-reload` alone does *not* always
pick up a setting key that didn't exist when the widget was last loaded —
during development, changing `walk_threshold`'s key name and only running
`config-reload` left the running widget calling `getConfig()` for a key that,
as far as its already-loaded settings snapshot was concerned, had never
existed, which returned `nil` and crashed `update()`. Disable/enable forces a
clean settings snapshot.

## Testing

Offline manifest/settings validation (no running shell needed):

```bash
noctalia plugins lint .
```

To exercise the actual pace behavior, generate load and watch the widget
switch from asleep → walking → running as it crosses `walk_threshold` /
`run_threshold`:

```bash
for i in $(seq 1 "$(nproc)"); do ( yes > /dev/null & ); done
# watch the bar, then:
pkill -x yes
```

## Rebuilding the font

`fonts/catwalk2.otf` isn't hand-authored — it's traced from the source SVGs
in `icons/` by `tools/build_font.py`:

```bash
python3 -m venv .venv && source .venv/bin/activate  # skip if your system pip works directly
pip install fonttools
python tools/build_font.py --family "Noctalia Catwalk 3" --out fonts/catwalk3.otf
```

(On Arch and other PEP 668 distros, a bare `pip install` fails with
`externally-managed-environment` — the venv above sidesteps that.)

Then update the `noctalia.loadFont("fonts/catwalk2.otf")` call in `cat.luau`
to point at the new file.

You only need this if you're changing the cat's artwork (swapping in
different source SVGs, adjusting `TARGET_H`/`PAD` in the script, etc.) — no
build step is needed just to run the plugin.

**Why a new filename every time:** `noctalia.loadFont()` registers fonts in a
**process-global** cache keyed by file path, and re-registering the same path
is a documented no-op. If you edit `fonts/catwalk2.otf` in place instead of
building a new file, the running shell can keep showing stale or missing
glyphs (a missing glyph falls back to a system font, which reads as a random
letter flashing where a cat frame should be) until the whole Noctalia
process restarts — a plugin disable/enable is not enough, because the cache
lives above the plugin. `tools/build_font.py` refuses to overwrite an
existing file for exactly this reason.

## License

MIT — see [LICENSE](LICENSE). The cat artwork in `fonts/catwalk2.otf` is
traced from [CatWalk](https://store.kde.org/p/2055225) by Driglu4it
(MIT-licensed); the original source SVGs are kept in `icons/` for reference
and future rebuilds.
