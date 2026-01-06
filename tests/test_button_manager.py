import pytest
from unittest.mock import Mock, MagicMock, patch, call
from src.hardware.button_manager import (
    ButtonManager,
    ButtonConfig,
    ButtonAction,
    HardwarePresets
)


class TestButtonConfig:
    """Test ButtonConfig class"""

    def test_button_config_initialization(self):
        config_dict = {
            "id": "test_button",
            "label": "Test",
            "pin": 17,
            "pull_up": True,
            "bounce_time": 0.2,
            "action": "refresh_current",
            "action_params": {"param1": "value1"}
        }
        button = ButtonConfig(config_dict)

        assert button.id == "test_button"
        assert button.label == "Test"
        assert button.pin == 17
        assert button.pull_up is True
        assert button.bounce_time == 0.2
        assert button.action == "refresh_current"
        assert button.action_params == {"param1": "value1"}

    def test_button_config_defaults(self):
        config_dict = {
            "id": "minimal",
            "label": "Min",
            "pin": 5
        }
        button = ButtonConfig(config_dict)

        assert button.pull_up is True
        assert button.bounce_time == 0.2
        assert button.hold_time == 2.0
        assert button.action == "refresh_current"
        assert button.action_params == {}

    def test_button_config_to_dict(self):
        config_dict = {
            "id": "test",
            "label": "A",
            "pin": 5,
            "pull_up": True,
            "bounce_time": 0.3,
            "hold_time": 2.5,
            "action": "next_plugin",
            "action_params": {}
        }
        button = ButtonConfig(config_dict)
        result = button.to_dict()

        assert result == config_dict


class TestHardwarePresets:
    """Test HardwarePresets class"""

    def test_inky_impression_7_3_preset(self):
        preset = HardwarePresets.get_preset("inky_impression_7.3")

        assert len(preset) == 4
        assert preset[0]["pin"] == 5
        assert preset[1]["pin"] == 6
        assert preset[2]["pin"] == 16
        assert preset[3]["pin"] == 24

    def test_inky_impression_13_3_preset(self):
        preset = HardwarePresets.get_preset("inky_impression_13.3")

        assert len(preset) == 4
        assert preset[0]["pin"] == 5
        assert preset[1]["pin"] == 6
        assert preset[2]["pin"] == 25  # Different from 7.3"
        assert preset[3]["pin"] == 24

    def test_custom_preset(self):
        preset = HardwarePresets.get_preset("custom")
        assert preset == []

    def test_unknown_preset(self):
        preset = HardwarePresets.get_preset("unknown_preset")
        assert preset == []


class TestButtonManager:
    """Test ButtonManager class"""

    @patch('src.hardware.button_manager.GPIOZERO_AVAILABLE', False)
    def test_disabled_when_gpiozero_unavailable(self):
        config = {"enabled": True}
        manager = ButtonManager(config)
        assert manager.enabled is False

    @patch('src.hardware.button_manager.GPIOZERO_AVAILABLE', True)
    def test_enabled_with_config(self):
        config = {"enabled": True, "hardware_preset": "custom", "buttons": []}
        manager = ButtonManager(config)
        assert manager.enabled is True

    @patch('src.hardware.button_manager.GPIOZERO_AVAILABLE', True)
    def test_disabled_by_config(self):
        config = {"enabled": False}
        manager = ButtonManager(config)
        assert manager.enabled is False

    @patch('src.hardware.button_manager.GPIOZERO_AVAILABLE', True)
    def test_load_hardware_preset(self):
        config = {
            "enabled": True,
            "hardware_preset": "inky_impression_7.3"
        }
        manager = ButtonManager(config)

        assert len(manager.buttons) == 4
        assert manager.buttons[0].pin == 5
        assert manager.buttons[1].pin == 6
        assert manager.buttons[2].pin == 16
        assert manager.buttons[3].pin == 24

    @patch('src.hardware.button_manager.GPIOZERO_AVAILABLE', True)
    def test_load_custom_buttons(self):
        config = {
            "enabled": True,
            "hardware_preset": "custom",
            "buttons": [
                {
                    "id": "btn1",
                    "label": "Button 1",
                    "pin": 17,
                    "action": "refresh_current"
                }
            ]
        }
        manager = ButtonManager(config)

        assert len(manager.buttons) == 1
        assert manager.buttons[0].pin == 17
        assert manager.buttons[0].label == "Button 1"

    @patch('src.hardware.button_manager.GPIOZERO_AVAILABLE', True)
    @patch('src.hardware.button_manager.Button')
    def test_start_initializes_buttons(self, mock_button_class):
        config = {
            "enabled": True,
            "hardware_preset": "custom",
            "buttons": [
                {"id": "btn1", "label": "B1", "pin": 17, "action": "refresh_current"}
            ]
        }
        manager = ButtonManager(config)

        # Mock the Button instance
        mock_button_instance = MagicMock()
        mock_button_class.return_value = mock_button_instance

        manager.start()

        # Verify Button was created with correct parameters
        mock_button_class.assert_called_once_with(
            17,
            pull_up=True,
            bounce_time=0.2,
            hold_time=2.0
        )
        assert manager.running is True

    @patch('src.hardware.button_manager.GPIOZERO_AVAILABLE', True)
    def test_start_when_disabled(self):
        config = {"enabled": False}
        manager = ButtonManager(config)
        manager.start()
        assert manager.running is False

    @patch('src.hardware.button_manager.GPIOZERO_AVAILABLE', True)
    @patch('src.hardware.button_manager.Button')
    def test_stop_closes_buttons(self, mock_button_class):
        config = {
            "enabled": True,
            "hardware_preset": "custom",
            "buttons": [
                {"id": "btn1", "label": "B1", "pin": 17, "action": "refresh_current"}
            ]
        }
        manager = ButtonManager(config)

        # Mock button instance
        mock_button_instance = MagicMock()
        mock_button_class.return_value = mock_button_instance

        manager.start()
        manager.stop()

        mock_button_instance.close.assert_called_once()
        assert manager.running is False

    @patch('src.hardware.button_manager.GPIOZERO_AVAILABLE', True)
    @patch('src.hardware.button_manager.Button')
    def test_handle_refresh_current_action(self, mock_button_class):
        config = {
            "enabled": True,
            "hardware_preset": "custom",
            "buttons": [
                {"id": "btn1", "label": "B1", "pin": 17, "action": "refresh_current"}
            ]
        }
        manager = ButtonManager(config)

        # Set up handler
        refresh_handler = Mock()
        manager.set_refresh_handler(refresh_handler)

        # Simulate button press
        button_config = manager.buttons[0]
        manager._handle_button_press(button_config)

        refresh_handler.assert_called_once()

    @patch('src.hardware.button_manager.GPIOZERO_AVAILABLE', True)
    @patch('src.hardware.button_manager.Button')
    def test_handle_next_plugin_action(self, mock_button_class):
        config = {
            "enabled": True,
            "hardware_preset": "custom",
            "buttons": [
                {"id": "btn1", "label": "B1", "pin": 17, "action": "next_plugin"}
            ]
        }
        manager = ButtonManager(config)

        # Set up handler
        next_handler = Mock()
        manager.set_next_plugin_handler(next_handler)

        # Simulate button press
        button_config = manager.buttons[0]
        manager._handle_button_press(button_config)

        next_handler.assert_called_once()

    @patch('src.hardware.button_manager.GPIOZERO_AVAILABLE', True)
    @patch('src.hardware.button_manager.Button')
    def test_handle_previous_plugin_action(self, mock_button_class):
        config = {
            "enabled": True,
            "hardware_preset": "custom",
            "buttons": [
                {"id": "btn1", "label": "B1", "pin": 17, "action": "previous_plugin"}
            ]
        }
        manager = ButtonManager(config)

        # Set up handler
        prev_handler = Mock()
        manager.set_previous_plugin_handler(prev_handler)

        # Simulate button press
        button_config = manager.buttons[0]
        manager._handle_button_press(button_config)

        prev_handler.assert_called_once()

    @patch('src.hardware.button_manager.GPIOZERO_AVAILABLE', True)
    @patch('src.hardware.button_manager.Button')
    def test_handle_plugin_specific_action(self, mock_button_class):
        config = {
            "enabled": True,
            "hardware_preset": "custom",
            "buttons": [
                {
                    "id": "btn1",
                    "label": "B1",
                    "pin": 17,
                    "action": "plugin_specific",
                    "action_params": {"button_id": 1}
                }
            ]
        }
        manager = ButtonManager(config)

        # Set up handler
        plugin_handler = Mock()
        manager.set_plugin_specific_handler(plugin_handler)

        # Simulate button press
        button_config = manager.buttons[0]
        manager._handle_button_press(button_config)

        plugin_handler.assert_called_once_with({"button_id": 1})

    @patch('src.hardware.button_manager.GPIOZERO_AVAILABLE', True)
    @patch('src.hardware.button_manager.Button')
    def test_handle_custom_action(self, mock_button_class):
        config = {
            "enabled": True,
            "hardware_preset": "custom",
            "buttons": [
                {
                    "id": "btn1",
                    "label": "B1",
                    "pin": 17,
                    "action": "custom",
                    "action_params": {"handler": "my_handler", "data": "test"}
                }
            ]
        }
        manager = ButtonManager(config)

        # Register custom handler
        custom_handler = Mock()
        manager.register_action_handler("my_handler", custom_handler)

        # Simulate button press
        button_config = manager.buttons[0]
        manager._handle_button_press(button_config)

        custom_handler.assert_called_once_with({"handler": "my_handler", "data": "test"})

    @patch('src.hardware.button_manager.GPIOZERO_AVAILABLE', True)
    def test_get_button_configs(self):
        config = {
            "enabled": True,
            "hardware_preset": "custom",
            "buttons": [
                {"id": "btn1", "label": "B1", "pin": 17, "action": "refresh_current"}
            ]
        }
        manager = ButtonManager(config)

        configs = manager.get_button_configs()
        assert len(configs) == 1
        assert configs[0]["id"] == "btn1"
        assert configs[0]["pin"] == 17

    @patch('src.hardware.button_manager.GPIOZERO_AVAILABLE', True)
    def test_is_enabled(self):
        config = {"enabled": True, "hardware_preset": "custom", "buttons": []}
        manager = ButtonManager(config)
        assert manager.is_enabled() is True

        config = {"enabled": False}
        manager = ButtonManager(config)
        assert manager.is_enabled() is False

    @patch('src.hardware.button_manager.GPIOZERO_AVAILABLE', True)
    @patch('src.hardware.button_manager.Button')
    def test_missing_handler_logs_warning(self, mock_button_class, caplog):
        config = {
            "enabled": True,
            "hardware_preset": "custom",
            "buttons": [
                {"id": "btn1", "label": "B1", "pin": 17, "action": "refresh_current"}
            ]
        }
        manager = ButtonManager(config)

        # Don't set handler - should log warning
        button_config = manager.buttons[0]
        manager._handle_button_press(button_config)

        assert "No handler registered for refresh_current action" in caplog.text

    @patch('src.hardware.button_manager.GPIOZERO_AVAILABLE', True)
    @patch('src.hardware.button_manager.Button')
    def test_thread_safety(self, mock_button_class):
        """Test that button press handling is thread-safe"""
        config = {
            "enabled": True,
            "hardware_preset": "custom",
            "buttons": [
                {"id": "btn1", "label": "B1", "pin": 17, "action": "refresh_current"}
            ]
        }
        manager = ButtonManager(config)

        handler_called = []
        def handler():
            handler_called.append(1)

        manager.set_refresh_handler(handler)

        # Simulate multiple concurrent button presses
        import threading
        threads = []
        button_config = manager.buttons[0]

        for _ in range(10):
            t = threading.Thread(target=manager._handle_button_press, args=(button_config,))
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        # All presses should have been handled
        assert len(handler_called) == 10
