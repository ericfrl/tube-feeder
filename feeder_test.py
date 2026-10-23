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

from FRL_tube_feeder import TubeFeederController


class InteractiveTubeFeeder(TubeFeederController):
    """Extended controller with interactive print output."""

    def __init__(self, port=None, baudrate=115200):
        super().__init__(port, baudrate)
        self.set_callback(lambda line: print(f"<< {line}"))

    def connect(self):
        """Connect with verbose output."""
        if self.port is None:
            self.port = self.find_arduino()
            if self.port is None:
                print("ERROR: Could not find Arduino. Please specify port.")
                return False

        result = super().connect()
        if result:
            print(f"Connected to {self.port}")
        else:
            print(f"ERROR: Could not connect to {self.port}")
        return result

    def disconnect(self):
        """Disconnect with verbose output."""
        super().disconnect()
        print("Disconnected")

    def send(self, command):
        """Send with verbose output."""
        if not self.connected:
            print("ERROR: Not connected")
            return False
        result = super().send(command)
        if result:
            print(f">> {command}")
        else:
            print("ERROR: Send failed")
        return result


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

    controller = InteractiveTubeFeeder(port)

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
