# Cat

An animated running cat for the Noctalia v5 bar. The cat's pace reflects
your CPU usage — idle systems get a sleeping cat, busy systems get a
sprinting one. Inspired by [RunCat](https://kyome.io/runcat/); the cat is
drawn from a small custom icon font (`fonts/catwalk2.otf`, traced from the
MIT-licensed [CatWalk](https://store.kde.org/p/2055225) plasmoid by
Driglu4it) so it can be colored like any other bar text.

## Install (local development)

```bash
mkdir -p ~/.local/share/noctalia/plugins
ln -s /home/rob/Code/claude/CatNoctaliaV5Plugin ~/.local/share/noctalia/plugins/cat
```

Then in Noctalia: **Settings → Plugins → Scan for Plugins → enable Cat →
add the "Cat" widget to a bar**.

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

## Development note: font caching

`noctalia.loadFont()` registers fonts with a **process-global** cache keyed by
file path, and re-registering the same path is a documented no-op. If you
edit the glyph artwork in `fonts/catwalk2.otf` in place, the running shell can
keep showing stale/missing glyphs (missing glyphs fall back to a system font,
which reads as a random letter flashing where a cat frame should be) until
the whole Noctalia process restarts — a plugin disable/enable is not enough,
because the cache lives above the plugin.

So: whenever the glyph *contents* change, give the font file a new name (and
update the `familyName`/`loadFont()` call to match) rather than overwriting
`catwalk2.otf` in place. Bump the name again for the next change.

## License

MIT — see [LICENSE](LICENSE). The cat artwork in `fonts/catwalk2.otf` is
traced from [CatWalk](https://store.kde.org/p/2055225) by Driglu4it
(MIT-licensed); the original source SVGs are kept in `icons/` for reference
and future rebuilds.
