# tohk.io world search

The world list for the **tohk.io world search** panel (a VRChat world prefab).

The panel downloads `worlds.txt` from this repository's GitHub Pages site once,
when the world loads, and searches it inside the world.

    https://tokyubevoxelverse.github.io/tohk-world-search/worlds.txt

## Files

| File | What it is |
|---|---|
| `worlds.txt` | The list. One world per line, most visited first, tab separated. |
| `collect_worlds.py` | Builds and updates the list. Read the top of the file first. |

## The list format

    #tohk-world-index <tab> 1 <tab> <count> <tab> <date>
    id <tab> name <tab> author <tab> visits <tab> favorites <tab> platforms <tab> tags

`platforms` is 1 (PC) + 2 (Quest) + 4 (iOS). `tags` are comma separated.

## Updating the list

    python collect_worlds.py --contact you@example.com
    git add worlds.txt
    git commit -m "Update world list"
    git push

The collector uses **your own VRChat login** and waits 60 seconds between
requests. VRChat does not officially support scripted use of its API.
Worlds tagged as adult or sexual content are left out unless you pass
`--include-adult`.

Never commit your `auth` cookie. The collector keeps it in memory only.
