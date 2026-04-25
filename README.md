# Spa Care — Home Assistant Integration

Turn weekly test-strip readings into ranked treatment recommendations.
Bromine system support (TB / pH / TA / CH); litres for volume.

## Install

Via HACS: add this repo as a Custom Repository (type: Integration), then
install **Spa Care** from HACS and restart Home Assistant.

## Configure

`Settings → Devices & Services → Add Integration → Spa Care`. Walks you
through tub volume, products on hand, and target ranges.

## Routing nudges

Every recommendation fires a `spa_care.nudge` event. Wire one automation
to route those events to your notify service of choice. Example automation
in `docs/example-automation.yaml`.
