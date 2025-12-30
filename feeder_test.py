#!/usr/bin/env python3
"""
Tube Feeder Test Script
Interactive terminal for testing the tube feeder Arduino controller.

Usage:
    python3 feeder_test.py [port]

    If port is not specified, will auto-detect Arduino Uno.
"""

import serial
import serial.tools.list_ports
import sys
import time
import threading

class TubeFeederController:
    def __init__(self, port=None, baudrate=115200):
        self.port = port
        self.baudrate = baudrate
        self.serial = None
        self.connected = False
        self.reading = False
        self.read_thread = None

    def find_arduino(self):
        """Auto-detect Arduino Uno port."""
        ports = serial.tools.list_ports.comports()

        # First pass: look specifically for Arduino Uno
        for port in ports:
            desc = port.description.lower() if port.description else ''
            if 'arduino' in desc and 'uno' in desc:
                return port.device

        # Second pass: look for Arduino (not Teensy)
        for port in ports:
            desc = port.description.lower() if port.description else ''
            if 'arduino' in desc and 'teensy' not in desc:
                return port.device

        # Third pass: try to identify by VID/PID (Arduino Uno = 2341:0043 or 2341:0001)
        for port in ports:
            if port.vid == 0x2341:  # Arduino vendor ID
                if port.pid in [0x0043, 0x0001, 0x0243]:  # Uno PIDs
                    return port.device

        return None

    def connect(self):
        """Connect to the Arduino."""
        if self.port is None:
            self.port = self.find_arduino()
            if self.port is None:
                print("ERROR: Could not find Arduino. Please specify port.")
                return False

        try:
            self.serial = serial.Serial(self.port, self.baudrate, timeout=0.1)
            time.sleep(2)  # Wait for Arduino reset

            # Clear any startup messages
            self.serial.reset_input_buffer()
            self.serial.reset_output_buffer()

            self.connected = True

            # Start read thread
            self.reading = True
            self.read_thread = threading.Thread(target=self._read_loop, daemon=True)
            self.read_thread.start()

            print(f"Connected to {self.port}")
            return True
        except serial.SerialException as e:
            print(f"ERROR: Could not connect to {self.port}: {e}")
            return False

    def disconnect(self):
        """Disconnect from Arduino."""
        self.reading = False
        if self.serial and self.serial.is_open:
            self.serial.close()
        self.connected = False
        print("Disconnected")

    def _read_loop(self):
        """Background thread to read serial responses."""
        while self.reading and self.serial and self.serial.is_open:
            try:
                if self.serial.in_waiting:
                    line = self.serial.readline().decode('utf-8', errors='ignore').strip()
                    if line:
                        print(f"<< {line}")
            except:
                pass
            time.sleep(0.01)

    def send(self, command):
        """Send a command to the Arduino."""
        if not self.connected:
            print("ERROR: Not connected")
            return False

        try:
            cmd = command.strip() + '\n'
            self.serial.write(cmd.encode())
            self.serial.flush()  # Ensure data is sent immediately
            print(f">> {command}")
            return True
        except serial.SerialException as e:
            print(f"ERROR: Send failed: {e}")
            return False

    def feed(self, mm):
        """Feed forward by specified mm."""
        return self.send(f"F{mm}")

    def retract(self, mm):
        """Retract by specified mm."""
        return self.send(f"R{mm}")

    def set_speed(self, mm_per_sec):
        """Set feed speed in mm/sec."""
        return self.send(f"S{mm_per_sec}")

    def jog_forward(self):
        """Start jogging forward."""
        return self.send("J+")

    def jog_reverse(self):
        """Start jogging reverse."""
        return self.send("J-")

    def stop(self):
        """Stop all motion."""
        return self.send("STOP")

    def home(self):
        """Set current position as zero."""
        return self.send("HOME")

    def get_position(self):
        """Query current position."""
        return self.send("POS")

    def get_status(self):
        """Query full status."""
        return self.send("?")


def print_help():
    """Print available commands."""
    print("""
=== Tube Feeder Test Commands ===
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
  help       - Show this help
  quit       - Exit
=================================
""")


def main():
    # Get port from command line or auto-detect
    port = sys.argv[1] if len(sys.argv) > 1 else None

    controller = TubeFeederController(port)

    print("=== Tube Feeder Test Tool ===")
    print("Connecting...")

    if not controller.connect():
        print("Failed to connect. Check that Arduino is connected and port is correct.")
        print("Usage: python3 feeder_test.py [port]")
        print("\nAvailable ports:")
        for p in serial.tools.list_ports.comports():
            print(f"  {p.device} - {p.description}")
        return 1

    time.sleep(0.5)  # Let startup messages come through
    print_help()

    try:
        while True:
            try:
                user_input = input("\nfeeder> ").strip().lower()
            except EOFError:
                break

            if not user_input:
                continue

            parts = user_input.split()
            cmd = parts[0]

            if cmd == 'quit' or cmd == 'exit' or cmd == 'q':
                break
            elif cmd == 'help' or cmd == 'h':
                print_help()
            elif cmd == 'f' or cmd == 'feed':
                if len(parts) >= 2:
                    controller.feed(parts[1])
                else:
                    print("Usage: f <mm>")
            elif cmd == 'r' or cmd == 'retract':
                if len(parts) >= 2:
                    controller.retract(parts[1])
                else:
                    print("Usage: r <mm>")
            elif cmd == 's' or cmd == 'speed':
                if len(parts) >= 2:
                    controller.set_speed(parts[1])
                else:
                    print("Usage: s <speed_mm_sec>")
            elif cmd == 'j+':
                controller.jog_forward()
            elif cmd == 'j-':
                controller.jog_reverse()
            elif cmd == 'stop':
                controller.stop()
            elif cmd == 'home':
                controller.home()
            elif cmd == 'pos':
                controller.get_position()
            elif cmd == '?':
                controller.get_status()
            elif cmd == 'raw':
                if len(parts) >= 2:
                    controller.send(' '.join(parts[1:]))
                else:
                    print("Usage: raw <command>")
            else:
                print(f"Unknown command: {cmd}. Type 'help' for commands.")

    except KeyboardInterrupt:
        print("\nInterrupted")

    finally:
        controller.stop()  # Safety stop
        controller.disconnect()

    return 0


if __name__ == "__main__":
    sys.exit(main())
