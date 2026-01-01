/*
 * Tube Feeder Controller + Wake Word LED
 * For Arduino Uno R3 + DM322T Driver + NEMA 17 (17HS19-2004S1)
 *
 * Wiring:
 *   Uno D2  -> DM322T PUL+
 *   Uno D3  -> DM322T DIR+
 *   Uno D4  -> DM322T ENA+
 *   Uno GND -> DM322T PUL-, DIR-, ENA-
 *   Uno D13 -> LED (built-in) for wake word indicator
 *
 * Serial Commands (115200 baud):
 *   F<mm>   - Feed forward (e.g., F100 = feed 100mm)
 *   R<mm>   - Retract (e.g., R50 = retract 50mm)
 *   S<val>  - Set speed in mm/sec (e.g., S10 = 10mm/sec)
 *   J+      - Jog forward (continuous until STOP)
 *   J-      - Jog reverse (continuous until STOP)
 *   STOP    - Stop all motion
 *   HOME    - Set current position as zero
 *   POS     - Report current position
 *   ?       - Report status
 *   L<0-3>  - Set LED state (0=off, 1=idle/dim, 2=active/bright, 3=processing)
 */

// Pin definitions
#define PIN_STEP 2
#define PIN_DIR  3
#define PIN_ENA  4
#define PIN_LED  13  // Built-in LED for wake word indicator

// Direction constants
#define DIR_FORWARD  HIGH
#define DIR_REVERSE  LOW

// Configuration - ADJUST THESE FOR YOUR SETUP
float stepsPerMm = 17.62;      // Steps per mm (calibrated)
float maxSpeedMmSec = 50.0;    // Maximum speed in mm/sec
float defaultSpeedMmSec = 10.0; // Default speed in mm/sec
float accelMmSec2 = 100.0;     // Acceleration in mm/sec^2

// State variables
volatile bool isRunning = false;
volatile bool stopRequested = false;
bool jogMode = false;
int jogDirection = DIR_FORWARD;
int ledState = 0;  // Wake word LED state

float currentPositionMm = 0.0;
float targetSpeedMmSec = 10.0;
unsigned long stepDelayUs = 1000;

// Serial buffer
String inputBuffer = "";

void setup() {
  // Initialize pins
  pinMode(PIN_STEP, OUTPUT);
  pinMode(PIN_DIR, OUTPUT);
  pinMode(PIN_ENA, OUTPUT);
  pinMode(PIN_LED, OUTPUT);

  digitalWrite(PIN_STEP, LOW);
  digitalWrite(PIN_DIR, DIR_FORWARD);
  digitalWrite(PIN_ENA, LOW);  // LOW = enabled for most drivers
  digitalWrite(PIN_LED, LOW);  // LED off initially

  // Calculate initial step delay
  updateStepDelay();

  // Initialize serial
  Serial.begin(115200);
  delay(100);  // Give serial time to initialize

  Serial.println("TUBE_FEEDER_READY");
  Serial.println("Commands: F<mm>, R<mm>, S<speed>, J+, J-, STOP, HOME, POS, ?");
}

void loop() {
  // Handle serial input
  while (Serial.available()) {
    char c = Serial.read();
    if (c == '\n' || c == '\r') {
      if (inputBuffer.length() > 0) {
        processCommand(inputBuffer);
        inputBuffer = "";
      }
    } else {
      inputBuffer += c;
    }
  }

  // Handle jog mode
  if (jogMode && !stopRequested) {
    doStep(jogDirection);
    delayMicroseconds(stepDelayUs);
  }
}

void processCommand(String cmd) {
  cmd.trim();
  cmd.toUpperCase();

  if (cmd.length() == 0) return;

  char firstChar = cmd.charAt(0);

  // STOP command - highest priority
  if (cmd == "STOP") {
    stopMotion();
    Serial.println("OK STOPPED");
    return;
  }

  // Don't accept new motion commands while running
  if (isRunning && firstChar != '?') {
    Serial.println("ERR BUSY");
    return;
  }

  switch (firstChar) {
    case 'F': {
      // Feed forward
      float mm = cmd.substring(1).toFloat();
      if (mm > 0) {
        feedDistance(mm, DIR_FORWARD);
      } else {
        Serial.println("ERR INVALID_DISTANCE");
      }
      break;
    }

    case 'R': {
      // Retract
      float mm = cmd.substring(1).toFloat();
      if (mm > 0) {
        feedDistance(mm, DIR_REVERSE);
      } else {
        Serial.println("ERR INVALID_DISTANCE");
      }
      break;
    }

    case 'S': {
      // Set speed
      float speed = cmd.substring(1).toFloat();
      if (speed > 0 && speed <= maxSpeedMmSec) {
        targetSpeedMmSec = speed;
        updateStepDelay();
        Serial.print("OK SPEED=");
        Serial.println(targetSpeedMmSec);
      } else {
        Serial.print("ERR SPEED_RANGE 0-");
        Serial.println(maxSpeedMmSec);
      }
      break;
    }

    case 'J': {
      // Jog mode
      if (cmd.length() >= 2) {
        char dir = cmd.charAt(1);
        if (dir == '+') {
          startJog(DIR_FORWARD);
        } else if (dir == '-') {
          startJog(DIR_REVERSE);
        } else {
          Serial.println("ERR USE J+ OR J-");
        }
      }
      break;
    }

    case 'H': {
      // HOME - set current position as zero
      if (cmd == "HOME") {
        currentPositionMm = 0.0;
        Serial.println("OK HOME=0");
      }
      break;
    }

    case 'P': {
      // Position query
      if (cmd == "POS") {
        Serial.print("POS=");
        Serial.println(currentPositionMm, 2);
      }
      break;
    }

    case '?': {
      // Status query
      reportStatus();
      break;
    }

    case 'L': {
      // LED control for wake word indicator
      if (cmd.length() >= 2) {
        int state = cmd.substring(1).toInt();
        if (state >= 0 && state <= 3) {
          setLED(state);
          // Silent acknowledgment - don't spam serial
        } else {
          Serial.println("ERR LED_RANGE 0-3");
        }
      }
      break;
    }

    default:
      Serial.println("ERR UNKNOWN_CMD");
      break;
  }
}

void feedDistance(float mm, int direction) {
  isRunning = true;
  stopRequested = false;
  jogMode = false;

  digitalWrite(PIN_DIR, direction);
  delayMicroseconds(5);  // Direction setup time

  long totalSteps = (long)(mm * stepsPerMm);
  long stepsCompleted = 0;

  Serial.print("FEEDING ");
  Serial.print(mm);
  Serial.println("mm");

  while (stepsCompleted < totalSteps && !stopRequested) {
    doStep(direction);
    stepsCompleted++;
    delayMicroseconds(stepDelayUs);

    // Check for stop command
    if (Serial.available()) {
      char c = Serial.peek();
      if (c == 'S' || c == 's') {
        // Read and check for STOP
        String check = Serial.readStringUntil('\n');
        check.trim();
        check.toUpperCase();
        if (check == "STOP") {
          stopRequested = true;
        }
      }
    }
  }

  // Update position
  float actualMm = stepsCompleted / stepsPerMm;
  if (direction == DIR_FORWARD) {
    currentPositionMm += actualMm;
  } else {
    currentPositionMm -= actualMm;
  }

  isRunning = false;

  if (stopRequested) {
    Serial.println("OK STOPPED_EARLY");
  } else {
    Serial.println("OK DONE");
  }
}

void startJog(int direction) {
  jogMode = true;
  jogDirection = direction;
  isRunning = true;
  stopRequested = false;

  digitalWrite(PIN_DIR, direction);
  delayMicroseconds(5);

  Serial.print("JOGGING ");
  Serial.println(direction == DIR_FORWARD ? "FORWARD" : "REVERSE");
}

void stopMotion() {
  stopRequested = true;
  jogMode = false;
  isRunning = false;
}

void doStep(int direction) {
  digitalWrite(PIN_STEP, HIGH);
  delayMicroseconds(10);
  digitalWrite(PIN_STEP, LOW);

  // Track position
  float stepMm = 1.0 / stepsPerMm;
  if (direction == DIR_FORWARD) {
    currentPositionMm += stepMm;
  } else {
    currentPositionMm -= stepMm;
  }
}

void updateStepDelay() {
  // Calculate delay between steps for desired speed
  // speed (mm/sec) = steps/sec / steps_per_mm
  // steps/sec = speed * steps_per_mm
  // delay_us = 1,000,000 / steps_per_sec

  float stepsPerSec = targetSpeedMmSec * stepsPerMm;
  stepDelayUs = (unsigned long)(1000000.0 / stepsPerSec);

  // Minimum delay to prevent issues
  if (stepDelayUs < 100) stepDelayUs = 100;
}

void reportStatus() {
  Serial.println("--- STATUS ---");
  Serial.print("Position: ");
  Serial.print(currentPositionMm, 2);
  Serial.println(" mm");
  Serial.print("Speed: ");
  Serial.print(targetSpeedMmSec);
  Serial.println(" mm/sec");
  Serial.print("Steps/mm: ");
  Serial.println(stepsPerMm);
  Serial.print("Running: ");
  Serial.println(isRunning ? "YES" : "NO");
  Serial.print("Jog Mode: ");
  Serial.println(jogMode ? "YES" : "NO");
  Serial.print("LED State: ");
  Serial.println(ledState);
  Serial.println("--------------");
}

void setLED(int state) {
  ledState = state;
  // Use PWM for brightness levels
  switch(state) {
    case 0:  // OFF
      analogWrite(PIN_LED, 0);
      break;
    case 1:  // IDLE - dim (listening for wake word)
      analogWrite(PIN_LED, 30);
      break;
    case 2:  // ACTIVE - bright (recording command)
      analogWrite(PIN_LED, 255);
      break;
    case 3:  // PROCESSING - medium
      analogWrite(PIN_LED, 150);
      break;
  }
}
