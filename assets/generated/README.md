# assets/generated/

Machine-generated. **Do not edit by hand** — anything here is overwritten.

| File | Produced by | Cadence |
| :-- | :-- | :-- |
| `snake-dark.svg` | [`Platane/snk`](https://github.com/Platane/snk) via [`.github/workflows/snake.yml`](../../.github/workflows/snake.yml) | daily, on push, and on demand |
| `snake-light.svg` | same | same |

The snake is generated with the profile palette rather than the GitHub defaults
(`color_snake` + five `color_dots`), so it matches the hero artwork and the
project cards:

| | snake | dots (0 → highest) |
| :-- | :-- | :-- |
| dark | `#8B5CF6` violet | `#1A1027` `#3D1B3A` `#7A1F45` `#C3134D` `#FF4D7E` |
| light | `#6D3FD1` violet | `#EFE9F6` `#F0C9DA` `#DC93B4` `#C2185B` `#8A1043` |

The two SVGs are committed so the profile page renders before the workflow has
ever run. They were bootstrapped locally with the same library the action wraps
(`generate-snake-animation@3.5.0` on npm, the `packages/generate-snake-animation`
workspace of `Platane/snk` v3.5.0), driven against the public contribution
calendar instead of the GraphQL API. After the first push the action owns them
and will rewrite the pair whenever the calendar changes.

Each file is a CSS-animated SVG (`@keyframes`, no `<script>`), so it still
animates when GitHub loads it through an `<img>` tag, and the first frame is a
complete contribution grid — which matters because GitHub puts a pause control
on animated images.
