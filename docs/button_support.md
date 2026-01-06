# Button Support

InkyPi supports physical GPIO buttons connected to your Raspberry Pi, allowing you to interact with your display without using the web interface.

## Features

- **Generic GPIO Button Support**: Configure any GPIO button on your Raspberry Pi
- **Hardware Presets**: Pre-configured button mappings for supported displays
- **Global Actions**: Built-in actions like refresh, next/previous plugin
- **Plugin-Specific Actions**: Plugins can implement custom button handlers
- **Flexible Configuration**: JSON-based configuration via device.json

## Supported Hardware Presets

### Inky Impression 7.3" (Spectra 6)
4 built-in buttons on the side of the display:
- **Button A** (GPIO 5): Plugin-specific action
- **Button B** (GPIO 6): Plugin-specific action
- **Button C** (GPIO 16): Plugin-specific action
- **Button D** (GPIO 24): Refresh current display

### Inky Impression 13.3"
4 built-in buttons:
- **Button A** (GPIO 5): Plugin-specific action
- **Button B** (GPIO 6): Plugin-specific action
- **Button C** (GPIO 25): Plugin-specific action (Note: different from 7.3")
- **Button D** (GPIO 24): Refresh current display

## Configuration

### Quick Start with Hardware Presets

For Inky Impression 7.3" displays, add this to your `device.json`:

```json
{
  "buttons": {
    "enabled": true,
    "hardware_preset": "inky_impression_7.3"
  }
}
```

Or copy the example configuration:
```bash
cp install/config_base/buttons_inky_impression_7.3.json src/config/device.json
# Then merge the "buttons" section into your existing device.json
```

Available presets:
- `inky_impression_7.3` - For Inky Impression 7.3" displays
- `inky_impression_13.3` - For Inky Impression 13.3" displays
- `custom` - For custom button configurations

### Custom Button Configuration

For custom GPIO button setups, use the `custom` preset and define your buttons:

```json
{
  "buttons": {
    "enabled": true,
    "hardware_preset": "custom",
    "buttons": [
      {
        "id": "my_button",
        "label": "Refresh",
        "pin": 17,
        "pull_up": true,
        "bounce_time": 0.2,
        "action": "refresh_current",
        "action_params": {}
      }
    ]
  }
}
```

### Button Configuration Options

Each button supports the following options:

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `id` | string | required | Unique identifier for the button |
| `label` | string | required | Human-readable label (e.g., "A", "Refresh") |
| `pin` | integer | required | GPIO pin number (BCM numbering) |
| `pull_up` | boolean | `true` | Use internal pull-up resistor |
| `bounce_time` | float | `0.2` | Debounce time in seconds |
| `hold_time` | float | `2.0` | Long press threshold in seconds |
| `action` | string | required | Action to perform (see below) |
| `action_params` | object | `{}` | Parameters for the action |

## Available Actions

### Global Actions

These actions work regardless of which plugin is displayed:

#### `refresh_current`
Refreshes the currently displayed plugin.

```json
{
  "action": "refresh_current",
  "action_params": {}
}
```

#### `next_plugin`
Advances to the next plugin in the active playlist.

```json
{
  "action": "next_plugin",
  "action_params": {}
}
```

#### `previous_plugin`
Goes back to the previous plugin in the active playlist.

```json
{
  "action": "previous_plugin",
  "action_params": {}
}
```

### Plugin-Specific Actions

#### `plugin_specific`
Delegates the button press to the currently displayed plugin's `handle_button()` method.

```json
{
  "action": "plugin_specific",
  "action_params": {
    "button_id": 1
  }
}
```

The `button_id` parameter is passed to the plugin, allowing it to distinguish between different buttons.

## Plugin Development: Handling Buttons

Plugins can implement custom button behavior by overriding the `handle_button()` method:

```python
from plugins.base_plugin.base_plugin import BasePlugin

class MyPlugin(BasePlugin):
    def __init__(self, config, **dependencies):
        super().__init__(config, **dependencies)
        self.current_index = 0
        self.items = ["Item 1", "Item 2", "Item 3"]

    def handle_button(self, button_id: int, settings, device_config):
        """
        Handle button press events.

        Args:
            button_id: Integer ID from action_params
            settings: Plugin instance settings
            device_config: Device configuration

        Returns:
            PIL.Image: New image to display, or None to keep current
        """
        if button_id == 1:
            # Button A: Next item
            self.current_index = (self.current_index + 1) % len(self.items)
        elif button_id == 2:
            # Button B: Previous item
            self.current_index = (self.current_index - 1) % len(self.items)
        elif button_id == 3:
            # Button C: Refresh
            pass  # Just regenerate the image

        # Return updated image
        return self.generate_image(settings, device_config)
```

### Example: Weather Plugin with Station Switching

```python
class WeatherPlugin(BasePlugin):
    def __init__(self, config, **dependencies):
        super().__init__(config, **dependencies)
        self.stations = ["New York", "London", "Tokyo"]
        self.current_station = 0

    def handle_button(self, button_id, settings, device_config):
        if button_id == 1:
            # Previous station
            self.current_station = (self.current_station - 1) % len(self.stations)
        elif button_id == 2:
            # Next station
            self.current_station = (self.current_station + 1) % len(self.stations)
        elif button_id == 3:
            # Force refresh weather data
            self.update_weather_data(force=True)

        return self.generate_image(settings, device_config)
```

## Enabling Button Support

1. **Install gpiozero** (included in requirements.txt):
   ```bash
   pip install gpiozero
   ```

2. **Configure buttons** in `device.json`:
   ```json
   {
     "buttons": {
       "enabled": true,
       "hardware_preset": "inky_impression_7.3"
     }
   }
   ```

3. **Restart InkyPi**:
   ```bash
   sudo systemctl restart inkypi
   ```

4. **Verify button functionality** by pressing buttons and checking logs:
   ```bash
   sudo journalctl -u inkypi -f
   ```

## Troubleshooting

### Buttons Not Responding

1. **Check gpiozero is installed**:
   ```bash
   python3 -c "import gpiozero; print(gpiozero.__version__)"
   ```

2. **Verify button configuration**:
   - Check `enabled` is `true` in device.json
   - Verify GPIO pin numbers match your hardware
   - Check logs for initialization errors

3. **Test GPIO pins manually**:
   ```bash
   # Install pigpio if needed
   sudo apt-get install pigpio python3-pigpio

   # Test a button on GPIO 5
   python3 << EOF
   from gpiozero import Button
   button = Button(5)
   print("Press the button...")
   button.wait_for_press()
   print("Button pressed!")
   EOF
   ```

### Wrong GPIO Pin Numbers

- InkyPi uses **BCM numbering** (not BOARD numbering)
- For Inky Impression 7.3": Buttons are on GPIO 5, 6, 16, 24
- For Inky Impression 13.3": Button C uses GPIO 25 (not 16)

### Buttons Trigger Multiple Times

Increase the `bounce_time` value in your button configuration:
```json
{
  "bounce_time": 0.5
}
```

### Plugin Doesn't Handle Buttons

Ensure your plugin implements the `handle_button()` method. The default implementation logs a message but doesn't update the display.

## Advanced Configuration

### Custom Actions

You can register custom action handlers programmatically:

```python
def my_custom_action(params):
    logger.info(f"Custom action triggered with {params}")
    # Your custom logic here

button_manager.register_action_handler("my_action", my_custom_action)
```

Then use it in configuration:
```json
{
  "action": "custom",
  "action_params": {
    "handler": "my_action",
    "param1": "value1"
  }
}
```

### Long Press Support

The `hold_time` parameter can be used for future long-press implementations:
```json
{
  "hold_time": 2.0
}
```

(Currently, only press events are supported, but the infrastructure is in place for hold events.)

## GPIO Pin Reference

Common GPIO pins on Raspberry Pi (BCM numbering):

```
     3.3V  (1) (2)  5V
    GPIO2  (3) (4)  5V
    GPIO3  (5) (6)  GND
    GPIO4  (7) (8)  GPIO14
      GND  (9) (10) GPIO15
   GPIO17 (11) (12) GPIO18
   GPIO27 (13) (14) GND
   GPIO22 (15) (16) GPIO23
     3.3V (17) (18) GPIO24
   GPIO10 (19) (20) GND
    GPIO9 (21) (22) GPIO25
   GPIO11 (23) (24) GPIO8
      GND (25) (26) GPIO7
    GPIO0 (27) (28) GPIO1
    GPIO5 (29) (30) GND
    GPIO6 (31) (32) GPIO12
   GPIO13 (33) (34) GND
   GPIO19 (35) (36) GPIO16
   GPIO26 (37) (38) GPIO20
      GND (39) (40) GPIO21
```

**Inky Impression 7.3" Button Pins**: 5, 6, 16, 24
**Inky Impression 13.3" Button Pins**: 5, 6, 25, 24

## Examples

### Example 1: Simple Refresh Button

```json
{
  "buttons": {
    "enabled": true,
    "hardware_preset": "custom",
    "buttons": [
      {
        "id": "refresh_btn",
        "label": "Refresh",
        "pin": 17,
        "pull_up": true,
        "action": "refresh_current"
      }
    ]
  }
}
```

### Example 2: Playlist Navigation

```json
{
  "buttons": {
    "enabled": true,
    "hardware_preset": "custom",
    "buttons": [
      {
        "id": "prev",
        "label": "Previous",
        "pin": 22,
        "pull_up": true,
        "action": "previous_plugin"
      },
      {
        "id": "next",
        "label": "Next",
        "pin": 27,
        "pull_up": true,
        "action": "next_plugin"
      }
    ]
  }
}
```

### Example 3: Weather Station Switcher

For a weather plugin that supports multiple stations:

```json
{
  "buttons": {
    "enabled": true,
    "hardware_preset": "inky_impression_7.3",
    "buttons": [
      {
        "id": "button_a",
        "label": "A",
        "pin": 5,
        "pull_up": true,
        "action": "plugin_specific",
        "action_params": {
          "button_id": 1,
          "description": "Previous station"
        }
      },
      {
        "id": "button_b",
        "label": "B",
        "pin": 6,
        "pull_up": true,
        "action": "plugin_specific",
        "action_params": {
          "button_id": 2,
          "description": "Next station"
        }
      },
      {
        "id": "button_c",
        "label": "C",
        "pin": 16,
        "pull_up": true,
        "action": "plugin_specific",
        "action_params": {
          "button_id": 3,
          "description": "Force refresh"
        }
      },
      {
        "id": "button_d",
        "label": "D",
        "pin": 24,
        "pull_up": true,
        "action": "refresh_current"
      }
    ]
  }
}
```

## Security Considerations

- Button actions run with the same permissions as InkyPi
- Be cautious with custom action handlers
- Validate all button configuration before deployment
- Consider physical access to buttons when deploying in shared environments

## Future Enhancements

Planned features for button support:

- [ ] Long press actions (infrastructure exists, needs implementation)
- [ ] Button combinations (e.g., A+B together)
- [ ] Web UI for button configuration
- [ ] Button status API endpoint
- [ ] Haptic feedback support (if hardware available)
- [ ] Button macros (sequences of actions)

## Related Documentation

- [Building Plugins](building_plugins.md) - How to create plugins
- [Installation Guide](installation.md) - Installing InkyPi
- [Configuration Reference](configuration.md) - All config options
