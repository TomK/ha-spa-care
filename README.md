# Spa Care — Home Assistant Integration

Turn weekly bromine test-strip readings into ranked treatment recommendations
with proactive nudges. Bromine system only at the moment (TB / pH / TA / CH);
litres for volume.

## Install

Via HACS: add this repo as a Custom Repository (type: Integration), then
install **Spa Care** from HACS and restart Home Assistant.

## Configure

`Settings → Devices & Services → Add Integration → Spa Care`. The config
flow asks for a name (so multiple spas can be told apart) and the tub
volume in litres. Default target ranges and the full product list are
applied automatically and can be tuned later in the integration's options
(when implemented) or by editing the source.

Add the integration once per tub. Each instance gets its own device with
the chosen name, isolated state (last reading, doses, suppressions), and
its own set of entities prefixed by the spa name.

## What it gives you

Once configured, the **Spa Care** device exposes:

- **Four editable readings**: Total Bromine, pH, Total Alkalinity, Calcium
  Hardness. Tap a value, type the new reading from your strip, save. The
  integration logs a partial reading and merges it with the previously
  known values, so you can update one at a time without losing the rest.
- **`Recommended Action`** sensor: shows everything you need to add right
  now, joined as a single line on the device card and exposed as a clean
  list of strings in the `actions` state attribute. Ordered TB → pH → TA →
  CH (sanitation first, comfort second, slow problems last).
- **`Log Recommended Doses`** button: one-tap shortcut that iterates the
  full action list and logs each item as a `Dose`, kicking off the post-dose
  retest cycle. No-op when there's nothing to dose.
- **`Test Due`** binary sensor: on whenever you should go test the spa,
  for either of two reasons exposed in the `reasons` state attribute:
  - `routine` — no reading in 5 days
  - `post_dose` — you dosed something reading-driven 2 h ago and haven't
    retested
- **`Next Retest At`** timestamp sensor: when the post-dose retest is
  predicted to fire (HA renders this as relative time, e.g. "in 1 h 23 m").
- **Per-reading `*_out_of_range` binary sensors** (TB, pH, TA, CH).
- **`Last Test Age`** sensor: minutes since your last reading.

## Custom Lovelace card (optional)

A vanilla-JS card that drives the workflow from a single dashboard tile
ships in [`dashboard/`](dashboard/). It pulls all entities from a
`device_id` you configure, so it works with multiple spas. See
[`dashboard/README.md`](dashboard/README.md) for installation.

## Day-to-day workflow

1. Test the water with your strip.
2. Tap each of the four reading entities on the Spa Care device card and
   enter the values from the strip.
3. Read what `Recommended Action` says.
4. Physically add the chemicals.
5. Tap **Log Recommended Doses**.
6. Two hours later `Test Due` flips on (`reason: post_dose`); retest, repeat.

If you'd rather log doses precisely (e.g. you added 45 g instead of the
recommended 50 g), call the `spa_care.log_dose` service directly from
Developer Tools → Actions, where the product field is a dropdown of the
13 supported products.

## Why are recommended doses lower than the textbook calculation?

Every recommended dose is **capped at 75 % of the raw chemistry-table
amount** before rounding. So if the textbook says "60 g of brominating
granules to raise TB from 2.0 → 4.0 ppm in 1500 L", you'll be told to add
**45 g**.

This is deliberate. The dose-factor constants are starting estimates from
product datasheets, water temperature meaningfully affects absorption,
your colour strip reads to roughly ±0.5 ppm at best, and the spa pack's
filter cycle changes how quickly chemicals distribute. Under-shooting and
topping up converges on the right answer; over-shooting means waiting for
natural decay (or in the worst case, draining and refilling).

After a few weeks of use you'll see whether the recommendations land
where predicted. If they're consistently too low, raise the `cap`
parameter in `domain/chemistry.py` (currently `0.75`) toward `0.85` or
`0.9`. If they're too high, lower it.

## Routing nudges

Every nudge fires an HA event called `spa_care.nudge` with a payload like:

```json
{
  "category": "out_of_range",
  "subject": "tb",
  "message": "TB = 2.0 is low; target 3.0–5.0. Suggested: 50g of brominating_granules.",
  "product": "brominating_granules",
  "amount": 50.0
}
```

Wire one HA automation to catch those events and route them to your
notify service of choice (mobile push, Slack, dashboard banner, …).
A starter automation lives in [`docs/example-automation.yaml`](docs/example-automation.yaml).

The integration also creates a `persistent_notification` for every nudge,
so you'll see them in the HA notifications panel even without an
automation set up.

## Honesty

This is a personal-scale integration, not a professional pool/spa
controller. The chemistry math is conservative-textbook; the dose-factor
constants are sourced from common UK product instructions and are easy
to tune in `domain/chemistry.py` and `domain/products.py` once you see
how your particular tub responds.

The integration does not replace knowing how your spa works or how to
read a test strip. It tracks state, computes a sensible starting dose,
and reminds you to test on cadence.
