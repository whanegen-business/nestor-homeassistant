"""Sensors for Nestor integration."""
from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_EXPIRY_THRESHOLD_DAYS, DEFAULT_EXPIRY_THRESHOLD_DAYS, DOMAIN
from .coordinator import NestorCoordinator


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator: NestorCoordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    threshold = int(entry.options.get(CONF_EXPIRY_THRESHOLD_DAYS, DEFAULT_EXPIRY_THRESHOLD_DAYS))

    async_add_entities(
        [
            NestorShoppingItemsSensor(coordinator),
            NestorInventoryTotalSensor(coordinator),
            NestorExpiringItemsSensor(coordinator, threshold),
            NestorRoutinesDueSensor(coordinator),
            NestorNextExpiryDateSensor(coordinator),
        ]
    )


def _parse_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).date()
    except (ValueError, AttributeError):
        return None


def _days_until(d: date) -> int:
    return (d - date.today()).days


class NestorShoppingItemsSensor(CoordinatorEntity, SensorEntity):
    _attr_name = "Nestor courses à acheter"
    _attr_unique_id = "nestor_courses_a_acheter"
    _attr_icon = "mdi:cart"
    _attr_native_unit_of_measurement = "articles"

    def __init__(self, coordinator: NestorCoordinator) -> None:
        super().__init__(coordinator)

    @property
    def native_value(self) -> int:
        items = self.coordinator.data.get("shopping_items", [])
        return sum(1 for i in items if not i.get("bought", False))

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        items = self.coordinator.data.get("shopping_items", [])
        return {
            "items": [i.get("name") for i in items if not i.get("bought", False)]
        }


class NestorInventoryTotalSensor(CoordinatorEntity, SensorEntity):
    _attr_name = "Nestor inventaire total"
    _attr_unique_id = "nestor_inventaire_total"
    _attr_icon = "mdi:package-variant-closed"
    _attr_native_unit_of_measurement = "produits"

    def __init__(self, coordinator: NestorCoordinator) -> None:
        super().__init__(coordinator)

    @property
    def native_value(self) -> int:
        return len(self.coordinator.data.get("inventory_items", []))

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        items = self.coordinator.data.get("inventory_items", [])
        by_location: dict[str, int] = {}
        for item in items:
            loc = item.get("location") or "inconnu"
            by_location[loc] = by_location.get(loc, 0) + 1
        return {"par_emplacement": by_location}


class NestorExpiringItemsSensor(CoordinatorEntity, SensorEntity):
    _attr_name = "Nestor péremptions proches"
    _attr_unique_id = "nestor_peremptions_proches"
    _attr_icon = "mdi:calendar-alert"
    _attr_native_unit_of_measurement = "unités"

    def __init__(self, coordinator: NestorCoordinator, threshold: int) -> None:
        super().__init__(coordinator)
        self._threshold = threshold

    def _expiring_units(self) -> list[dict]:
        result = []
        for item in self.coordinator.data.get("inventory_items", []):
            units = item.get("units", [])
            if not isinstance(units, list):
                continue
            for unit in units:
                if not isinstance(unit, dict):
                    continue
                exp = _parse_date(unit.get("expiryDate") or unit.get("expiry_date"))
                if exp is None:
                    continue
                days = _days_until(exp)
                if days <= self._threshold:
                    result.append({
                        "nom": item.get("name"),
                        "date": exp.isoformat(),
                        "jours_restants": days,
                    })
        return sorted(result, key=lambda x: x["jours_restants"])

    @property
    def native_value(self) -> int:
        return len(self._expiring_units())

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {"unités": self._expiring_units()}


class NestorRoutinesDueSensor(CoordinatorEntity, SensorEntity):
    _attr_name = "Nestor routines à faire"
    _attr_unique_id = "nestor_routines_a_faire"
    _attr_icon = "mdi:clipboard-check-outline"
    _attr_native_unit_of_measurement = "routines"

    def __init__(self, coordinator: NestorCoordinator) -> None:
        super().__init__(coordinator)

    def _due_routines(self) -> list[dict]:
        result = []
        today = date.today()
        for r in self.coordinator.data.get("routines", []):
            due = _parse_date(r.get("nextDueDate") or r.get("next_due_date"))
            if due is not None and due <= today:
                result.append({"nom": r.get("name"), "due_date": due.isoformat()})
        return result

    @property
    def native_value(self) -> int:
        return len(self._due_routines())

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {"routines": self._due_routines()}


class NestorNextExpiryDateSensor(CoordinatorEntity, SensorEntity):
    _attr_name = "Nestor prochaine péremption"
    _attr_unique_id = "nestor_prochaine_peremption"
    _attr_icon = "mdi:calendar-clock"

    def __init__(self, coordinator: NestorCoordinator) -> None:
        super().__init__(coordinator)
        self._next: tuple[str | None, str | None] = (None, None)

    def _find_next(self) -> tuple[str | None, str | None]:
        best_date: date | None = None
        best_name: str | None = None
        for item in self.coordinator.data.get("inventory_items", []):
            units = item.get("units", [])
            if not isinstance(units, list):
                continue
            for unit in units:
                if not isinstance(unit, dict):
                    continue
                exp = _parse_date(unit.get("expiryDate") or unit.get("expiry_date"))
                if exp is None:
                    continue
                if best_date is None or exp < best_date:
                    best_date = exp
                    best_name = item.get("name")
        return (best_date.isoformat() if best_date else None, best_name)

    @property
    def native_value(self) -> str | None:
        date_str, _ = self._find_next()
        return date_str

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        _, name = self._find_next()
        return {"produit": name}
