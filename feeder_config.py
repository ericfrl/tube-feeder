"""
Tube Feeder Configuration

Adjust these values to match your hardware setup.
This file can be imported by the main HMI when integrating the feeder.
"""

# === Hardware Configuration ===

# Motor: NEMA 17 (17HS19-2004S1)
# - Step angle: 1.8 degrees (200 steps/rev)
# - Current: 2A

# Driver: DM322T
# - Microstepping setting (set via DIP switches on driver)
MICROSTEPS = 16  # Options: 1, 2, 4, 8, 16, 32

# Mechanical
ROLLER_DIAMETER_MM = 10.0  # Diameter of the feed roller/gear
MOTOR_STEPS_PER_REV = 200  # Full steps per revolution (1.8 degree motor)

# === Calculated Values ===
# Circumference of roller = distance per revolution
ROLLER_CIRCUMFERENCE_MM = 3.14159 * ROLLER_DIAMETER_MM

# Steps per mm = (steps_per_rev * microsteps) / circumference
STEPS_PER_MM = (MOTOR_STEPS_PER_REV * MICROSTEPS) / ROLLER_CIRCUMFERENCE_MM

# === Motion Parameters ===
DEFAULT_SPEED_MM_SEC = 10.0   # Default feed speed
MAX_SPEED_MM_SEC = 50.0       # Maximum allowed speed
MIN_SPEED_MM_SEC = 0.5        # Minimum speed
ACCELERATION_MM_SEC2 = 100.0  # Acceleration (for future use)

# === Limits ===
MAX_FEED_MM = 1000.0          # Maximum single feed distance
SOFT_LIMIT_MIN_MM = -100.0    # Soft limit (retract)
SOFT_LIMIT_MAX_MM = 5000.0    # Soft limit (feed)

# === Serial Communication ===
SERIAL_BAUDRATE = 115200
SERIAL_TIMEOUT = 0.1

# === Arduino Pin Assignments (for reference) ===
# These are defined in the Arduino sketch, listed here for documentation
PIN_STEP = 2
PIN_DIR = 3
PIN_ENA = 4

# Direction logic (may need to swap depending on wiring)
DIR_FORWARD_STATE = "HIGH"  # HIGH or LOW
DIR_REVERSE_STATE = "LOW"


def print_config():
    """Print current configuration for debugging."""
    print("=== Tube Feeder Configuration ===")
    print(f"Roller diameter:  {ROLLER_DIAMETER_MM} mm")
    print(f"Microstepping:    1/{MICROSTEPS}")
    print(f"Steps per mm:     {STEPS_PER_MM:.2f}")
    print(f"Default speed:    {DEFAULT_SPEED_MM_SEC} mm/sec")
    print(f"Max speed:        {MAX_SPEED_MM_SEC} mm/sec")
    print(f"Baudrate:         {SERIAL_BAUDRATE}")
    print("=================================")


if __name__ == "__main__":
    print_config()
    print(f"\n** UPDATE the Arduino sketch with: stepsPerMm = {STEPS_PER_MM:.2f}; **")
