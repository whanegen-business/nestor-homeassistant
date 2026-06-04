"""Nestor for Home Assistant — Firestore integration."""
from __future__ import annotations

import json
import logging

import aiohttp

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import CONF_HOUSEHOLD_ID, CONF_SERVICE_ACCOUNT_JSON, DOMAIN
from .coordinator import NestorCoordinator
from .firestore import FirestoreClient
from .services import async_setup_services, async_unload_services

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[str] = ["sensor", "binary_sensor"]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    sa = json.loads(entry.data[CONF_SERVICE_ACCOUNT_JSON])
    household_id: str = entry.data[CONF_HOUSEHOLD_ID]

    session = aiohttp.ClientSession()
    client = FirestoreClient(session, sa)

    coordinator = NestorCoordinator(hass, client, household_id)
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = {
        "coordinator": coordinator,
        "client": client,
        "session": session,
    }

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    if not hass.services.has_service(DOMAIN, "refresh"):
        await async_setup_services(hass)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        data = hass.data[DOMAIN].pop(entry.entry_id)
        await data["session"].close()
        if not hass.data.get(DOMAIN):
            await async_unload_services(hass)
    return unload_ok
