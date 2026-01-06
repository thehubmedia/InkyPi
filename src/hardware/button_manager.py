"""
Button Manager for InkyPi

Provides generic button support for Raspberry Pi GPIO buttons.
Supports both hardware-specific presets and custom button configurations.

This module handles button events and dispatches actions to the refresh task
or individual plugins.
"""

import logging
import threading
from typing import Dict, List, Optional, Callable, Any
from enum import Enum

logger = logging.getLogger(__name__)

# Try to import gpiozero, but provide graceful fallback for development
try:
    from gpiozero import Button
    GPIOZERO_AVAILABLE = True
except ImportError:
    logger.warning("gpiozero not available - button support will be disabled")
    GPIOZERO_AVAILABLE = False
    Button = None


class ButtonAction(Enum):
    """Available button actions"""
    REFRESH_CURRENT = "refresh_current"  # Refresh currently displayed plugin
    NEXT_PLUGIN = "next_plugin"          # Advance to next plugin in playlist
    PREVIOUS_PLUGIN = "previous_plugin"  # Go to previous plugin in playlist
    PLUGIN_SPECIFIC = "plugin_specific"  # Delegate to plugin's handle_button method
    CUSTOM = "custom"                    # Custom action callback


class ButtonConfig:
    """Configuration for a single button"""

    def __init__(self, config_dict: Dict[str, Any]):
        """
        Initialize button configuration.

        Args:
            config_dict: Dictionary with button configuration
                {
                    "id": "button_a",
                    "label": "A",
                    "pin": 5,
                    "pull_up": true,
                    "bounce_time": 0.2,
                    "hold_time": 2.0,
                    "action": "plugin_specific",
                    "action_params": {"button_id": 1}
                }
        """
        self.id = config_dict.get("id", "")
        self.label = config_dict.get("label", "")
        self.pin = config_dict.get("pin")
        self.pull_up = config_dict.get("pull_up", True)
        self.bounce_time = config_dict.get("bounce_time", 0.2)
        self.hold_time = config_dict.get("hold_time", 2.0)
        self.action = config_dict.get("action", "refresh_current")
        self.action_params = config_dict.get("action_params", {})

        # GPIO button instance (set later)
        self.button_instance: Optional[Any] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "id": self.id,
            "label": self.label,
            "pin": self.pin,
            "pull_up": self.pull_up,
            "bounce_time": self.bounce_time,
            "hold_time": self.hold_time,
            "action": self.action,
            "action_params": self.action_params
        }


class HardwarePresets:
    """Hardware-specific button presets"""

    PRESETS = {
        "inky_impression_7.3": [
            {
                "id": "button_a",
                "label": "A",
                "pin": 5,
                "pull_up": True,
                "action": "plugin_specific",
                "action_params": {"button_id": 1}
            },
            {
                "id": "button_b",
                "label": "B",
                "pin": 6,
                "pull_up": True,
                "action": "plugin_specific",
                "action_params": {"button_id": 2}
            },
            {
                "id": "button_c",
                "label": "C",
                "pin": 16,
                "pull_up": True,
                "action": "plugin_specific",
                "action_params": {"button_id": 3}
            },
            {
                "id": "button_d",
                "label": "D",
                "pin": 24,
                "pull_up": True,
                "action": "plugin_specific",
                "action_params": {"button_id": 4}
            }
        ],
        "inky_impression_13.3": [
            {
                "id": "button_a",
                "label": "A",
                "pin": 5,
                "pull_up": True,
                "action": "plugin_specific",
                "action_params": {"button_id": 1}
            },
            {
                "id": "button_b",
                "label": "B",
                "pin": 6,
                "pull_up": True,
                "action": "plugin_specific",
                "action_params": {"button_id": 2}
            },
            {
                "id": "button_c",
                "label": "C",
                "pin": 25,  # Different pin for 13.3"
                "pull_up": True,
                "action": "plugin_specific",
                "action_params": {"button_id": 3}
            },
            {
                "id": "button_d",
                "label": "D",
                "pin": 24,
                "pull_up": True,
                "action": "plugin_specific",
                "action_params": {"button_id": 4}
            }
        ],
        "custom": []  # Empty preset for custom configuration
    }

    @classmethod
    def get_preset(cls, preset_name: str) -> List[Dict[str, Any]]:
        """Get button configuration for a hardware preset"""
        return cls.PRESETS.get(preset_name, [])


class ButtonManager:
    """
    Manages GPIO buttons and dispatches button press events.

    The ButtonManager runs in the background and handles button press events,
    dispatching them to either global actions or plugin-specific handlers.
    """

    def __init__(self, config_dict: Optional[Dict[str, Any]] = None):
        """
        Initialize the button manager.

        Args:
            config_dict: Button configuration dictionary from device.json
        """
        self.config_dict = config_dict or {}
        self.enabled = self.config_dict.get("enabled", False)
        self.buttons: List[ButtonConfig] = []
        self.action_handlers: Dict[str, Callable] = {}
        self.running = False
        self._lock = threading.Lock()

        # Callbacks for global actions
        self.on_refresh_current: Optional[Callable] = None
        self.on_next_plugin: Optional[Callable] = None
        self.on_previous_plugin: Optional[Callable] = None
        self.on_plugin_specific: Optional[Callable] = None

        if not GPIOZERO_AVAILABLE:
            logger.warning("Button support disabled - gpiozero not available")
            self.enabled = False

        if self.enabled:
            self._load_button_configs()

    def _load_button_configs(self):
        """Load button configurations from config dict"""
        preset_name = self.config_dict.get("hardware_preset", "custom")

        if preset_name != "custom":
            # Load from hardware preset
            preset_configs = HardwarePresets.get_preset(preset_name)
            if not preset_configs:
                logger.warning(f"Unknown hardware preset: {preset_name}")
                return

            logger.info(f"Loading button preset: {preset_name}")
            button_configs = preset_configs
        else:
            # Load custom configuration
            button_configs = self.config_dict.get("buttons", [])

        # Create ButtonConfig objects
        for btn_config in button_configs:
            try:
                button = ButtonConfig(btn_config)
                self.buttons.append(button)
                logger.info(f"Configured button: {button.label} (GPIO {button.pin}) -> {button.action}")
            except Exception as e:
                logger.error(f"Failed to configure button: {e}")

    def start(self):
        """Start monitoring buttons"""
        if not self.enabled or not GPIOZERO_AVAILABLE:
            logger.info("Button manager not started (disabled or gpiozero unavailable)")
            return

        if self.running:
            logger.warning("Button manager already running")
            return

        logger.info("Starting button manager...")
        self.running = True

        # Initialize GPIO buttons
        for button_config in self.buttons:
            try:
                # Create gpiozero Button instance
                button_config.button_instance = Button(
                    button_config.pin,
                    pull_up=button_config.pull_up,
                    bounce_time=button_config.bounce_time,
                    hold_time=button_config.hold_time
                )

                # Bind event handlers
                button_config.button_instance.when_pressed = lambda bc=button_config: self._handle_button_press(bc)

                logger.info(f"Button {button_config.label} initialized on GPIO {button_config.pin}")

            except Exception as e:
                logger.error(f"Failed to initialize button {button_config.label}: {e}")

        logger.info(f"Button manager started with {len(self.buttons)} buttons")

    def stop(self):
        """Stop monitoring buttons and clean up GPIO"""
        if not self.running:
            return

        logger.info("Stopping button manager...")
        self.running = False

        # Clean up GPIO buttons
        for button_config in self.buttons:
            if button_config.button_instance:
                try:
                    button_config.button_instance.close()
                    logger.debug(f"Closed button {button_config.label}")
                except Exception as e:
                    logger.error(f"Error closing button {button_config.label}: {e}")

        logger.info("Button manager stopped")

    def _handle_button_press(self, button_config: ButtonConfig):
        """
        Handle a button press event.

        Args:
            button_config: Configuration of the pressed button
        """
        with self._lock:
            logger.info(f"Button pressed: {button_config.label} (GPIO {button_config.pin})")

            try:
                action = button_config.action
                params = button_config.action_params

                if action == ButtonAction.REFRESH_CURRENT.value:
                    if self.on_refresh_current:
                        self.on_refresh_current()
                    else:
                        logger.warning("No handler registered for refresh_current action")

                elif action == ButtonAction.NEXT_PLUGIN.value:
                    if self.on_next_plugin:
                        self.on_next_plugin()
                    else:
                        logger.warning("No handler registered for next_plugin action")

                elif action == ButtonAction.PREVIOUS_PLUGIN.value:
                    if self.on_previous_plugin:
                        self.on_previous_plugin()
                    else:
                        logger.warning("No handler registered for previous_plugin action")

                elif action == ButtonAction.PLUGIN_SPECIFIC.value:
                    if self.on_plugin_specific:
                        self.on_plugin_specific(params)
                    else:
                        logger.warning("No handler registered for plugin_specific action")

                elif action == ButtonAction.CUSTOM.value:
                    # Custom action - look up in action_handlers
                    handler_name = params.get("handler")
                    if handler_name and handler_name in self.action_handlers:
                        self.action_handlers[handler_name](params)
                    else:
                        logger.warning(f"No custom handler registered: {handler_name}")

                else:
                    logger.warning(f"Unknown button action: {action}")

            except Exception as e:
                logger.error(f"Error handling button press: {e}", exc_info=True)

    def register_action_handler(self, name: str, handler: Callable):
        """
        Register a custom action handler.

        Args:
            name: Name of the action handler
            handler: Callable to execute when action is triggered
        """
        self.action_handlers[name] = handler
        logger.info(f"Registered custom action handler: {name}")

    def set_refresh_handler(self, handler: Callable):
        """Set handler for refresh_current action"""
        self.on_refresh_current = handler

    def set_next_plugin_handler(self, handler: Callable):
        """Set handler for next_plugin action"""
        self.on_next_plugin = handler

    def set_previous_plugin_handler(self, handler: Callable):
        """Set handler for previous_plugin action"""
        self.on_previous_plugin = handler

    def set_plugin_specific_handler(self, handler: Callable):
        """Set handler for plugin_specific action"""
        self.on_plugin_specific = handler

    def get_button_configs(self) -> List[Dict[str, Any]]:
        """Get current button configurations as dictionaries"""
        return [btn.to_dict() for btn in self.buttons]

    def is_enabled(self) -> bool:
        """Check if button manager is enabled"""
        return self.enabled and GPIOZERO_AVAILABLE
