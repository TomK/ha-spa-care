"""DataUpdateCoordinator: state, persistence, rule dispatch."""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import DOMAIN, STORAGE_KEY, STORAGE_VERSION
from .domain.models import Action, Dose, Reading, TargetRange
from .domain.recommendations import DEFAULT_TARGETS
from .domain.rules import RuleState, evaluate_rules

_LOGGER = logging.getLogger(__name__)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class SpaCareCoordinator(DataUpdateCoordinator[None]):
    """Owns spa_care state and dispatches rule-engine Actions."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry_id: str,
        volume_l: float,
        targets: dict[str, TargetRange] | None,
        store: Store | None = None,
    ) -> None:
        super().__init__(hass, logger=_LOGGER, name=DOMAIN)
        self.hass = hass
        self._entry_id = entry_id
        self.volume_l = volume_l
        self.targets = targets or DEFAULT_TARGETS
        self._store = store or Store(hass, STORAGE_VERSION, f"{STORAGE_KEY}_{entry_id}")
        self.last_reading: Reading | None = None
        self.doses: list[Dose] = []
        self.suppressions: dict[tuple[str, str], datetime] = {}

    async def async_initialize(self) -> None:
        data = await self._store.async_load()
        if not data:
            return
        last = data.get("last_reading")
        if last:
            self.last_reading = Reading(
                timestamp=datetime.fromisoformat(last["timestamp"]),
                total_bromine=last.get("total_bromine"),
                ph=last.get("ph"),
                total_alkalinity=last.get("total_alkalinity"),
                calcium_hardness=last.get("calcium_hardness"),
            )
        self.doses = [
            Dose(
                timestamp=datetime.fromisoformat(d["timestamp"]),
                product_key=d["product_key"],
                amount=d["amount"],
            )
            for d in data.get("doses", [])
        ]
        self.suppressions = {
            (k.split("|")[0], k.split("|")[1]): datetime.fromisoformat(v)
            for k, v in data.get("suppressions", {}).items()
        }

    async def async_log_reading(self, reading: Reading) -> None:
        self.last_reading = reading
        self._dispatch(trigger="log_reading", now=_utcnow())
        await self._persist()  # after dispatch — captures suppressions added during dispatch
        self.async_update_listeners()

    async def async_log_dose(
        self,
        *,
        product_key: str,
        amount: float,
        when: datetime | None = None,
    ) -> None:
        self.doses.append(Dose(
            timestamp=when or _utcnow(),
            product_key=product_key,
            amount=amount,
        ))
        self._dispatch(trigger="log_dose", now=_utcnow())
        await self._persist()  # after dispatch — captures suppressions added during dispatch
        self.async_update_listeners()

    async def async_hourly_tick(self) -> None:
        self._dispatch(trigger="hourly", now=_utcnow())
        await self._persist()
        self.async_update_listeners()

    def _dispatch(self, *, trigger: str, now: datetime) -> None:
        state = RuleState(
            targets=self.targets,
            volume_l=self.volume_l,
            last_reading=self.last_reading,
            doses=tuple(self.doses),
            suppressions=self.suppressions,
        )
        actions = evaluate_rules(state, now=now, trigger=trigger)
        for action in actions:
            self._apply(action, now)

    def _apply(self, action: Action, now: datetime) -> None:
        if action.kind == "fire_event":
            category = action.payload["category"]
            subject = action.payload["subject"]
            # Record suppression before firing — accept silent loss on a broken
            # event handler rather than risk a tight retry loop.
            self.suppressions[(category, subject)] = now
            self.hass.bus.async_fire(f"{DOMAIN}.nudge", action.payload)
            # Persistent notification, fire-and-forget.
            self.hass.async_create_task(self._notify(action.payload["message"]))
        # set_entity / create_notification kinds reserved for future Actions.

    async def _notify(self, message: str) -> None:
        try:
            from homeassistant.components.persistent_notification import async_create
            async_create(self.hass, message, title="Spa Care")
        except Exception:
            _LOGGER.exception("spa_care: failed to create persistent notification")

    async def _persist(self) -> None:
        payload = {
            "last_reading": (
                {
                    "timestamp": self.last_reading.timestamp.isoformat(),
                    "total_bromine": self.last_reading.total_bromine,
                    "ph": self.last_reading.ph,
                    "total_alkalinity": self.last_reading.total_alkalinity,
                    "calcium_hardness": self.last_reading.calcium_hardness,
                }
                if self.last_reading
                else None
            ),
            "doses": [
                {
                    "timestamp": d.timestamp.isoformat(),
                    "product_key": d.product_key,
                    "amount": d.amount,
                }
                for d in self.doses
            ],
            "suppressions": {
                f"{cat}|{subj}": ts.isoformat()
                for (cat, subj), ts in self.suppressions.items()
            },
        }
        await self._store.async_save(payload)
