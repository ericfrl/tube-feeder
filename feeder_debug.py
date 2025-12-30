#!/usr/bin/env python3
"""
Tube Feeder Interactive Debug Tool
Comprehensive diagnostics for the tube feeder system.

Usage:
    python3 feeder_debug.py [port]
"""

import serial
import serial.tools.list_ports
import sys
import time
import os

class FeederDebugger:
    def __init__(self):
        self.serial = None
        self.port = None
        self.connected = False

    def list_ports(self):
        """List all available serial ports with details."""
        print("\n" + "="*60)
        print("AVAILABLE SERIAL PORTS")
        print("="*60)

        ports = serial.tools.list_ports.comports()
        if not ports:
            print("No serial ports found!")
            return []

        for i, port in enumerate(ports):
            print(f"\n[{i}] {port.device}")
            print(f"    Description: {port.description}")
            print(f"    Manufacturer: {port.manufacturer}")
            print(f"    VID:PID: {hex(port.vid) if port.vid else 'N/A'}:{hex(port.pid) if port.pid else 'N/A'}")
            print(f"    Serial#: {port.serial_number}")

            # Identify device type
            if port.vid == 0x2341:  # Arduino
                print(f"    --> ARDUINO DEVICE")
            elif port.vid == 0x16C0 and port.pid == 0x0483:  # Teensy
                print(f"    --> TEENSY DEVICE (Robot Controller)")
            elif 'teensy' in (port.description or '').lower():
                print(f"    --> TEENSY DEVICE (Robot Controller)")

        return ports

    def find_arduino_uno(self):
        """Auto-detect Arduino Uno port."""
        ports = serial.tools.list_ports.comports()

        # Look for Arduino Uno specifically
        for port in ports:
            if port.vid == 0x2341:  # Arduino vendor ID
                if port.pid in [0x0043, 0x0001, 0x0243]:  # Uno PIDs
                    return port.device
            desc = (port.description or '').lower()
            if 'arduino' in desc and 'uno' in desc:
                return port.device
            if 'arduino' in desc and 'teensy' not in desc:
                return port.device

        return None

    def connect(self, port=None):
        """Connect to the Arduino."""
        if port is None:
            port = self.find_arduino_uno()
            if port is None:
                print("ERROR: Could not auto-detect Arduino Uno.")
                print("Please specify port manually.")
                return False

        self.port = port
        print(f"\nConnecting to {port}...")

        try:
            self.serial = serial.Serial(port, 115200, timeout=1)
            time.sleep(2)  # Wait for Arduino reset
            self.serial.reset_input_buffer()
            self.connected = True
            print(f"Connected to {port}")
            return True
        except serial.SerialException as e:
            print(f"ERROR: Could not connect: {e}")
            return False

    def disconnect(self):
        """Disconnect from Arduino."""
        if self.serial and self.serial.is_open:
            self.serial.close()
        self.connected = False
        print("Disconnected")

    def send_command(self, cmd, wait_response=True, timeout=1.0):
        """Send a command and optionally wait for response."""
        if not self.connected:
            print("ERROR: Not connected")
            return None

        try:
            # Clear input buffer
            self.serial.reset_input_buffer()

            # Send command
            full_cmd = cmd.strip() + '\n'
            self.serial.write(full_cmd.encode())
            self.serial.flush()
            print(f">> {cmd}")

            if not wait_response:
                return True

            # Wait for response
            time.sleep(0.1)
            response_lines = []
            end_time = time.time() + timeout

            while time.time() < end_time:
                if self.serial.in_waiting:
                    line = self.serial.readline().decode('utf-8', errors='ignore').strip()
                    if line:
                        response_lines.append(line)
                        print(f"<< {line}")
                else:
                    if response_lines:
                        break
                    time.sleep(0.05)

            return response_lines
        except serial.SerialException as e:
            print(f"ERROR: {e}")
            return None

    def test_connection(self):
        """Test basic serial connection."""
        print("\n" + "="*60)
        print("TEST 1: Serial Connection")
        print("="*60)

        response = self.send_command("?")
        if response and any("STATUS" in line for line in response):
            print("\n[PASS] Serial communication working")
            return True
        else:
            print("\n[FAIL] No valid response from Arduino")
            print("       Check: Sketch uploaded? Correct baud rate?")
            return False

    def test_motor_jog(self):
        """Test motor jogging."""
        print("\n" + "="*60)
        print("TEST 2: Motor Jog")
        print("="*60)

        print("\nStarting forward jog...")
        response = self.send_command("J+")

        if response and any("JOGGING" in line for line in response):
            print("[PASS] Jog command accepted")
        else:
            print("[WARN] No jog confirmation received")

        print("\nMotor should be spinning now.")
        print("Check: Is the motor actually moving?")

        input("\nPress Enter to stop...")

        self.send_command("STOP")
        print("Motor stopped")

        answer = input("\nDid the motor move? (y/n): ").strip().lower()
        if answer == 'y':
            print("[PASS] Motor jog working")
            return True
        else:
            print("[FAIL] Motor not moving")
            print("       Check: 24V power? Wiring? DIP switches?")
            return False

    def test_direction(self):
        """Test both directions."""
        print("\n" + "="*60)
        print("TEST 3: Direction Control")
        print("="*60)

        print("\nTesting FORWARD direction (J+)...")
        self.send_command("J+", wait_response=False)
        time.sleep(1)
        self.send_command("STOP")
        fwd_dir = input("Which direction did it move? (left/right/none): ").strip().lower()

        print("\nTesting REVERSE direction (J-)...")
        self.send_command("J-", wait_response=False)
        time.sleep(1)
        self.send_command("STOP")
        rev_dir = input("Which direction did it move? (left/right/none): ").strip().lower()

        if fwd_dir != 'none' and rev_dir != 'none' and fwd_dir != rev_dir:
            print("\n[PASS] Both directions working")
            return True
        else:
            print("\n[WARN] Direction issue detected")
            if fwd_dir == rev_dir:
                print("       Motor moves same direction for both commands")
                print("       Check: DIR wire connected to D3?")
            return False

    def test_speed(self):
        """Test speed control."""
        print("\n" + "="*60)
        print("TEST 4: Speed Control")
        print("="*60)

        print("\nTesting SLOW speed (5 mm/sec)...")
        self.send_command("S5")
        self.send_command("J+", wait_response=False)
        time.sleep(2)
        self.send_command("STOP")

        print("\nTesting FAST speed (30 mm/sec)...")
        self.send_command("S30")
        self.send_command("J+", wait_response=False)
        time.sleep(2)
        self.send_command("STOP")

        # Reset to default
        self.send_command("S10")

        answer = input("\nDid the second run feel faster? (y/n): ").strip().lower()
        if answer == 'y':
            print("[PASS] Speed control working")
            return True
        else:
            print("[WARN] Speed difference not noticeable")
            return False

    def test_distance(self):
        """Test distance feeding."""
        print("\n" + "="*60)
        print("TEST 5: Distance Feed")
        print("="*60)

        self.send_command("HOME")
        print("\nFeeding 50mm forward...")
        self.send_command("F50")

        time.sleep(3)  # Wait for move to complete

        response = self.send_command("POS")
        print(f"\nPosition after feed: {response}")

        print("\nRetracting 50mm...")
        self.send_command("R50")

        time.sleep(3)

        response = self.send_command("POS")
        print(f"\nPosition after retract: {response}")

        return True

    def test_voltage(self):
        """Guide for voltage testing."""
        print("\n" + "="*60)
        print("TEST 6: Voltage Check (Manual)")
        print("="*60)

        print("""
Use a multimeter to check these voltages:

1. Arduino 5V to GND: Should read ~5V
2. 24V PSU + to -: Should read ~24V
3. Driver +VDC to GND: Should read ~24V
4. Driver OPTO to GND: Should read ~5V

With motor stopped:
5. D2 (PUL) to GND: Should read ~0V

With 'j+' running:
6. D2 (PUL) to GND: Should fluctuate or read ~2-3V average
""")

        input("\nPress Enter when done checking voltages...")
        return True

    def run_all_tests(self):
        """Run all diagnostic tests."""
        print("\n" + "="*60)
        print("TUBE FEEDER DIAGNOSTIC SUITE")
        print("="*60)

        results = {}

        results['connection'] = self.test_connection()

        if results['connection']:
            results['motor_jog'] = self.test_motor_jog()

            if results['motor_jog']:
                results['direction'] = self.test_direction()
                results['speed'] = self.test_speed()
                results['distance'] = self.test_distance()

        results['voltage'] = self.test_voltage()

        # Summary
        print("\n" + "="*60)
        print("TEST SUMMARY")
        print("="*60)

        for test, passed in results.items():
            status = "[PASS]" if passed else "[FAIL]"
            print(f"  {status} {test}")

        passed_count = sum(1 for v in results.values() if v)
        total_count = len(results)
        print(f"\nPassed: {passed_count}/{total_count}")

    def interactive_mode(self):
        """Interactive command mode."""
        print("\n" + "="*60)
        print("INTERACTIVE DEBUG MODE")
        print("="*60)
        print("""
Commands:
  ports     - List all serial ports
  connect   - Connect to Arduino (auto-detect)
  connect <port> - Connect to specific port
  disconnect - Disconnect

  ?         - Get status
  j+        - Jog forward
  j-        - Jog reverse
  stop      - Stop motion
  f <mm>    - Feed distance
  r <mm>    - Retract distance
  s <speed> - Set speed (mm/sec)
  home      - Zero position
  pos       - Get position

  test      - Run all diagnostic tests
  test connection - Test serial connection
  test motor - Test motor jog
  test direction - Test both directions
  test speed - Test speed control
  test distance - Test distance feed
  test voltage - Voltage check guide

  raw <cmd> - Send raw command
  quit      - Exit
""")

        while True:
            try:
                cmd = input("\ndebug> ").strip()
            except (EOFError, KeyboardInterrupt):
                break

            if not cmd:
                continue

            parts = cmd.split()
            action = parts[0].lower()

            if action == 'quit' or action == 'exit' or action == 'q':
                break

            elif action == 'ports':
                self.list_ports()

            elif action == 'connect':
                port = parts[1] if len(parts) > 1 else None
                self.connect(port)

            elif action == 'disconnect':
                self.disconnect()

            elif action == 'test':
                if not self.connected:
                    print("Not connected. Use 'connect' first.")
                    continue

                if len(parts) > 1:
                    test_name = parts[1].lower()
                    if test_name == 'connection':
                        self.test_connection()
                    elif test_name == 'motor':
                        self.test_motor_jog()
                    elif test_name == 'direction':
                        self.test_direction()
                    elif test_name == 'speed':
                        self.test_speed()
                    elif test_name == 'distance':
                        self.test_distance()
                    elif test_name == 'voltage':
                        self.test_voltage()
                    else:
                        print(f"Unknown test: {test_name}")
                else:
                    self.run_all_tests()

            elif action == 'raw':
                if not self.connected:
                    print("Not connected. Use 'connect' first.")
                    continue
                if len(parts) > 1:
                    self.send_command(' '.join(parts[1:]))
                else:
                    print("Usage: raw <command>")

            elif action in ['?', 'j+', 'j-', 'stop', 'home', 'pos']:
                if not self.connected:
                    print("Not connected. Use 'connect' first.")
                    continue
                self.send_command(action.upper())

            elif action == 'f':
                if not self.connected:
                    print("Not connected. Use 'connect' first.")
                    continue
                if len(parts) > 1:
                    self.send_command(f"F{parts[1]}")
                else:
                    print("Usage: f <mm>")

            elif action == 'r':
                if not self.connected:
                    print("Not connected. Use 'connect' first.")
                    continue
                if len(parts) > 1:
                    self.send_command(f"R{parts[1]}")
                else:
                    print("Usage: r <mm>")

            elif action == 's':
                if not self.connected:
                    print("Not connected. Use 'connect' first.")
                    continue
                if len(parts) > 1:
                    self.send_command(f"S{parts[1]}")
                else:
                    print("Usage: s <speed>")

            else:
                print(f"Unknown command: {action}")
                print("Type 'quit' to exit or just press Enter for help")


def main():
    print("="*60)
    print("TUBE FEEDER DEBUG TOOL")
    print("="*60)

    debugger = FeederDebugger()

    # List ports first
    ports = debugger.list_ports()

    # Try to auto-connect
    port = sys.argv[1] if len(sys.argv) > 1 else None

    if port or debugger.find_arduino_uno():
        print("\n" + "-"*60)
        if debugger.connect(port):
            print("\nConnection successful!")
        else:
            print("\nConnection failed. Use 'connect <port>' to try manually.")
    else:
        print("\nNo Arduino Uno detected. Use 'connect <port>' to connect manually.")

    # Enter interactive mode
    debugger.interactive_mode()

    # Cleanup
    if debugger.connected:
        debugger.send_command("STOP", wait_response=False)
        debugger.disconnect()

    print("\nGoodbye!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
