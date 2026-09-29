class DomainError(Exception):
    """Error de negocio. Los adaptadores de entrada lo traducen a su protocolo."""

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class BadRequestError(DomainError):
    pass


class UnauthorizedError(DomainError):
    pass


class ForbiddenError(DomainError):
    pass


class ServiceUnavailableError(DomainError):
    """Dependencia externa (LLM, servidor MCP) no disponible. El mensaje no expone detalles internos."""


class EmployeeNotFoundError(DomainError):
    """El empleado no existe en el almacén de permisos."""


class SearchRejectedError(DomainError):
    """El servidor de búsqueda rechazó la petición con un error estructurado (no reintentable)."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
