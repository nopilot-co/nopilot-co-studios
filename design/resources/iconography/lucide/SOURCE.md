# Lucide — vendored (nopilot icon lock)

- **Set:** lucide · **Version:** 0.469.0 · **License:** ISC (open)
- **Source:** https://lucide.dev — pulled from
  `https://cdn.jsdelivr.net/npm/lucide-static@0.469.0/icons/<name>.svg`
- **Brand lock:** nopilot `tokens.yaml` → `icon` (`set: lucide`, `stroke: 1.5px`,
  `size: sm 16 / md 20 / lg 24`). The 1.5px stroke + colour are applied by
  `design/uds/ui/base.css` `.uds-icon`; these SVGs carry geometry only.
- **UI sprite:** built into `design/uds/ui/icons.svg` (symbol id `i-<alias>` →
  lucide name); examples reference `../icons.svg#i-<alias>`.

## Vendored icons (alias → lucide name)

- `i-grid` → `layout-dashboard`
- `i-users` → `users`
- `i-branch` → `git-branch`
- `i-building` → `building-2`
- `i-check` → `circle-check-big`
- `i-chart` → `chart-column`
- `i-cog` → `settings`
- `i-search` → `search`
- `i-bell` → `bell`
- `i-panel-left` → `panel-left`
- `i-panel-right` → `panel-right`
- `i-chevron` → `chevron-right`
- `i-plus` → `plus`
- `i-x` → `x`
- `i-arrow` → `arrow-right`
- `i-back` → `arrow-left`
- `i-mail` → `mail`
- `i-lock` → `lock`

## Re-pull / regenerate

```
curl -sSL "https://cdn.jsdelivr.net/npm/lucide-static@0.469.0/icons/{NAME}.svg" -o icons/NAME.svg
python3 /path/to/build-sprite   # rebuilds design/uds/ui/icons.svg from icons/
```
