"""Provides the mammotion DataUpdateCoordinator."""

from __future__ import annotations

from dataclasses import asdict
from datetime import timedelta
from typing import TYPE_CHECKING

from bleak_retry_connector import BleakError, BleakNotFoundError
from pyluba.mammotion.devices import MammotionBaseBLEDevice, has_field
from pyluba.mammotion.devices.luba import CharacteristicMissingError
from pyluba.proto.luba_msg import LubaMsg

from homeassistant.components import bluetooth
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import LOGGER

if TYPE_CHECKING:
    from bleak.backends.device import BLEDevice

    from . import MammotionConfigEntry

MOWER_SCAN_INTERVAL = timedelta(minutes=1)


class MammotionDataUpdateCoordinator(DataUpdateCoordinator[LubaMsg]):
    """Class to manage fetching mammotion data."""

    config_entry: MammotionConfigEntry

    def __init__(
        self,
        hass: HomeAssistant,
        ble_device: BLEDevice,
    ) -> None:
        """Initialize global mammotion data updater."""
        super().__init__(
            hass=hass,
            logger=LOGGER,
            name="Mammotion Lawn Mower data",
            update_interval=MOWER_SCAN_INTERVAL,
        )
        self.device = MammotionBaseBLEDevice(ble_device)
        self.device_name = ble_device.name or "Unknown"
        self.address = ble_device.address
        self.update_failures = 0

    async def _async_update_data(self) -> LubaMsg:
        """Get data from the device."""
        if ble_device := bluetooth.async_ble_device_from_address(
            self.hass, self.address
        ):
            self.device.update_device(ble_device)
            try:
                if not has_field(self.device.luba_msg.net):
                    return await self.device.start_sync(0)
                await self.device.command("get_report_cfg")
            except (
                BleakNotFoundError,
                CharacteristicMissingError,
                BleakError,
                TimeoutError,
            ) as exc:
                self.update_failures += 1
                raise UpdateFailed(f"Updating Mammotion device failed: {exc}") from exc

            LOGGER.debug("Updated Mammotion device %s", self.device_name)
            LOGGER.debug("================= Debug Log =================")
            LOGGER.debug("Mammotion device data: %s", asdict(self.device.luba_msg))
            LOGGER.debug("==================================")

            self.update_failures = 0
            return self.device.luba_msg

        self.update_failures += 1
        raise UpdateFailed("Could not find device")
