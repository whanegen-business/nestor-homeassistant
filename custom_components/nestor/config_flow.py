"""Config flow for Nestor integration."""
from __future__ import annotations

import json
import logging
from typing import Any

import aiohttp
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.selector import (
    TextSelector,
    TextSelectorConfig,
    TextSelectorType,
)

from .const import CONF_HOUSEHOLD_ID, CONF_SERVICE_ACCOUNT_JSON, DOMAIN
from .firestore import FirestoreClient

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_SERVICE_ACCOUNT_JSON): TextSelector(
            TextSelectorConfig(type=TextSelectorType.TEXT, multiline=True)
        ),
        vol.Required(CONF_HOUSEHOLD_ID): str,
    }
)


async def _validate_connection(hass: HomeAssistant, data: dict) -> dict:
    """Parse the SA key and verify we can reach the household document."""
    try:
        sa = json.loads(data[CONF_SERVICE_ACCOUNT_JSON])
    except json.JSONDecodeError as err:
        raise InvalidServiceAccountJson from err

    required = {"client_email", "private_key", "token_uri", "project_id"}
    if not required.issubset(sa.keys()):
        raise InvalidServiceAccountJson

    household_id = data[CONF_HOUSEHOLD_ID].strip()

    async with aiohttp.ClientSession() as session:
        client = FirestoreClient(session, sa)
        try:
            await client.get_document(f"households/{household_id}")
        except aiohttp.ClientResponseError as err:
            if err.status == 401:
                raise InvalidAuth from err
            if err.status == 404:
                raise HouseholdNotFound from err
            raise CannotConnect from err
        except Exception as err:
            raise CannotConnect from err

    return {"project_id": sa["project_id"], "household_id": household_id}


class NestorConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None):
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                info = await _validate_connection(self.hass, user_input)
            except InvalidServiceAccountJson:
                errors["base"] = "invalid_service_account"
            except InvalidAuth:
                errors["base"] = "invalid_auth"
            except HouseholdNotFound:
                errors["base"] = "household_not_found"
            except CannotConnect:
                errors["base"] = "cannot_connect"
            else:
                await self.async_set_unique_id(
                    f"{info['project_id']}_{info['household_id']}"
                )
                self._abort_if_unique_id_configured()

                return self.async_create_entry(
                    title=f"Nestor — {info['household_id']}",
                    data={
                        CONF_SERVICE_ACCOUNT_JSON: user_input[CONF_SERVICE_ACCOUNT_JSON],
                        CONF_HOUSEHOLD_ID: info["household_id"],
                    },
                )

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
        )


class InvalidServiceAccountJson(HomeAssistantError):
    pass


class InvalidAuth(HomeAssistantError):
    pass


class HouseholdNotFound(HomeAssistantError):
    pass


class CannotConnect(HomeAssistantError):
    pass
