"""DataUpdateCoordinator for Nestor — polls Firestore every 3 minutes."""
from __future__ import annotations

import logging
from datetime import timedelta

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN, UPDATE_INTERVAL_MINUTES
from .firestore import FirestoreClient

_LOGGER = logging.getLogger(__name__)


class NestorCoordinator(DataUpdateCoordinator):
    def __init__(self, hass: HomeAssistant, client: FirestoreClient, household_id: str) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(minutes=UPDATE_INTERVAL_MINUTES),
        )
        self._client = client
        self._household_id = household_id

    async def _async_update_data(self) -> dict:
        base = f"households/{self._household_id}"
        try:
            inventory_items = await self._client.list_collection(f"{base}/inventoryItems")
            shopping_items = await self._client.list_collection(f"{base}/shoppingItems")
            routines = await self._client.list_collection(f"{base}/routines")
        except Exception as err:
            raise UpdateFailed(f"Error communicating with Firestore: {err}") from err

        _LOGGER.debug(
            "Nestor fetched %d inventory items, %d shopping items, %d routines",
            len(inventory_items),
            len(shopping_items),
            len(routines),
        )

        return {
            "inventory_items": inventory_items,
            "shopping_items": shopping_items,
            "routines": routines,
        }
