from __future__ import annotations


class DomainOperationError(Exception):
    def __init__(self, message: str, code: str = "OPERATION_ERROR", path: str = "") -> None:
        super().__init__(message)
        self.message = str(message or "")
        self.code = str(code or "OPERATION_ERROR")
        self.path = str(path or "")


class ValidationOperationError(DomainOperationError):
    def __init__(self, message: str, code: str = "VALIDATION_ERROR", path: str = "") -> None:
        super().__init__(message=message, code=code, path=path)


class NotFoundOperationError(DomainOperationError):
    def __init__(self, message: str, code: str = "NOT_FOUND", path: str = "") -> None:
        super().__init__(message=message, code=code, path=path)


class ConflictOperationError(DomainOperationError):
    def __init__(self, message: str, code: str = "CONFLICT", path: str = "") -> None:
        super().__init__(message=message, code=code, path=path)

