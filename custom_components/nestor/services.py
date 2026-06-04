"""Service implementations for Nestor integration."""
from __future__ import annotations

import logging
from datetime import datetime, timezone

import voluptuous as vol

from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import config_validation as cv

from .const import DOMAIN
from .firestore import FirestoreClient

_LOGGER = logging.getLogger(__name__)

SCHEMA_ADD_SHOPPING = vol.Schema(
    {
        vol.Required("name"): cv.string,
        vol.Optional("quantity", default=""): cv.string,
    }
)

SCHEMA_NAME_ONLY = vol.Schema({vol.Required("name"): cv.string})


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _get_entry_data(hass: HomeAssistant) -> tuple[FirestoreClient, str] | None:
    domain_data = hass.data.get(DOMAIN, {})
    if not domain_data:
        return None
    entry_data = next(iter(domain_data.values()))
    return entry_data["client"], entry_data["coordinator"]._household_id


async def async_setup_services(hass: HomeAssistant) -> None:

    async def handle_add_to_shopping_list(call: ServiceCall) -> None:
        data = SCHEMA_ADD_SHOPPING(dict(call.data))
        result = _get_entry_data(hass)
        if result is None:
            _LOGGER.error("Nestor: no configured entry found")
            return
        client, household_id = result

        doc = {
            "name": data["name"],
            "bought": False,
            "addedBy": "homeassistant",
            "addedAt": _now_iso(),
        }
        if data["quantity"]:
            doc["quantity"] = data["quantity"]

        await client.create_document(f"households/{household_id}/shoppingItems", doc)
        _LOGGER.debug("Nestor: added '%s' to shopping list", data["name"])

        coordinator = next(iter(hass.data[DOMAIN].values()))["coordinator"]
        await coordinator.async_request_refresh()

    async def handle_mark_bought(call: ServiceCall) -> None:
        data = SCHEMA_NAME_ONLY(dict(call.data))
        result = _get_entry_data(hass)
        if result is None:
            _LOGGER.error("Nestor: no configured entry found")
            return
        client, household_id = result

        coordinator = next(iter(hass.data[DOMAIN].values()))["coordinator"]
        shopping_items = (coordinator.data or {}).get("shopping_items", [])

        target = next(
            (i for i in shopping_items if i.get("name", "").lower() == data["name"].lower() and not i.get("bought", False)),
            None,
        )
        if target is None:
            _LOGGER.warning("Nestor: item '%s' not found in shopping list", data["name"])
            return

        doc_id = target["_id"]
        patch = {"bought": True, "boughtAt": _now_iso()}
        await client.patch_document(
            f"households/{household_id}/shoppingItems/{doc_id}",
            patch,
            list(patch.keys()),
        )
        _LOGGER.debug("Nestor: marked '%s' as bought", data["name"])
        await coordinator.async_request_refresh()

    async def handle_complete_routine(call: ServiceCall) -> None:
        data = SCHEMA_NAME_ONLY(dict(call.data))
        result = _get_entry_data(hass)
        if result is None:
            _LOGGER.error("Nestor: no configured entry found")
            return
        client, household_id = result

        coordinator = next(iter(hass.data[DOMAIN].values()))["coordinator"]
        routines = (coordinator.data or {}).get("routines", [])

        target = next(
            (r for r in routines if r.get("name", "").lower() == data["name"].lower()),
            None,
        )
        if target is None:
            _LOGGER.warning("Nestor: routine '%s' not found", data["name"])
            return

        doc_id = target["_id"]
        now_iso = _now_iso()
        patch: dict = {"lastCompletedAt": now_iso}

        frequency = target.get("frequency")
        next_due = _compute_next_due(now_iso, frequency)
        if next_due:
            patch["nextDueDate"] = next_due

        await client.patch_document(
            f"households/{household_id}/routines/{doc_id}",
            patch,
            list(patch.keys()),
        )
        _LOGGER.debug("Nestor: completed routine '%s', next due: %s", data["name"], next_due)
        await coordinator.async_request_refresh()

    async def handle_refresh(call: ServiceCall) -> None:
        domain_data = hass.data.get(DOMAIN, {})
        for entry_data in domain_data.values():
            await entry_data["coordinator"].async_request_refresh()

    hass.services.async_register(DOMAIN, "add_to_shopping_list", handle_add_to_shopping_list)
    hass.services.async_register(DOMAIN, "mark_bought", handle_mark_bought)
    hass.services.async_register(DOMAIN, "complete_routine", handle_complete_routine)
    hass.services.async_register(DOMAIN, "refresh", handle_refresh)


def _compute_next_due(last_completed_iso: str, frequency: str | None) -> str | None:
    """Compute next due date from frequency string like '7d', '1m', '2w'."""
    if not frequency:
        return None
    from datetime import timedelta

    try:
        dt = datetime.fromisoformat(last_completed_iso.replace("Z", "+00:00"))
        freq = str(frequency).strip().lower()
        if freq.endswith("d"):
            delta = timedelta(days=int(freq[:-1]))
        elif freq.endswith("w"):
            delta = timedelta(weeks=int(freq[:-1]))
        elif freq.endswith("m"):
            delta = timedelta(days=int(freq[:-1]) * 30)
        else:
            return None
        return (dt + delta).isoformat().replace("+00:00", "Z")
    except (ValueError, TypeError):
        return None


async def async_unload_services(hass: HomeAssistant) -> None:
    for service in ("add_to_shopping_list", "mark_bought", "complete_routine", "refresh"):
        hass.services.async_remove(DOMAIN, service)
