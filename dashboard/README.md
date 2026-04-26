# Spa Care Lovelace Card

Drop-in card for the [Spa Care integration](../README.md). One file,
no build step.

## Install

1. Copy `spa-care-card.js` into your HA `config/www/` folder.
2. Add it as a Lovelace resource — Settings → Dashboards → ⋮ →
   Resources → **Add Resource**:
   - URL: `/local/spa-care-card.js`
   - Type: **JavaScript Module**
3. Find your spa's device_id: Settings → Devices & Services → Spa Care
   → click the device → URL contains `/devices/<device_id>`. Copy that.
4. Add to a dashboard via Manual card YAML:

   ```yaml
   type: 'custom:spa-care-card'
   device_id: <paste from step 3>
   ```

## Multiple spas

Install the integration once per tub, then add one card per device.

## Troubleshooting

- "Configure a device" → check the `device_id` exists under Spa Care.
- Card doesn't appear in card-picker → confirm the resource was added
  with type "JavaScript Module" and reload the browser.
