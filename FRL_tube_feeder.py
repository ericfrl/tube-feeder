#!/usr/bin/env python3
"""
FRL Tube Feeder Controller
Canonical module for controlling the tube feeder Arduino.

This is the single source of truth - other projects should import from here
or from ~/.frl/FRL_tube_feeder.py (system-wide copy).
"""

import serial
import serial.tools.list_ports
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
        self.position = 0.0
        self.last_response = ""
        self._callback = None  # Optional callback for received data

    def set_callback(self, callback):
        """Set callback function for received data: callback(line)"""
        self._callback = callback

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

            return True
        except serial.SerialException:
            return False

    def disconnect(self):
        """Disconnect from Arduino."""
        self.reading = False
        if self.serial and self.serial.is_open:
            self.serial.close()
        self.connected = False

    def _read_loop(self):
        """Background thread to read serial responses."""
        while self.reading and self.serial and self.serial.is_open:
            try:
                if self.serial.in_waiting:
                    line = self.serial.readline().decode('utf-8', errors='ignore').strip()
                    if line:
                        self.last_response = line
                        # Parse position responses
                        if line.startswith("POS:"):
                            try:
                                self.position = float(line[4:])
                            except:
                                pass
                        if self._callback:
                            self._callback(line)
            except:
                pass
            time.sleep(0.01)

    def send(self, command):
        """Send a command to the Arduino."""
        if not self.connected:
            return False

        try:
            cmd = command.strip() + '\n'
            self.serial.write(cmd.encode())
            self.serial.flush()
            return True
        except serial.SerialException:
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
