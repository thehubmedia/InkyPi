import pytest
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime
from PIL import Image

from src.refresh_task import ButtonRefresh
from src.model import PluginInstance, Playlist, PlaylistManager


class TestButtonRefresh:
    """Test ButtonRefresh action class"""

    def test_button_refresh_initialization(self):
        refresh = ButtonRefresh("weather", "Station 1", {"button_id": 1})

        assert refresh.plugin_id == "weather"
        assert refresh.plugin_instance_name == "Station 1"
        assert refresh.button_params == {"button_id": 1}

    def test_get_plugin_id(self):
        refresh = ButtonRefresh("clock", "Main Clock", {"button_id": 2})
        assert refresh.get_plugin_id() == "clock"

    def test_get_refresh_info(self):
        refresh = ButtonRefresh("weather", "Station 1", {"button_id": 1})
        info = refresh.get_refresh_info()

        assert info["refresh_type"] == "Button Press"
        assert info["plugin_id"] == "weather"
        assert info["plugin_instance"] == "Station 1"

    def test_execute_with_valid_plugin_instance(self):
        # Mock plugin that handles buttons
        mock_plugin = Mock()
        mock_image = Image.new('RGB', (100, 100), color='red')
        mock_plugin.handle_button.return_value = mock_image

        # Mock device config with plugin instance
        mock_device_config = Mock()
        mock_device_config.plugin_image_dir = "/tmp/images"

        # Create playlist with plugin instance
        plugin_instance = PluginInstance(
            plugin_id="weather",
            name="Station 1",
            settings={"location": "NYC"},
            refresh={}
        )
        playlist = Playlist("Test", "00:00", "24:00")
        playlist.plugins = [plugin_instance]

        playlist_manager = PlaylistManager()
        playlist_manager.playlists = [playlist]
        mock_device_config.get_playlist_manager.return_value = playlist_manager

        # Execute button refresh
        refresh = ButtonRefresh("weather", "Station 1", {"button_id": 1})
        current_dt = datetime(2025, 1, 1, 12, 0, 0)

        # Mock the image save operation
        with patch('os.path.join', return_value="/tmp/images/weather/station1.png"), \
             patch.object(Image.Image, 'save'):
            result_image = refresh.execute(mock_plugin, mock_device_config, current_dt)

        # Verify handle_button was called
        mock_plugin.handle_button.assert_called_once_with(
            1,
            {"location": "NYC"},
            mock_device_config
        )
        assert result_image == mock_image

    def test_execute_plugin_returns_none(self):
        # Mock plugin that returns None from handle_button
        mock_plugin = Mock()
        mock_plugin.handle_button.return_value = None
        mock_fallback_image = Image.new('RGB', (100, 100), color='blue')
        mock_plugin.generate_image.return_value = mock_fallback_image

        # Mock device config
        mock_device_config = Mock()
        mock_device_config.plugin_image_dir = "/tmp/images"

        plugin_instance = PluginInstance(
            plugin_id="clock",
            name="Main",
            settings={"format": "24h"},
            refresh={}
        )
        playlist = Playlist("Test", "00:00", "24:00")
        playlist.plugins = [plugin_instance]

        playlist_manager = PlaylistManager()
        playlist_manager.playlists = [playlist]
        mock_device_config.get_playlist_manager.return_value = playlist_manager

        # Execute
        refresh = ButtonRefresh("clock", "Main", {"button_id": 3})
        current_dt = datetime(2025, 1, 1, 12, 0, 0)

        result_image = refresh.execute(mock_plugin, mock_device_config, current_dt)

        # Should fall back to generate_image
        mock_plugin.generate_image.assert_called_once_with(
            {"format": "24h"},
            mock_device_config
        )
        assert result_image == mock_fallback_image

    def test_execute_plugin_instance_not_found(self):
        # Mock plugin
        mock_plugin = Mock()
        mock_fallback_image = Image.new('RGB', (100, 100), color='green')
        mock_plugin.generate_image.return_value = mock_fallback_image

        # Mock device config with no matching plugin instance
        mock_device_config = Mock()
        mock_device_config.plugin_image_dir = "/tmp/images"

        playlist = Playlist("Test", "00:00", "24:00")
        playlist.plugins = []  # Empty

        playlist_manager = PlaylistManager()
        playlist_manager.playlists = [playlist]
        mock_device_config.get_playlist_manager.return_value = playlist_manager

        # Execute
        refresh = ButtonRefresh("nonexistent", "Doesn't Exist", {"button_id": 1})
        current_dt = datetime(2025, 1, 1, 12, 0, 0)

        result_image = refresh.execute(mock_plugin, mock_device_config, current_dt)

        # Should generate with empty settings
        mock_plugin.generate_image.assert_called_once_with({}, mock_device_config)
        assert result_image == mock_fallback_image

    def test_execute_searches_all_playlists(self):
        """Test that execute searches across multiple playlists"""
        mock_plugin = Mock()
        mock_image = Image.new('RGB', (100, 100), color='yellow')
        mock_plugin.handle_button.return_value = mock_image

        mock_device_config = Mock()
        mock_device_config.plugin_image_dir = "/tmp/images"

        # Create multiple playlists
        plugin_instance_1 = PluginInstance("weather", "Station A", {}, {})
        playlist_1 = Playlist("Morning", "00:00", "12:00")
        playlist_1.plugins = [plugin_instance_1]

        plugin_instance_2 = PluginInstance("weather", "Station B", {"location": "LA"}, {})
        playlist_2 = Playlist("Evening", "12:00", "24:00")
        playlist_2.plugins = [plugin_instance_2]

        playlist_manager = PlaylistManager()
        playlist_manager.playlists = [playlist_1, playlist_2]
        mock_device_config.get_playlist_manager.return_value = playlist_manager

        # Execute - should find Station B in second playlist
        refresh = ButtonRefresh("weather", "Station B", {"button_id": 2})
        current_dt = datetime(2025, 1, 1, 12, 0, 0)

        # Mock the image save operation
        with patch('os.path.join', return_value="/tmp/images/weather/stationb.png"), \
             patch.object(Image.Image, 'save'):
            result_image = refresh.execute(mock_plugin, mock_device_config, current_dt)

        # Verify correct settings were used
        mock_plugin.handle_button.assert_called_once_with(
            2,
            {"location": "LA"},
            mock_device_config
        )

    def test_execute_updates_plugin_instance_timestamp(self):
        """Test that execute updates the plugin instance's latest_refresh_time"""
        mock_plugin = Mock()
        mock_image = Image.new('RGB', (100, 100), color='white')
        mock_plugin.handle_button.return_value = mock_image

        mock_device_config = Mock()
        mock_device_config.plugin_image_dir = "/tmp/images"

        plugin_instance = PluginInstance("clock", "Main", {}, {})
        plugin_instance.latest_refresh_time = None

        playlist = Playlist("Test", "00:00", "24:00")
        playlist.plugins = [plugin_instance]

        playlist_manager = PlaylistManager()
        playlist_manager.playlists = [playlist]
        mock_device_config.get_playlist_manager.return_value = playlist_manager

        refresh = ButtonRefresh("clock", "Main", {"button_id": 1})
        current_dt = datetime(2025, 1, 6, 15, 30, 45)

        # Mock the image save operation
        with patch('os.path.join', return_value="/tmp/images/clock/main.png"), \
             patch.object(Image.Image, 'save'):
            refresh.execute(mock_plugin, mock_device_config, current_dt)

        # Check timestamp was updated
        assert plugin_instance.latest_refresh_time == "2025-01-06T15:30:45"


class TestRefreshTaskButtonActions:
    """Test RefreshTask button action methods"""

    @patch('src.refresh_task.RefreshTask.manual_update')
    def test_refresh_current_plugin(self, mock_manual_update):
        from src.refresh_task import RefreshTask

        mock_device_config = Mock()
        mock_display_manager = Mock()

        refresh_task = RefreshTask(mock_device_config, mock_display_manager)
        refresh_task.current_plugin_id = "weather"
        refresh_task.current_plugin_instance_name = "Station 1"

        refresh_task.refresh_current_plugin()

        # Verify manual_update was called with ButtonRefresh
        assert mock_manual_update.called
        call_args = mock_manual_update.call_args[0][0]
        assert call_args.plugin_id == "weather"
        assert call_args.plugin_instance_name == "Station 1"

    @patch('src.refresh_task.RefreshTask.manual_update')
    def test_refresh_current_plugin_no_current(self, mock_manual_update):
        """Test refresh_current_plugin when no plugin is displayed"""
        from src.refresh_task import RefreshTask

        mock_device_config = Mock()
        mock_display_manager = Mock()

        refresh_task = RefreshTask(mock_device_config, mock_display_manager)
        refresh_task.current_plugin_id = None
        refresh_task.current_plugin_instance_name = None

        refresh_task.refresh_current_plugin()

        # Should not call manual_update
        mock_manual_update.assert_not_called()

    @patch('src.refresh_task.RefreshTask.manual_update')
    @patch('src.refresh_task.RefreshTask._get_current_datetime')
    def test_next_plugin(self, mock_get_dt, mock_manual_update):
        """Test next_plugin advances to next plugin in playlist"""
        from src.refresh_task import RefreshTask

        mock_device_config = Mock()
        mock_display_manager = Mock()

        # Create mock playlist with plugins
        plugin1 = PluginInstance("weather", "Station 1", {}, {})
        plugin2 = PluginInstance("clock", "Clock 1", {}, {})

        playlist = Playlist("Test", "00:00", "24:00")
        playlist.plugins = [plugin1, plugin2]
        playlist.current_plugin_index = 0

        playlist_manager = PlaylistManager()
        playlist_manager.playlists = [playlist]

        mock_device_config.get_playlist_manager.return_value = playlist_manager
        mock_get_dt.return_value = datetime(2025, 1, 1, 12, 0, 0)

        refresh_task = RefreshTask(mock_device_config, mock_display_manager)
        refresh_task.next_plugin()

        # Verify manual_update was called with next plugin
        assert mock_manual_update.called
        call_args = mock_manual_update.call_args[0][0]
        assert call_args.plugin_instance == plugin2  # Should be plugin2

    @patch('src.refresh_task.RefreshTask.manual_update')
    @patch('src.refresh_task.RefreshTask._get_current_datetime')
    def test_previous_plugin(self, mock_get_dt, mock_manual_update):
        """Test previous_plugin goes back in playlist"""
        from src.refresh_task import RefreshTask

        mock_device_config = Mock()
        mock_display_manager = Mock()

        plugin1 = PluginInstance("weather", "Station 1", {}, {})
        plugin2 = PluginInstance("clock", "Clock 1", {}, {})
        plugin3 = PluginInstance("calendar", "Cal 1", {}, {})

        playlist = Playlist("Test", "00:00", "24:00")
        playlist.plugins = [plugin1, plugin2, plugin3]
        playlist.current_plugin_index = 2  # Currently at plugin3

        playlist_manager = PlaylistManager()
        playlist_manager.playlists = [playlist]

        mock_device_config.get_playlist_manager.return_value = playlist_manager
        mock_get_dt.return_value = datetime(2025, 1, 1, 12, 0, 0)

        refresh_task = RefreshTask(mock_device_config, mock_display_manager)
        refresh_task.previous_plugin()

        # Verify manual_update was called with previous plugin
        assert mock_manual_update.called
        call_args = mock_manual_update.call_args[0][0]
        assert call_args.plugin_instance == plugin2  # Should go back to plugin2

    @patch('src.refresh_task.RefreshTask.manual_update')
    def test_handle_plugin_specific_button(self, mock_manual_update):
        """Test handle_plugin_specific_button delegates to plugin"""
        from src.refresh_task import RefreshTask

        mock_device_config = Mock()
        mock_display_manager = Mock()

        refresh_task = RefreshTask(mock_device_config, mock_display_manager)
        refresh_task.current_plugin_id = "weather"
        refresh_task.current_plugin_instance_name = "Station 1"

        button_params = {"button_id": 2, "extra": "data"}
        refresh_task.handle_plugin_specific_button(button_params)

        # Verify ButtonRefresh was created with correct params
        assert mock_manual_update.called
        call_args = mock_manual_update.call_args[0][0]
        assert call_args.plugin_id == "weather"
        assert call_args.plugin_instance_name == "Station 1"
        assert call_args.button_params == button_params

    @patch('src.refresh_task.RefreshTask._get_current_datetime')
    def test_next_plugin_no_active_playlist(self, mock_get_dt):
        """Test next_plugin when no playlist is active"""
        from src.refresh_task import RefreshTask

        mock_device_config = Mock()
        mock_display_manager = Mock()

        playlist_manager = PlaylistManager()
        playlist_manager.playlists = []

        mock_device_config.get_playlist_manager.return_value = playlist_manager
        mock_get_dt.return_value = datetime(2025, 1, 1, 12, 0, 0)

        refresh_task = RefreshTask(mock_device_config, mock_display_manager)

        # Should not raise exception
        refresh_task.next_plugin()
