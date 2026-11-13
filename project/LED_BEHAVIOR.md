# JARVIS LED Behavior — Current Fixed Specification

## Hardware output

- Use only the onboard WS2812 RGB LED on GPIO21.
- GPIO2 is not used. No external status LED is configured or driven.

## State table

| State | Onboard RGB LED — GPIO21 |
|---|---|
| Power ON | Red blinking exactly five times |
| Startup greeting | LED off while the local greeting "Hi there!" plays |
| Standby / waiting for "Jarvis" | Yellow breathing |
| Listening to user | Blue blinking |
| Processing the request | Alternating green and blue blinking |
| AI speaking / responding | Green blinking |

## Transition requirements

- Run the five red startup flashes once only; never restart the sequence during normal state transitions.
- Play "Hi there!" once after successful startup and audio initialization.
- Keep the LED off during the local startup greeting.
- After the greeting finishes, enter standby with a yellow breathing effect.
- Listening, processing, and speaking each replace the previous animation; patterns must never run concurrently.
- Use non-blocking timer-driven animation so LED effects do not block microphone capture, network I/O, or speaker playback.
- Use GPIO21 only. Do not initialize GPIO2 or any external LED output.
