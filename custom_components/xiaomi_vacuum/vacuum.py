"""Xiaomi Vacuum 1C"""
from functools import partial
import logging
import voluptuous as vol

from .miio import DreameVacuum, DeviceException

from homeassistant.components.vacuum import (
    PLATFORM_SCHEMA,
    STATE_CLEANING,
    STATE_IDLE,
    STATE_PAUSED,
    STATE_RETURNING,
    STATE_DOCKED,
    STATE_ERROR,
    StateVacuumEntity,
    VacuumEntityFeature,
)

from homeassistant.const import CONF_HOST, CONF_NAME, CONF_TOKEN, CONF_UNIQUE_ID
from homeassistant.helpers import config_validation as cv

_LOGGER = logging.getLogger(__name__)

DEFAULT_NAME = "Xiaomi vacuum cleaner"
DATA_KEY = "vacuum.xiaomi_vacuum"

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Required(CONF_HOST): cv.string,
        vol.Required(CONF_TOKEN): vol.All(str, vol.Length(min=32, max=32)),
        vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
        vol.Optional(CONF_UNIQUE_ID): cv.string,
    },
    extra=vol.ALLOW_EXTRA,
)

ATTR_STATUS = "status"
ATTR_ERROR = "error"
ATTR_FAN_SPEED = "fan_speed"
ATTR_CLEANING_TIME = "cleaning_time"
ATTR_CLEANING_AREA = "cleaning_area"
ATTR_MAIN_BRUSH_LEFT_TIME = "main_brush_time_left"
ATTR_MAIN_BRUSH_LIFE_LEVEL = "main_brush_life_level"
ATTR_SIDE_BRUSH_LEFT_TIME = "side_brush_time_left"
ATTR_SIDE_BRUSH_LIFE_LEVEL = "side_brush_life_level"
ATTR_FILTER_LIFE_LEVEL = "filter_life_level"
ATTR_FILTER_LEFT_TIME = "filter_left_time"
ATTR_CLEANING_TOTAL_TIME = "total_cleaning_count"
ATTR_CLEANING_TOTAL_AREA = "total_cleaning_area"
ATTR_WATER_LEVEL = "water_level"
ATTR_WATER_LEVEL_LIST = "water_level_list"

SUPPORT_XIAOMI = (
    VacuumEntityFeature.STATE
    | VacuumEntityFeature.BATTERY
    | VacuumEntityFeature.LOCATE
    | VacuumEntityFeature.RETURN_HOME
    | VacuumEntityFeature.START
    | VacuumEntityFeature.STOP
    | VacuumEntityFeature.PAUSE
    | VacuumEntityFeature.FAN_SPEED
    | VacuumEntityFeature.SEND_COMMAND
)

STATE_CODE_TO_STATE = {
    1: STATE_CLEANING,
    2: STATE_IDLE,
    3: STATE_PAUSED,
    4: STATE_ERROR,
    5: STATE_RETURNING,
    6: STATE_DOCKED,
}

SPEED_CODE_TO_NAME = {
    0: "Silent",
    1: "Standard",
    2: "Strong",
    3: "Turbo",
}

WATER_CODE_TO_NAME = {
    1: "Low",
    2: "Medium",
    3: "High",
}

ERROR_CODE_TO_ERROR = {
    0: "NoError",
    1: "Drop",
    2: "Cliff",
    3: "Bumper",
    4: "Gesture",
    5: "Bumper_repeat",
    6: "Drop_repeat",
    7: "Optical_flow",
    8: "No_box",
    9: "No_tankbox",
    10: "Waterbox_empty",
    11: "Box_full",
    12: "Brush",
    13: "Side_brush",
    14: "Fan",
    15: "Left_wheel_motor",
    16: "Right_wheel_motor",
    17: "Turn_suffocate",
    18: "Forward_suffocate",
    19: "Charger_get",
    20: "Battery_low",
    21: "Charge_fault",
    22: "Battery_percentage",
    23: "Heart",
    24: "Camera_occlusion",
    25: "Camera_fault",
    26: "Event_battery",
    27: "Forward_looking",
    28: "Gyroscope",
}


async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    """Set up the Xiaomi vacuum cleaner platform."""
    if DATA_KEY not in hass.data:
        hass.data[DATA_KEY] = {}

    host = config.get(CONF_HOST)
    token = config.get(CONF_TOKEN)
    name = config.get(CONF_NAME)
    unique_id = config.get(CONF_UNIQUE_ID)

    # Create handler
    _LOGGER.info("Initializing with host %s (token %s...)", host, token)
    vacuum = DreameVacuum(host, token)

    dreame_vacuum_entity = DreameVacuumEntity(name, vacuum, unique_id)
    hass.data[DATA_KEY][host] = dreame_vacuum_entity

    async_add_entities([dreame_vacuum_entity], update_before_add=True)


class DreameVacuumEntity(StateVacuumEntity):
    """Representation of a Xiaomi vacuum cleaner robot."""

    def __init__(self, name, vacuum, unique_id=None):
        """Initialize the Xiaomi vacuum cleaner robot handler."""
        self._name = name
        self._vacuum = vacuum
        self._unique_id = unique_id

        self._fan_speeds = None
        self._fan_speeds_reverse = None
        self._current_fan_speed = None

        self.vacuum_state = None
        self.vacuum_error = None
        self.battery_percentage = None

        self._main_brush_time_left = None
        self._main_brush_life_level = None

        self._side_brush_time_left = None
        self._side_brush_life_level = None

        self._filter_life_level = None
        self._filter_left_time = None

        self._total_clean_count = None
        self._total_area = None

        self._cleaning_area = None
        self._cleaning_time = None

        self._water_level = None
        self._current_water_level = None
        self._water_level_reverse = None

    @property
    def name(self):
        """Return the name of the device."""
        return self._name

    @property
    def state(self):
        """Return the status of the vacuum cleaner."""
        if self.vacuum_state is not None:
            try:
                return STATE_CODE_TO_STATE[int(self.vacuum_state)]
            except KeyError:
                _LOGGER.error(
                    "STATE_CODE not supported: %s",
                    self.vacuum_state,
                )
                return None

    @property
    def error(self):
        """Return the error of the vacuum cleaner."""
        if self.vacuum_error is not None:
            try:
                return ERROR_CODE_TO_ERROR.get(self.vacuum_error, "Unknown")
            except KeyError:
                _LOGGER.error(
                    "ERROR_CODE not supported: %s",
                    self.vacuum_error,
                )
                return None

    @property
    def battery_level(self):
        """Return the battery level of the vacuum cleaner."""
        if self.vacuum_state is not None:
            return self.battery_percentage

    @property
    def fan_speed(self):
        """Return the fan speed of the vacuum cleaner."""
        if self.vacuum_state is not None:
            speed = self._current_fan_speed
            if speed in self._fan_speeds_reverse:
                return SPEED_CODE_TO_NAME.get(self._current_fan_speed, "Unknown")

            _LOGGER.debug("Unable to find reverse for %s", speed)

            return speed

    @property
    def fan_speed_list(self):
        """Get the list of available fan speeds of the vacuum cleaner."""
        return list(self._fan_speeds_reverse)

    @property
    def water_level(self):
        """Return the water level of the vacuum cleaner."""
        if self.vacuum_state is not None:
            water = self._current_water_level
            if water in self._water_level_reverse:
                return WATER_CODE_TO_NAME.get(self._current_water_level, "Unknown")

            _LOGGER.debug("Unable to find reverse for %s", water)

            return water

    @property
    def water_level_list(self):
        """Get the list of available water levels of the vacuum cleaner."""
        return list(self._water_level_reverse)

    @property
    def extra_state_attributes(self):
        """Return the extra state attributes of this vacuum cleaner."""
        if self.vacuum_state is not None:
            return {
                ATTR_STATUS: STATE_CODE_TO_STATE[int(self.vacuum_state)],
                ATTR_ERROR: ERROR_CODE_TO_ERROR.get(self.vacuum_error, "Unknown"),
				ATTR_FAN_SPEED: SPEED_CODE_TO_NAME.get(self._current_fan_speed, "Unknown"),
                ATTR_MAIN_BRUSH_LEFT_TIME: self._main_brush_time_left,
                ATTR_MAIN_BRUSH_LIFE_LEVEL: self._main_brush_life_level,
                ATTR_SIDE_BRUSH_LEFT_TIME: self._side_brush_time_left,
                ATTR_SIDE_BRUSH_LIFE_LEVEL: self._side_brush_life_level,
                ATTR_FILTER_LIFE_LEVEL: self._filter_life_level,
                ATTR_FILTER_LEFT_TIME: self._filter_left_time,
                ATTR_CLEANING_AREA: self._cleaning_area,
                ATTR_CLEANING_TOTAL_AREA: self._total_area,
                ATTR_CLEANING_TIME: self._cleaning_time,
                ATTR_CLEANING_TOTAL_TIME: self._total_clean_count,
				ATTR_WATER_LEVEL: WATER_CODE_TO_NAME.get(self._current_water_level, "Unknown"),
                ATTR_WATER_LEVEL_LIST: ["Low", "Medium", "High"],
            }

    @property
    def supported_features(self):
        """Flag vacuum cleaner robot features that are supported."""
        return SUPPORT_XIAOMI

    @property
    def unique_id(self):
        """Return the unique id of the device."""
        return self._unique_id

    async def _try_command(self, mask_error, func, *args, **kwargs):
        """Call a vacuum command handling error messages."""
        try:
            await self.hass.async_add_executor_job(partial(func, *args, **kwargs))
            return True
        except DeviceException as exc:
            _LOGGER.error(mask_error, exc)
            return False

    async def async_locate(self, **kwargs):
        """Locate the vacuum cleaner."""
        await self._try_command("Unable to locate the botvac: %s", self._vacuum.find)

    async def async_start(self):
        """Start or resume the cleaning task."""
        await self._try_command("Unable to start the vacuum: %s", self._vacuum.start)

    async def async_stop(self, **kwargs):
        """Stop the vacuum cleaner."""
        await self._try_command("Unable to stop the vacuum: %s", self._vacuum.stop)

    async def async_pause(self):
        """Pause the cleaning task."""
        await self._try_command("Unable to start/pause the vacuum: %s", self._vacuum.stop)

    async def async_return_to_base(self, **kwargs):
        """Set the vacuum cleaner to return to the dock."""
        await self._try_command("Unable to return home: %s", self._vacuum.return_home)

    async def async_set_fan_speed(self, fan_speed, **kwargs):
        """Set fan speed."""
        if fan_speed in self._fan_speeds_reverse:
            fan_speed = self._fan_speeds_reverse[fan_speed]
        else:
            try:
                fan_speed = int(fan_speed)
            except ValueError as exc:
                _LOGGER.error(
                    "Fan speed step not recognized (%s). Valid speeds are: %s",
                    exc,
                    self.fan_speed_list,
                )
                return
        await self._try_command("Unable to set fan speed: %s", self._vacuum.set_fan_speed, fan_speed)

    async def set_water_level(self, water_level, **kwargs):
        """Set water level."""
        if water_level in self._water_level_reverse:
            water_level = self._water_level_reverse[water_level]
        else:
            try:
                water_level = int(water_level)
            except ValueError as exc:
                _LOGGER.error(
                    "water level step not recognized (%s). Valid are: %s",
                    exc,
                    self.water_level_list,
                )
                return
        await self._try_command("Unable to set water level: %s", self._vacuum.set_water_level, water_level)

    async def async_send_command(self, command, params, **kwargs):
        """Send a command to a vacuum cleaner."""
        if command == "set_water_level":
            await self.set_water_level(params['water_level'])
        else:
            raise NotImplementedError()

    def update(self):
        """Fetch state from the device."""
        try:
            state = self._vacuum.status()

            self.vacuum_state = state.status
            self.vacuum_error = state.error

            self._fan_speeds = SPEED_CODE_TO_NAME
            self._fan_speeds_reverse = {v: k for k, v in self._fan_speeds.items()}
            self._current_fan_speed = state.fan_speed

            self.battery_percentage = state.battery

            self._total_clean_count = state.total_clean_count
            self._total_area = state.total_area

            self._main_brush_time_left = state.brush_left_time
            self._main_brush_life_level = state.brush_life_level

            self._side_brush_time_left = state.brush_left_time2
            self._side_brush_life_level = state.brush_life_level2

            self._filter_life_level = state.filter_life_level
            self._filter_left_time = state.filter_left_time

            self._cleaning_area = state.area
            self._cleaning_time = state.timer

            self._water_level = WATER_CODE_TO_NAME
            self._water_level_reverse = {v: k for k, v in self._water_level.items()}
            self._current_water_level = state.water_level

        except OSError as exc:
            _LOGGER.error("Got OSError while fetching the state: %s", exc)
