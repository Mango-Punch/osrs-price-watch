# osrs-price-watch

Price-level alerts for OSRS Grand Exchange items. Sibling of
[osrs-news-watch](https://github.com/Mango-Punch/osrs-news-watch) — same shape:
GitHub Actions cron → poll a public API → push to ntfy.

Polls the [OSRS wiki real-time prices API](https://prices.runescape.wiki) hourly
against `watchlist.json` and pings the phone when an item crosses its threshold.
Alert only, never auto-trade.

> Public repo by design (free unlimited Actions minutes). The watchlist is
> visible — price levels here are not secrets, the ntfy topic is (Actions
> secret `NTFY_TOPIC`, never committed).

## How it works

- **Cadence:** hourly cron (GitHub best-effort — expect 60–90 min in practice),
  plus manual `workflow_dispatch`.
- **Trigger:** `below` alerts fire on insta-buy (`latest.high`) ≤ threshold,
  confirmed by the 1h volume-weighted `avgHighPrice` (flash-wick filter; a null
  1h avg means the spot price decides alone). `above` alerts mirror on
  insta-sell / `avgLowPrice`.
- **Re-arm:** after firing, an alert mutes for 24h, then re-arms automatically.
  Edit or remove the entry to stop it permanently.
- **State:** `state.json` (last-fired per alert) is committed back by the
  workflow.

## Add / change an alert

Edit `watchlist.json`:

```json
{
  "item_id": 29684,
  "name": "Guthixian temple teleport",
  "direction": "below",
  "threshold": 8000,
  "note": "shows up in the notification",
  "added": "2026-06-10",
  "expires": null
}
```

- `item_id` — the OSRS item id (check https://prices.runescape.wiki/osrs/item/(id)).
- `direction` — `below` (buy alert, insta-buy side) or `above` (exit alert, insta-sell side).
- `expires` — optional `YYYY-MM-DD`; alert auto-retires after this date.

## Operate

- **Test the wiring:** Actions → poll-prices → Run workflow → set `test_ping`
  to anything → sends a test notification.
- **Pause everything:** Actions → poll-prices → ⋯ → Disable workflow.
- **Force a check now:** Run workflow with `test_ping` empty.
- **Change cadence:** edit the cron in `.github/workflows/poll.yml`.
