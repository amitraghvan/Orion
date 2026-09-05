"""Camera driver factory registry."""

from orion_ai.camera.interfaces import CameraDriverInterface


class CameraRegistry:
    """Registry mapping camera types to concrete driver implementations."""

    _drivers: dict[str, type[CameraDriverInterface]] = {}

    @classmethod
    def register(cls, driver_name: str, driver_cls: type[CameraDriverInterface]) -> None:
        cls._drivers[driver_name] = driver_cls

    @classmethod
    def get(cls, driver_name: str) -> type[CameraDriverInterface]:
        if driver_name not in cls._drivers:
            raise NotImplementedError(
                f"NOT IMPLEMENTED: Camera driver {driver_name} is not registered."
            )
        return cls._drivers[driver_name]
