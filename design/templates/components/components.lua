--[[ design-studio component bridge.

One authoring convention — Quarto fenced divs `::: <class>` — rendered to BOTH
targets with parity:

- HTML: the div is left as-is (`<div class="<class>">`); `components.css` styles it.
- Typst: there is no CSS-class analog, so this filter wraps the div's content in a
  call to a Typst function `#c_<class>[ ... ]` defined in `_preamble.typ`.

Class names are normalized to Typst identifiers (hyphens -> underscores).
Only classes in COMPONENTS are bridged; any other div is left untouched.
]]

local COMPONENTS = {
  precis = true, pullquote = true, ["stat-panel"] = true, byline = true,
  highlight = true, ["ds-callout"] = true, panel = true, cover = true,
  section = true, contents = true, cta = true, bio = true, reference = true,
}

function Div(el)
  if not quarto.doc.is_format("typst") then
    return el
  end
  for _, c in ipairs(el.classes) do
    if COMPONENTS[c] then
      local fn = "c_" .. c:gsub("-", "_")
      local out = el.content
      table.insert(out, 1, pandoc.RawBlock("typst", "#" .. fn .. "["))
      table.insert(out, pandoc.RawBlock("typst", "]"))
      return out
    end
  end
  return el
end
