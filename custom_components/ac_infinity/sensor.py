"""The ac_infinity sensor platform."""
from __future__ import annotations

import logging
from abc import abstractmethod
from typing import Any

from ac_infinity_ble import ACInfinityController

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)

from homeassistant.components.bluetooth.passive_update_coordinator import (
    PassiveBluetoothCoordinatorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE, UnitOfPressure, UnitOfTemperature
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from .const import DEVICE_MODEL, DOMAIN, WORK_TYPE_FROM_RAW
from .coordinator import ACInfinityDataUpdateCoordinator
from .models import ACInfinityData

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the sensor platform for AC Infinity."""
    data: ACInfinityData = hass.data[DOMAIN][entry.entry_id]
    entities: list[ACInfinitySensor] = []

    if data.device.state is None:
        _LOGGER.warning("Device state not available, skipping sensor setup")
        return

    device_type = data.device.state.type

    if device_type in [1, 6, 7, 11]:
        entities.append(TemperatureSensor(data.coordinator, data.device, entry.title))

    if device_type in [1, 7, 11]:
        entities.append(HumiditySensor(data.coordinator, data.device, entry.title))

    if data.device.state.version >= 3 and device_type in [7, 9, 11, 12]:
        entities.append(VpdSensor(data.coordinator, data.device, entry.title))

    if device_type in [6]:
        entities.append(
            TemperatureTriggerLowSensor(data.coordinator, data.device, entry.title)
        )
        entities.append(
            TemperatureTriggerHighSensor(data.coordinator, data.device, entry.title)
        )
        entities.append(WorkTypeSensor(data.coordinator, data.device, entry.title))

    async_add_entities(entities)


class ACInfinitySensor(
    PassiveBluetoothCoordinatorEntity[ACInfinityDataUpdateCoordinator], SensorEntity
):
    """Representation of AC Infinity sensor."""

    def __init__(
        self,
        coordinator: ACInfinityDataUpdateCoordinator,
        device: ACInfinityController,
        name: str,
    ) -> None:
        """Initialize an AC Infinity sensor."""
        super().__init__(coordinator)
        self._device = device
        self._name = name
        self._attr_device_info = DeviceInfo(
            name=device.name,
            model=DEVICE_MODEL.get(device.state.type, f"Unknown ({device.state.type})"),
            manufacturer="AC Infinity",
            sw_version=device.state.version,
            connections={(dr.CONNECTION_BLUETOOTH, device.address)},
        )
        self._async_update_attrs()

    @callback
    @abstractmethod
    def _async_update_attrs(self) -> None:
        """Handle updating _attr values."""

    @callback
    def _handle_coordinator_update(self, *args: Any) -> None:
        """Handle data update."""
        self._async_update_attrs()
        self.async_write_ha_state()

    async def async_added_to_hass(self) -> None:
        """Register callbacks."""
        self.async_on_remove(
            self._device.register_callback(self._handle_coordinator_update)
        )
        return await super().async_added_to_hass()


class TemperatureSensor(ACInfinitySensor):
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
    _attr_device_class = SensorDeviceClass.TEMPERATURE
    _attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def name(self) -> str:
        return f"{self._name} Temperature"

    @property
    def unique_id(self) -> str:
        """Return a unique, Home Assistant friendly identifier for this entity."""
        return f"{self._device.address}_tmp"

    @callback
    def _async_update_attrs(self) -> None:
        """Handle updating _attr values."""
        self._attr_native_value = self._device.temperature


class TemperatureTriggerLowSensor(ACInfinitySensor):
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
    _attr_device_class = SensorDeviceClass.TEMPERATURE
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    @property
    def name(self) -> str:
        return f"{self._name} Temperature Trigger Low"

    @property
    def unique_id(self) -> str:
        """Return a unique, Home Assistant friendly identifier for this entity."""
        return f"{self._device.address}_tmp_trigger_low"

    @callback
    def _async_update_attrs(self) -> None:
        """Handle updating _attr values."""
        self._attr_native_value = self._device.state.tmp_trigger_low


class TemperatureTriggerHighSensor(ACInfinitySensor):
    # NOTE: The AIRTAP T6 reports this value in Fahrenheit, unlike other temperature
    # readings which are in Celsius. This appears to be a firmware quirk.
    _attr_native_unit_of_measurement = UnitOfTemperature.FAHRENHEIT
    _attr_device_class = SensorDeviceClass.TEMPERATURE
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    @property
    def name(self) -> str:
        return f"{self._name} Temperature Trigger High"

    @property
    def unique_id(self) -> str:
        """Return a unique, Home Assistant friendly identifier for this entity."""
        return f"{self._device.address}_tmp_trigger_high"

    @callback
    def _async_update_attrs(self) -> None:
        """Handle updating _attr values."""
        self._attr_native_value = self._device.state.tmp_trigger_high


class HumiditySensor(ACInfinitySensor):
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_device_class = SensorDeviceClass.HUMIDITY
    _attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def name(self) -> str:
        return f"{self._name} Humidity"

    @property
    def unique_id(self) -> str:
        """Return a unique, Home Assistant friendly identifier for this entity."""
        return f"{self._device.address}_hum"

    @callback
    def _async_update_attrs(self) -> None:
        """Handle updating _attr values."""
        self._attr_native_value = self._device.humidity


class WorkTypeSensor(ACInfinitySensor):
    _attr_native_unit_of_measurement = None
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    @property
    def name(self) -> str:
        return f"{self._name} Work Type"

    @property
    def unique_id(self) -> str:
        """Return a unique, Home Assistant friendly identifier for this entity."""
        return f"{self._device.address}_work_type"

    @callback
    def _async_update_attrs(self) -> None:
        """Handle updating _attr values."""
        self._attr_native_value = WORK_TYPE_FROM_RAW.get(
            self._device.state.work_type, "Unknown"
        )


class VpdSensor(ACInfinitySensor):
    _attr_native_unit_of_measurement = UnitOfPressure.KPA
    _attr_device_class = SensorDeviceClass.ATMOSPHERIC_PRESSURE
    _attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def name(self) -> str:
        return f"{self._name} VPD"

    @property
    def unique_id(self) -> str:
        """Return a unique, Home Assistant friendly identifier for this entity."""
        return f"{self._device.address}_vpd"

    @callback
    def _async_update_attrs(self) -> None:
        """Handle updating _attr values."""
        self._attr_native_value = self._device.vpd
