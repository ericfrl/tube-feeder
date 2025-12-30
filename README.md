# Tube Feeder Toolkit

External tube feeder control system for the AR4 robot arms.
Uses Arduino Uno R3 + DM322T driver + NEMA 17 stepper motor.

## Overview

This toolkit provides control for an external tube feeding mechanism (similar to a 3D printer extruder) that can push/pull tubing. It integrates with the main AR4 HMI and can also be used standalone.

## Hardware

### Components
| Component | Model | Specs |
|-----------|-------|-------|
| Motor | NEMA 17 (17HS19-2004S1) | 59Ncm, 2A, 1.8°/step |
| Driver | DM322T | 18-30V DC, up to 2.2A |
| Controller | Arduino Uno R3 | USB serial @ 115200 baud |
| Power | 24V DC | 2.5-3A recommended |

### Wiring Diagram

```
Arduino Uno          DM322T Driver          Power Supply (24V DC)
-----------          -------------          --------------------
    D2  -----------> PUL                         +24V ---------> +VDC
    D3  -----------> DIR                         +24V ---------> OPTO
    5V  -----------> OPTO                        GND  ---------> GND
   GND  -----------> GND

                     ENA - Leave disconnected (driver defaults to enabled)

Motor (17HS19-2004S1)
---------------------
    Black  ---------> A+
    Green  ---------> A-
    Red    ---------> B+
    Blue   ---------> B-
```

### DM322T DIP Switch Settings
For 2A motor current:
- SW1 = ON
- SW2 = ON
- SW3 = OFF

Microstepping (adjust as needed):
- SW4, SW5, SW6 = per driver manual

### Important Notes
- Arduino Uno appears on `/dev/ttyACM3` (may vary)
- Common ground required between Arduino GND and 24V PSU GND
- OPTO must be connected to 5V for signal optocoupler to work
- ENA pin left disconnected (driver defaults to enabled state)

## Calibration

**Calibrated value: 17.62 steps/mm**

To recalibrate:
1. Mark starting position
2. Run `f 100` (feed 100mm)
3. Measure actual distance traveled
4. Calculate: `new_steps_per_mm = current_value × (commanded / actual)`
5. Update `stepsPerMm` in `tube_feeder.ino`
6. Re-upload sketch

## Files

| File | Description |
|------|-------------|
| `tube_feeder.ino` | Arduino sketch - handles step/dir generation |
| `feeder_test.py` | Standalone test script & TubeFeederController class |
| `feeder_config.py` | Configuration calculator for steps/mm |
| `serial_debug.py` | Low-level serial debugging script |
| `feeder_debug.py` | Interactive diagnostic tool |
| `run_feeder_test.sh` | Full launcher (port scan, camera, etc.) |
| `AR4_feeder_test.py` | AR4 HMI with tube feeder integrated |

## Quick Start

### 1. Flash Arduino
```bash
# Open in Arduino IDE
arduino tube_feeder/tube_feeder.ino
# Select Board: Arduino Uno
# Select Port: /dev/ttyACM3 (or appropriate port)
# Upload
```

### 2. Test Standalone
```bash
python3 tube_feeder/feeder_test.py
# Commands: j+, j-, stop, f 10, r 10, s 20, ?, home
```

### 3. Run with AR4 HMI
```bash
./tube_feeder/run_feeder_test.sh --noscan --nocam
# Click "Connect" on Tube Feeder panel
# Use buttons or arrow keys to control
```

## Serial Commands (115200 baud)

| Command | Description | Example |
|---------|-------------|---------|
| `F<mm>` | Feed forward | `F100` = feed 100mm |
| `R<mm>` | Retract | `R50` = retract 50mm |
| `S<val>` | Set speed (mm/sec) | `S10` = 10mm/sec |
| `J+` | Jog forward (continuous) | |
| `J-` | Jog reverse (continuous) | |
| `STOP` | Stop all motion | |
| `HOME` | Set position to zero | |
| `POS` | Report position | |
| `?` | Report full status | |

## Python Test Script Commands

```
f <mm>     - Feed forward (e.g., 'f 100')
r <mm>     - Retract (e.g., 'r 50')
s <speed>  - Set speed mm/sec (e.g., 's 10')
j+         - Jog forward (continuous)
j-         - Jog reverse (continuous)
stop       - Stop motion
home       - Set current position as zero
pos        - Get current position
?          - Get full status
raw <cmd>  - Send raw command
quit       - Exit
```

## HMI Integration

The Tube Feeder panel replaces the J9 axis in the "Linear Axes" section and includes:

- **Status indicator** - Shows Connected/Disconnected
- **Position display** - Current position in mm
- **Speed slider** - 1-50 mm/sec
- **Distance input** - Feed/Retract specific distance
- **Jog buttons** - "<< Back" and "Fwd >>"
- **Home button** - Zero the position
- **Connect button** - Connect/Disconnect from Arduino

### Keyboard Shortcuts
| Key | Action |
|-----|--------|
| Left Arrow | Feed forward (hold) |
| Right Arrow | Retract (hold) |

### System Integration
- `coordinated_home_all()` - Homes tube feeder along with robots
- `emergency_stop_all()` - Stops tube feeder along with robots

## Troubleshooting

### Motor not moving
1. Check 24V power supply is on
2. Verify wiring connections
3. Check Arduino is on correct port: `ls /dev/ttyACM*`
4. Run `feeder_debug.py` for diagnostics

### Wrong direction
Swap motor wires: exchange A+ with A- OR B+ with B-

### Steps/mm incorrect
Recalibrate using the procedure above

### Serial connection issues
```bash
# Check available ports
ls /dev/ttyACM* /dev/ttyUSB*

# Check permissions
sudo chmod 666 /dev/ttyACM3

# Add user to dialout group (permanent fix)
sudo usermod -a -G dialout $USER
# Then log out and back in
```

### Port detection issues
The Arduino Uno should auto-detect, but if not, specify manually:
```bash
python3 feeder_test.py /dev/ttyACM3
```

## Development Notes

### Adding to Main AR4 HMI
When ready to merge into the main `AR4_1.py`:
1. Add import: `from feeder_test import TubeFeederController`
2. Add RUN variables for tube feeder state
3. Copy the Tube Feeder Frame UI code
4. Copy the tube feeder functions
5. Update `coordinated_home_all()` and `emergency_stop_all()`

### Session History
- **Initial setup**: NEMA 17 + DM322T + Arduino Uno
- **Wiring issue**: Required common ground between Arduino and 24V PSU
- **OPTO connection**: Must connect to 5V for optocoupler to work
- **ENA pin**: Leave disconnected (driver defaults to enabled)
- **Port detection**: Arduino Uno on /dev/ttyACM3 (not ACM5)
- **Calibration**: 17.62 steps/mm for current roller setup
