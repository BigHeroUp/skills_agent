"""Custom errors for the Veraxis kernel runtime foundation."""


class KernelError(Exception):
    """Base error for the Veraxis kernel."""


class CapabilityNotFoundError(KernelError):
    """Raised when a capability is not registered in the kernel."""


class CapabilityExecutionError(KernelError):
    """Raised when a capability execution fails."""


class DuplicateCapabilityError(KernelError):
    """Raised when a capability name is registered more than once."""
