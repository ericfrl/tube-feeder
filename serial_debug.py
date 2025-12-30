#!/usr/bin/env python3
"""Simple serial debug script"""
import serial
import time

# Change this to your Arduino port
PORT = '/dev/ttyACM3'
BAUD = 115200

print(f"Opening {PORT} at {BAUD} baud...")
ser = serial.Serial(PORT, BAUD, timeout=1)
time.sleep(2)  # Wait for Arduino reset

print("Connected. Clearing buffers...")
ser.reset_input_buffer()

# Read any startup messages
time.sleep(0.5)
while ser.in_waiting:
    line = ser.readline().decode('utf-8', errors='ignore').strip()
    print(f"Startup: {line}")

print("\nSending '?' command...")
ser.write(b'?\n')
ser.flush()

print("Waiting for response...")
time.sleep(0.5)

while ser.in_waiting:
    line = ser.readline().decode('utf-8', errors='ignore').strip()
    print(f"Response: {line}")

print("\nSending 'J+' command...")
ser.write(b'J+\n')
ser.flush()

time.sleep(0.5)
while ser.in_waiting:
    line = ser.readline().decode('utf-8', errors='ignore').strip()
    print(f"Response: {line}")

print("\nMotor should be jogging. Press Enter to stop...")
input()

ser.write(b'STOP\n')
ser.flush()

time.sleep(0.5)
while ser.in_waiting:
    line = ser.readline().decode('utf-8', errors='ignore').strip()
    print(f"Response: {line}")

ser.close()
print("Done.")
