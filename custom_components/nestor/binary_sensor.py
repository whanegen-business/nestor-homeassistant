"""Binary sensors for Nestor integration."""
from __future__ import annotations

from datetime import date, datetime
from typing import Any

from homeassistant.components.binary_sensor import BinarySensorEntity, BinarySensorDeviceClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import NestorCoordinator


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator: NestorCoordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    async_add_entities([NestorUrgentExpiryBinarySensor(coordinator)])


def _parse_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).date()
    except (ValueError, AttributeError):
        return None


class NestorUrgentExpiryBinarySensor(CoordinatorEntity, BinarySensorEntity):
    _attr_name = "Nestor péremption urgente"
    _attr_unique_id = "nestor_peremption_urgente"
    _attr_device_class = BinarySensorDeviceClass.PROBLEM
    _attr_icon = "mdi:alert-circle"

    def __init__(self, coordinator: NestorCoordinator) -> None:
        super().__init__(coordinator)

    @property
    def is_on(self) -> bool:
        today = date.today()
        for item in self.coordinator.data.get("inventory_items", []):
            units = item.get("units", [])
            if not isinstance(units, list):
                continue
            for unit in units:
                if not isinstance(unit, dict):
                    continue
                exp = _parse_date(unit.get("expiryDate") or unit.get("expiry_date"))
                if exp is not None and (exp - today).days <= 1:
                    return True
        return False

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        today = date.today()
        urgent = []
        for item in self.coordinator.data.get("inventory_items", []):
            units = item.get("units", [])
            if not isinstance(units, list):
                continue
            for unit in units:
                if not isinstance(unit, dict):
                    continue
                exp = _parse_date(unit.get("expiryDate") or unit.get("expiry_date"))
                if exp is not None and (exp - today).days <= 1:
                    urgent.append({"nom": item.get("name"), "date": exp.isoformat()})
        return {"produits_urgents": urgent}
