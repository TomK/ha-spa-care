# Spa Care Lovelace Card

Drop-in card for the [Spa Care integration](../README.md). One file,
no build step.

## Install

1. Copy `spa-care-card.js` into your HA `config/www/` folder.
2. (You may need to enable Advanced Mode on your user profile first.)
   Add it as a Lovelace resource — **Settings → Dashboards → ⋮ →
   Resources → Add Resource**:
   - URL: `/local/spa-care-card.js`
   - Type: **JavaScript Module**
3. Hard-refresh the browser (Cmd-Shift-R / Ctrl-Shift-R).
4. On a dashboard in edit mode, **+ Add Card → search "Spa Care"**.
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

## Troubleshooting

- *"Configure a device"* → the `device_id` doesn't resolve. Re-pick via
  the visual editor, or check that your spa_care entry is loaded.
- *"Spa Care card is incompatible…"* → the device exists but lacks the
  expected entities. Reload the integration entry; if entities are
  missing, the integration may have failed setup (check HA logs).
- Card doesn't appear in card-picker → confirm the resource was added
  with type **JavaScript Module** and that you hard-refreshed the
  browser. Sometimes HA caches the old resource version aggressively;
  a one-shot fix is to edit the resource URL to add `?v=2` and save.
