#!/usr/bin/env python3
"""Price-level alert poller for OSRS Trader.

Reads watchlist.json, polls the OSRS wiki real-time prices API once, and pushes
an ntfy notification when an item crosses its threshold. State (last-fired
times) lives in state.json, committed back by the Actions workflow.

Trigger semantics:
- direction "below" (buy alert): fires when insta-buy (latest `high`) <= threshold
  AND the 1h volume-weighted avgHighPrice also <= threshold (flash-wick filter;
  if the 1h avg is null - no trades that hour - the spot price alone decides).
- direction "above" (exit alert): mirrored on insta-sell (latest `low`) / avgLowPrice.
- After firing, an alert is muted for REARM_HOURS, then re-arms automatically.
- Optional "expires" (YYYY-MM-DD) retires an alert.

Env: NTFY_TOPIC (required to push; without it, dry-run prints only).
     TEST_PING (any non-empty value): send a wiring-test notification and exit.
"""

import json
import os
import urllib.request
from datetime import datetime, timedelta, timezone

API_BASE = "https://prices.runescape.wiki/api/v1/osrs"
USER_AGENT = "osrs-price-watch alerts (github.com/Mango-Punch/osrs-price-watch)"
REARM_HOURS = 24


def fetch(path):
    req = urllib.request.Request(API_BASE + path, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)["data"]


def push(topic, title, message, item_id):
    req = urllib.request.Request(
        f"https://ntfy.sh/{topic}",
        data=message.encode(),
        headers={
            "User-Agent": USER_AGENT,
            "Title": title,
            "Priority": "high",
            "Tags": "moneybag",
            "Click": f"https://prices.runescape.wiki/osrs/item/{item_id}",
        },
    )
    urllib.request.urlopen(req, timeout=30)


def main():
    topic = os.environ.get("NTFY_TOPIC", "")

    if os.environ.get("TEST_PING"):
        if not topic:
            raise SystemExit("TEST_PING set but no NTFY_TOPIC")
        push(topic, "PRICE ALERT test", "Test ping from osrs-price-watch - wiring OK.", "29684")
        print("test ping sent")
        return

    watchlist = json.load(open("watchlist.json"))
    state = json.load(open("state.json")) if os.path.exists("state.json") else {}
    now = datetime.now(timezone.utc)

    latest = fetch("/latest")
    hourly = fetch("/1h")

    for w in watchlist:
        iid = str(w["item_id"])
        key = f"{iid}:{w['direction']}:{w['threshold']}"

        if w.get("expires") and now.date().isoformat() > w["expires"]:
            print(f"skip {key}: expired {w['expires']}")
            continue
        last = state.get(key, {}).get("last_fired")
        if last and now - datetime.fromisoformat(last) < timedelta(hours=REARM_HOURS):
            print(f"mute {key}: fired {last}")
            continue

        li = latest.get(iid) or {}
        hi = hourly.get(iid) or {}
        if w["direction"] == "below":
            spot = li.get("high")  # insta-buy: the price a buy fills at
            avg = hi.get("avgHighPrice")
            hit = spot is not None and spot <= w["threshold"] and (avg is None or avg <= w["threshold"])
            arrow = "<="
        else:
            spot = li.get("low")  # insta-sell: the price a sell fills at
            avg = hi.get("avgLowPrice")
            hit = spot is not None and spot >= w["threshold"] and (avg is None or avg >= w["threshold"])
            arrow = ">="

        if hit:
            title = f"PRICE ALERT: {w['name']} {arrow} {w['threshold']:,} gp"
            avg_txt = f"; 1h avg {avg:,} gp" if avg is not None else ""
            msg = f"{w['name']} at {spot:,} gp (threshold {arrow} {w['threshold']:,}{avg_txt})\n"
            if w.get("note"):
                msg += f"Note: {w['note']}\n"
            msg += f"Re-arms in {REARM_HOURS}h - edit watchlist.json to change/disable."
            print(f"FIRE {key}: spot={spot} avg={avg}")
            if topic:
                push(topic, title, msg, iid)
            state[key] = {"last_fired": now.isoformat(), "spot": spot}
        else:
            print(f"ok   {key}: spot={spot} avg={avg}")

    with open("state.json", "w") as f:
        json.dump(state, f, indent=2)
        f.write("\n")


if __name__ == "__main__":
    main()
