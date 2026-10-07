# -*- coding: utf-8 -*-
"""
tohk.io world search - WORLD LIST COLLECTOR
===========================================
Builds worlds.txt, the list the in-game panel downloads and searches.

It asks VRChat's own API for public worlds, a hundred at a time, using YOUR
VRChat login, and merges what it finds into worlds.txt next to this file.
Run it again any time: it adds to the list it already has.

READ THIS FIRST
  * VRChat does not officially support scripted use of its API. It asks that
    requests be slow (this waits 60 seconds between them by default) and that
    every caller says who it is. Using it is your decision and your account.
  * It needs your "auth" cookie. That cookie IS your login: never share it,
    never put it in a file you commit. This script only keeps it in memory.
  * It needs a contact (an email or a Discord name) to put in the request
    header, because VRChat refuses callers that do not identify themselves.

HOW TO GET THE COOKIE
  1. Log in at https://vrchat.com/home in your browser.
  2. Press F12 > Application (Chrome/Edge) or Storage (Firefox) > Cookies >
     https://vrchat.com
  3. Copy the VALUE of the cookie named "auth" (it starts with authcookie_).

RUN
  python collect_worlds.py --contact you@example.com
  (it then asks for the cookie; or set the VRC_AUTH_COOKIE environment variable)

  --requests 60      how many requests this run makes (60 = about an hour)
  --delay 60         seconds between requests
  --include-adult    keep worlds tagged as adult / sexual content (left out by default)
  --selftest         check the list format with made-up data; contacts nobody

THE LIST (worlds.txt): one world per line, most visited first, tab separated:
  id  name  author  visits  favorites  platforms  tags
  platforms: 1 = PC, 2 = Quest, 4 = iOS, added together (7 = all three)
  The first line is a header:  #tohk-world-index  1  <count>  <date>
"""
import argparse, datetime, getpass, io, json, os, sys, time, urllib.error, urllib.parse, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "worlds.txt")
API = "https://api.vrchat.cloud/api/1/worlds"
ADULT_TAGS = ("content_sex", "content_adult")

# What to ask for, in order. Each line is one request per page of 100.
SORTS = ["popularity", "heat", "favorites", "updated", "created"]
TAGS = ["author_tag_game", "author_tag_games", "author_tag_horror", "author_tag_chill", "author_tag_club",
        "author_tag_avatar", "author_tag_avatars", "author_tag_puzzle", "author_tag_adventure", "author_tag_music",
        "author_tag_art", "author_tag_sleep", "author_tag_hangout", "author_tag_exploration", "author_tag_udon",
        "author_tag_quest", "author_tag_rpg", "author_tag_pvp", "author_tag_social", "author_tag_japan"]
PAGES = 10          # pages of 100 per sort / tag


def clean(text):
    """A name or tag as one piece of a tab-separated line."""
    if text is None: return ""
    return " ".join(str(text).replace("\t", " ").replace("\r", " ").replace("\n", " ").split())


def to_line(w, include_adult):
    """One API world -> one line of the list, or None when it should be left out."""
    if not isinstance(w, dict): return None
    wid = clean(w.get("id"))
    if not wid.startswith("wrld_"): return None
    if w.get("releaseStatus") not in (None, "public"): return None
    tags = [t for t in (w.get("tags") or []) if isinstance(t, str)]
    if not include_adult and any(t in ADULT_TAGS for t in tags): return None

    plat = 0
    for p in (w.get("unityPackages") or []):
        name = (p.get("platform") or "") if isinstance(p, dict) else ""
        if name == "standalonewindows": plat |= 1
        elif name == "android": plat |= 2
        elif name == "ios": plat |= 4
    if plat == 0: plat = 1          # the list API sometimes leaves the packages out; every world has a PC build

    shown = []
    for t in tags:
        if t.startswith("author_tag_"): shown.append(clean(t[len("author_tag_"):]).replace(",", " "))
        elif t.startswith("content_"): shown.append(clean(t[len("content_"):]).replace(",", " "))
    name = clean(w.get("name"))
    if not name: return None
    return "\t".join([wid, name, clean(w.get("authorName")), str(int(w.get("visits") or 0)),
                      str(int(w.get("favorites") or 0)), str(plat), ",".join(x for x in shown if x)])


def load():
    """The list already on disk, as {id: line}."""
    have = {}
    if not os.path.exists(OUT): return have
    for line in io.open(OUT, encoding="utf-8").read().split("\n"):
        if not line or line.startswith("#"): continue
        parts = line.split("\t")
        if len(parts) == 7 and parts[0].startswith("wrld_"): have[parts[0]] = line
    return have


def save(have):
    def visits(line):
        try: return int(line.split("\t")[3])
        except ValueError: return 0
    lines = sorted(have.values(), key=visits, reverse=True)
    head = "#tohk-world-index\t1\t%d\t%s" % (len(lines), datetime.date.today().isoformat())
    tmp = OUT + ".tmp"
    with io.open(tmp, "w", encoding="utf-8", newline="\n") as f:
        f.write(head + "\n" + "\n".join(lines) + "\n")
    os.replace(tmp, OUT)


def ask(params, cookie, agent):
    url = API + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": agent, "Cookie": "auth=" + cookie, "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=40) as r:
        return json.loads(r.read().decode("utf-8"))


def plan():
    """Every request this collector knows how to make, in order."""
    jobs = []
    for page in range(PAGES):
        for s in SORTS:
            jobs.append({"n": 100, "offset": page * 100, "sort": s, "order": "descending", "releaseStatus": "public"})
    for page in range(PAGES):
        for t in TAGS:
            jobs.append({"n": 100, "offset": page * 100, "sort": "popularity", "order": "descending", "releaseStatus": "public", "tag": t})
    return jobs


def selftest():
    sample = [
        {"id": "wrld_00000000-0000-0000-0000-000000000001", "name": "Test\tWorld\nOne", "authorName": "Someone", "visits": 1200,
         "favorites": 30, "releaseStatus": "public", "tags": ["author_tag_game", "author_tag_chill"],
         "unityPackages": [{"platform": "standalonewindows"}, {"platform": "android"}]},
        {"id": "wrld_00000000-0000-0000-0000-000000000002", "name": "Grown Ups", "authorName": "X", "visits": 99999,
         "favorites": 1, "releaseStatus": "public", "tags": ["content_sex"], "unityPackages": [{"platform": "standalonewindows"}]},
        {"id": "wrld_00000000-0000-0000-0000-000000000003", "name": "Private", "authorName": "X", "releaseStatus": "private", "tags": []},
        {"id": "nope", "name": "Bad id"},
    ]
    lines = [to_line(w, False) for w in sample]
    assert lines[0] == "wrld_00000000-0000-0000-0000-000000000001\tTest World One\tSomeone\t1200\t30\t3\tgame,chill", lines[0]
    assert lines[1] is None and lines[2] is None and lines[3] is None, lines[1:]
    assert to_line(sample[1], True).endswith("\t1\tsex")
    print("selftest passed:", lines[0].replace("\t", " | "))


def main():
    ap = argparse.ArgumentParser(description="Collect public VRChat worlds into worlds.txt")
    ap.add_argument("--contact", help="an email or Discord name to identify these requests to VRChat")
    ap.add_argument("--requests", type=int, default=60)
    ap.add_argument("--delay", type=float, default=60.0)
    ap.add_argument("--include-adult", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest: selftest(); return

    if not a.contact:
        print("Give a contact so VRChat knows who is asking:  --contact you@example.com"); sys.exit(1)
    cookie = os.environ.get("VRC_AUTH_COOKIE") or getpass.getpass("Paste your VRChat 'auth' cookie value (it is not shown): ").strip()
    if not cookie:
        print("No cookie given."); sys.exit(1)
    agent = "tohk.io-world-search-collector/1.0 (%s)" % a.contact

    have = load()
    print("worlds already in the list:", len(have))
    jobs = plan()
    # carry on from where the last run stopped
    state_path = os.path.join(HERE, ".collector_position")
    start = 0
    if os.path.exists(state_path):
        try: start = int(open(state_path).read().strip()) % len(jobs)
        except ValueError: start = 0

    done = 0
    at = start
    while done < a.requests:
        job = jobs[at]
        what = job.get("tag", job["sort"]) + " page " + str(job["offset"] // 100 + 1)
        try:
            got = ask(job, cookie, agent)
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", "replace")[:200]
            if e.code in (401, 403):
                print("VRChat refused (%d): %s\nThe cookie is wrong or expired, or the contact was not accepted. Stopping." % (e.code, body)); break
            if e.code == 429:
                print("VRChat says too many requests. Stopping - run again later with a longer --delay."); break
            print("%s: error %d %s - skipped" % (what, e.code, body)); got = []
        except Exception as e:
            print("%s: %s - skipped" % (what, e)); got = []

        added = 0
        for w in (got if isinstance(got, list) else []):
            line = to_line(w, a.include_adult)
            if line is None: continue
            wid = line.split("\t")[0]
            if wid not in have: added += 1
            have[wid] = line
        save(have)
        done += 1
        at = (at + 1) % len(jobs)
        open(state_path, "w").write(str(at))
        print("[%d/%d] %-34s +%d new, %d in the list" % (done, a.requests, what, added, len(have)))
        if done < a.requests: time.sleep(max(1.0, a.delay))

    print("\nSaved %d worlds to %s" % (len(have), OUT))
    print("Publish it:  git add worlds.txt && git commit -m \"Update world list\" && git push")


if __name__ == "__main__":
    main()
