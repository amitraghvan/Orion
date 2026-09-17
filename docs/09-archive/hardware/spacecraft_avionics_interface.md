# Spacecraft Avionics & Sensor Interface Specification

## Optical Sensors
- **Glovebox Sensor**: Sony IMX485 industrial sensor over GigE Vision interface (1920x1080 @ 60 FPS).
- **Cabin Ambient Sensor**: 4K USB3 UVC wide-angle optical sensor.

## Accelerator Nodes
- **Primary Inference Accelerator**: NVIDIA Jetson AGX Orin Industrial (64GB ECC RAM, 275 TOPS, passive thermal cooling).
- **Secondary / Redundant Node**: Radiation-tolerant x86_64 industrial compute block.

## Power & Thermal
- 28V DC bus feed via isolated DC-DC converters.
- Thermal throttle triggers automatically at 82°C; emergency shutdown at 88°C core junction temperature.
