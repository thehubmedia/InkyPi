import pytest
from unittest.mock import Mock, patch
from PIL import Image

# We need to mock utils before importing base_plugin
import sys
sys.path.insert(0, 'src')

from plugins.base_plugin.base_plugin import BasePlugin


class MockPluginWithButtons(BasePlugin):
    """Mock plugin that implements button handling"""

    def __init__(self, config, **dependencies):
        super().__init__(config, **dependencies)
        self.button_press_count = 0
        self.last_button_id = None

    def generate_image(self, settings, device_config):
        return Image.new('RGB', (100, 100), color='red')

    def handle_button(self, button_id, settings, device_config):
        self.button_press_count += 1
        self.last_button_id = button_id

        if button_id == 1:
            return Image.new('RGB', (100, 100), color='blue')
        elif button_id == 2:
            return Image.new('RGB', (100, 100), color='green')
        else:
            return self.generate_image(settings, device_config)


class MockPluginWithoutButtons(BasePlugin):
    """Mock plugin that doesn't implement button handling"""

    def generate_image(self, settings, device_config):
        return Image.new('RGB', (100, 100), color='yellow')


class TestBasePluginButtons:
    """Test BasePlugin button handling"""

    @patch('plugins.base_plugin.base_plugin.resolve_path')
    @patch('plugins.base_plugin.base_plugin.get_fonts')
    def test_default_handle_button_returns_none(self, mock_fonts, mock_resolve):
        """Test that default handle_button implementation returns None"""
        mock_resolve.return_value = "/fake/path"
        mock_fonts.return_value = []

        config = {"id": "test_plugin"}
        plugin = MockPluginWithoutButtons(config)

        result = plugin.handle_button(1, {}, Mock())

        assert result is None

    @patch('plugins.base_plugin.base_plugin.resolve_path')
    @patch('plugins.base_plugin.base_plugin.get_fonts')
    def test_plugin_can_override_handle_button(self, mock_fonts, mock_resolve):
        """Test that plugins can override handle_button"""
        mock_resolve.return_value = "/fake/path"
        mock_fonts.return_value = []

        config = {"id": "test_plugin"}
        plugin = MockPluginWithButtons(config)

        result = plugin.handle_button(1, {}, Mock())

        assert result is not None
        assert isinstance(result, Image.Image)
        assert plugin.button_press_count == 1
        assert plugin.last_button_id == 1

    @patch('plugins.base_plugin.base_plugin.resolve_path')
    @patch('plugins.base_plugin.base_plugin.get_fonts')
    def test_handle_button_with_different_button_ids(self, mock_fonts, mock_resolve):
        """Test handling different button IDs"""
        mock_resolve.return_value = "/fake/path"
        mock_fonts.return_value = []

        config = {"id": "test_plugin"}
        plugin = MockPluginWithButtons(config)

        # Press button 1
        image1 = plugin.handle_button(1, {}, Mock())
        assert plugin.last_button_id == 1

        # Press button 2
        image2 = plugin.handle_button(2, {}, Mock())
        assert plugin.last_button_id == 2

        # Press button 3
        image3 = plugin.handle_button(3, {}, Mock())
        assert plugin.last_button_id == 3

        assert plugin.button_press_count == 3

    @patch('plugins.base_plugin.base_plugin.resolve_path')
    @patch('plugins.base_plugin.base_plugin.get_fonts')
    def test_handle_button_receives_settings(self, mock_fonts, mock_resolve):
        """Test that handle_button receives plugin settings"""
        mock_resolve.return_value = "/fake/path"
        mock_fonts.return_value = []

        config = {"id": "test_plugin"}

        class SettingsAwarePlugin(BasePlugin):
            def __init__(self, config, **dependencies):
                super().__init__(config, **dependencies)
                self.received_settings = None

            def generate_image(self, settings, device_config):
                return Image.new('RGB', (100, 100))

            def handle_button(self, button_id, settings, device_config):
                self.received_settings = settings
                return self.generate_image(settings, device_config)

        plugin = SettingsAwarePlugin(config)
        test_settings = {"location": "NYC", "units": "metric"}

        plugin.handle_button(1, test_settings, Mock())

        assert plugin.received_settings == test_settings

    @patch('plugins.base_plugin.base_plugin.resolve_path')
    @patch('plugins.base_plugin.base_plugin.get_fonts')
    def test_handle_button_receives_device_config(self, mock_fonts, mock_resolve):
        """Test that handle_button receives device config"""
        mock_resolve.return_value = "/fake/path"
        mock_fonts.return_value = []

        config = {"id": "test_plugin"}

        class ConfigAwarePlugin(BasePlugin):
            def __init__(self, config, **dependencies):
                super().__init__(config, **dependencies)
                self.received_device_config = None

            def generate_image(self, settings, device_config):
                return Image.new('RGB', (100, 100))

            def handle_button(self, button_id, settings, device_config):
                self.received_device_config = device_config
                return self.generate_image(settings, device_config)

        plugin = ConfigAwarePlugin(config)
        mock_device_config = Mock()
        mock_device_config.get_config.return_value = "test_value"

        plugin.handle_button(1, {}, mock_device_config)

        assert plugin.received_device_config == mock_device_config


class TestPluginButtonIntegration:
    """Integration tests for button handling with plugins"""

    @patch('plugins.base_plugin.base_plugin.resolve_path')
    @patch('plugins.base_plugin.base_plugin.get_fonts')
    def test_weather_station_switching_pattern(self, mock_fonts, mock_resolve):
        """Test a common pattern: weather plugin switching stations"""
        mock_resolve.return_value = "/fake/path"
        mock_fonts.return_value = []

        config = {"id": "weather"}

        class WeatherPlugin(BasePlugin):
            def __init__(self, config, **dependencies):
                super().__init__(config, **dependencies)
                self.stations = ["NYC", "LA", "Chicago"]
                self.current_station = 0

            def generate_image(self, settings, device_config):
                station = self.stations[self.current_station]
                return Image.new('RGB', (100, 100), color='blue')

            def handle_button(self, button_id, settings, device_config):
                if button_id == 1:
                    # Previous station
                    self.current_station = (self.current_station - 1) % len(self.stations)
                elif button_id == 2:
                    # Next station
                    self.current_station = (self.current_station + 1) % len(self.stations)

                return self.generate_image(settings, device_config)

        plugin = WeatherPlugin(config)

        # Start at NYC (index 0)
        assert plugin.current_station == 0

        # Press button 2 (next) - should go to LA
        plugin.handle_button(2, {}, Mock())
        assert plugin.current_station == 1

        # Press button 2 (next) - should go to Chicago
        plugin.handle_button(2, {}, Mock())
        assert plugin.current_station == 2

        # Press button 2 (next) - should wrap to NYC
        plugin.handle_button(2, {}, Mock())
        assert plugin.current_station == 0

        # Press button 1 (previous) - should go to Chicago
        plugin.handle_button(1, {}, Mock())
        assert plugin.current_station == 2

    @patch('plugins.base_plugin.base_plugin.resolve_path')
    @patch('plugins.base_plugin.base_plugin.get_fonts')
    def test_slideshow_navigation_pattern(self, mock_fonts, mock_resolve):
        """Test slideshow pattern with next/previous buttons"""
        mock_resolve.return_value = "/fake/path"
        mock_fonts.return_value = []

        config = {"id": "slideshow"}

        class SlideshowPlugin(BasePlugin):
            def __init__(self, config, **dependencies):
                super().__init__(config, **dependencies)
                self.images = ["img1.jpg", "img2.jpg", "img3.jpg", "img4.jpg"]
                self.current_index = 0

            def generate_image(self, settings, device_config):
                # Would load self.images[self.current_index]
                return Image.new('RGB', (100, 100))

            def handle_button(self, button_id, settings, device_config):
                if button_id == 1:
                    # Previous image
                    self.current_index = max(0, self.current_index - 1)
                elif button_id == 2:
                    # Next image
                    self.current_index = min(len(self.images) - 1, self.current_index + 1)
                elif button_id == 3:
                    # Jump to start
                    self.current_index = 0

                return self.generate_image(settings, device_config)

        plugin = SlideshowPlugin(config)

        # Start at beginning
        assert plugin.current_index == 0

        # Try to go previous (should stay at 0)
        plugin.handle_button(1, {}, Mock())
        assert plugin.current_index == 0

        # Go next
        plugin.handle_button(2, {}, Mock())
        assert plugin.current_index == 1

        # Go next
        plugin.handle_button(2, {}, Mock())
        assert plugin.current_index == 2

        # Jump to start
        plugin.handle_button(3, {}, Mock())
        assert plugin.current_index == 0

    @patch('plugins.base_plugin.base_plugin.resolve_path')
    @patch('plugins.base_plugin.base_plugin.get_fonts')
    def test_refresh_button_pattern(self, mock_fonts, mock_resolve):
        """Test refresh button pattern"""
        mock_resolve.return_value = "/fake/path"
        mock_fonts.return_value = []

        config = {"id": "data_display"}

        class DataPlugin(BasePlugin):
            def __init__(self, config, **dependencies):
                super().__init__(config, **dependencies)
                self.refresh_count = 0
                self.last_data = None

            def fetch_data(self):
                self.refresh_count += 1
                return f"Data {self.refresh_count}"

            def generate_image(self, settings, device_config):
                self.last_data = self.fetch_data()
                return Image.new('RGB', (100, 100))

            def handle_button(self, button_id, settings, device_config):
                if button_id == 3:
                    # Force refresh
                    return self.generate_image(settings, device_config)
                return None

        plugin = DataPlugin(config)

        # Initial state
        assert plugin.refresh_count == 0

        # Press refresh button
        plugin.handle_button(3, {}, Mock())
        assert plugin.refresh_count == 1

        # Press refresh button again
        plugin.handle_button(3, {}, Mock())
        assert plugin.refresh_count == 2

        # Press other button (should not refresh)
        result = plugin.handle_button(1, {}, Mock())
        assert result is None
        assert plugin.refresh_count == 2  # Unchanged
