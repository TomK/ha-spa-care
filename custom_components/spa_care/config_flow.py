"""Config flow — single-step MVP. Targets and products use defaults; can
be overridden via options flow in a follow-up.
"""

from __future__ import annotations

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResult

from .const import CONF_NAME, CONF_VOLUME_L, DOMAIN

_SCHEMA = vol.Schema({
    vol.Required(CONF_NAME, default="Spa"): str,
    vol.Required(CONF_VOLUME_L, default=1500.0): vol.Coerce(float),
})


class SpaCareConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input: dict | None = None) -> FlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            name = (user_input.get(CONF_NAME) or "").strip()
            volume = user_input.get(CONF_VOLUME_L, 0)
            if not name:
                errors["base"] = "invalid_name"
            elif volume <= 0:
                errors["base"] = "invalid_volume"
            else:
                return self.async_create_entry(
                    title=name,
                    data={CONF_NAME: name, CONF_VOLUME_L: volume},
                )
        return self.async_show_form(step_id="user", data_schema=_SCHEMA, errors=errors)
