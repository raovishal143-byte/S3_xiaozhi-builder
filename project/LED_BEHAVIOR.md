# JARVIS LED Behavior — Fixed Specification

## Hardware outputs

- Onboard addressable RGB LED data: GPIO21.
- External single-color LED control: GPIO2.
- The external LED is treated as active-high unless hardware verification proves otherwise.

## State table

| State | Onboard RGB GPIO21 | External GPIO2 |
|---|---|---|
| Power ON / startup | Green blink exactly 5 times, then off | Off |
| Standby / waiting for wake phrase | Off | Solid ON |
| Listening to user | Blue blinking | Off |
| Processing / thinking | Yellow blinking | Off |
| AI speaking / responding | Green blinking | Green blinking in sync |

## Transition requirements

- Exactly five startup green flashes. No sixth flash and no repeated startup sequence during normal operation.
- After startup and successful initialization, play the greeting "Hi there" once, then enter standby.
- In standby, GPIO2 stays continuously ON; GPIO21 is OFF.
- When listening starts, turn GPIO2 OFF and blink GPIO21 blue.
- When processing starts, stop the blue pattern and blink GPIO21 yellow.
- When speech playback starts, stop the yellow pattern and blink both outputs green in sync.
- When speech playback ends, stop both speech patterns and return to standby.
- On every state transition, cancel the previous state's LED task/pattern before starting the next one. Never allow two state patterns to run concurrently.

## Implementation notes

- Use one central state controller as the only owner of LED output.
- Use non-blocking timing; LED animation must not block microphone capture, network I/O, or audio playback.
- Keep blink timing configurable in one place. The required colors and number of startup flashes are fixed; timing may be tuned during bench testing.
- Confirm GPIO21 is the onboard RGB LED's data pin and determine its pixel protocol/color order before selecting the LED driver.
- Confirm GPIO2 external LED polarity and use a suitable series resistor.
