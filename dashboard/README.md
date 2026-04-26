# Spa Care Lovelace Card

The card ships **inside the integration** and registers itself
automatically — there's nothing to copy and no Lovelace resource to
add manually.

## How it works

When the integration loads, it serves the bundled
`custom_components/spa_care/spa-care-card.js` at the URL
`/spa_care/spa-care-card.js` and calls `add_extra_js_url(...)` so the
JS module is loaded on every Lovelace dashboard. The card registers
itself as `custom:spa-care-card`. Idempotent across config-entry
reloads.

## Add the card to a dashboard

1. After installing (or reloading) the integration, hard-refresh the
   browser (Cmd-Shift-R / Ctrl-Shift-R).
2. On a dashboard in edit mode → **+ Add Card → search "Spa Care"**.
   The visual editor opens with a device dropdown filtered to your
   spa_care devices — pick one and save. No YAML needed.

   *Or, if you prefer YAML, "+ Add Card → Manual" with:*
   ```yaml
   type: 'custom:spa-care-card'
   device_id: <your spa's device id>
   ```
   *(Find the device id at Settings → Devices & Services → Spa Care →
   click the device → URL contains `/devices/<device_id>`.)*

## What the card has

- Device-named header + status line (driven by `binary_sensor.test_due`).
- Four editable reading rows (TB / pH / TA / Hardness) with ✓/⚠️ badges
  reflecting `*_out_of_range` binary sensors. Bounds enforced from the
  number-entity's `min`/`max`.
- Recommendations list (chemical doses *and* advisories) sourced from
  `sensor.recommended_action`'s `actions` attribute.
- Primary **Log Recommended Doses** button + secondary **+ Log dose**
  with an inline form for off-recommendation chemicals (unit auto-flips
  g/ml by product, typical-for-this-tub amount pre-filled where known).
- **Maintenance** section with **Mark filter cleaned** / **Mark surfaces
  wiped** buttons → calls `spa_care.log_maintenance`.
- Retest countdown when a post-dose retest window is open.

## Multiple spas

Install the integration once per tub, then add one card per device.

## Migrating from the old manual install

If you set the card up manually before this auto-registration landed,
you'll have leftover bits to clean up:

1. Delete the file at `/config/www/spa-care-card.js` (no longer used).
2. **Settings → Dashboards → ⋮ → Resources** → remove the
   `/local/spa-care-card.js` resource entry.
3. Restart HA. The card will re-appear at the new URL automatically and
   any `custom:spa-care-card` references on your dashboards keep working
   (the element name is the same).

## Troubleshooting

- *"Configure a device"* → the `device_id` doesn't resolve. Re-pick via
  the visual editor, or check that your spa_care entry is loaded.
- *"Spa Care card is incompatible…"* → the device exists but lacks the
  expected entities. Reload the integration entry; if entities are
  missing, the integration may have failed setup (check HA logs).
- Card doesn't appear in card-picker → hard-refresh the browser. If the
  HA log shows `failed to register frontend card`, check that the JS
  file ships inside `custom_components/spa_care/` (HACS only ships that
  folder).
