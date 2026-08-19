"""Domain errors for cycle lifecycle operations."""


class CycleError(Exception):
    """Base exception for cycle domain errors."""


class CycleAlreadyOpenError(CycleError):
    """Raised when opening would violate the single-open-cycle rule."""


class CycleNotOpenError(CycleError):
    """Raised when closing a cycle that is not currently open."""


class CycleClosedError(CycleError):
    """Raised when advancing a stage on an encerrado cycle."""


class StageTransitionError(CycleError):
    """Raised when stage preconditions are not satisfied."""
