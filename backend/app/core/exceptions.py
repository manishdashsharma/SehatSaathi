class AppException(Exception):
    def __init__(self, message: str, status_code: int = 400):
        self.message = message
        self.status_code = status_code
        super().__init__(message)


class NotFoundError(AppException):
    def __init__(self, resource: str = "Resource"):
        super().__init__(f"{resource} not found", 404)


class UnauthorizedError(AppException):
    def __init__(self, message: str = "Unauthorized"):
        super().__init__(message, 401)


class ForbiddenError(AppException):
    def __init__(self, message: str = "Access forbidden"):
        super().__init__(message, 403)


class ConflictError(AppException):
    def __init__(self, message: str):
        super().__init__(message, 409)


class ValidationError(AppException):
    def __init__(self, message: str):
        super().__init__(message, 422)


class GuardrailError(AppException):
    def __init__(self, message: str = "Response blocked by safety guardrails"):
        super().__init__(message, 422)


class StorageError(AppException):
    def __init__(self, message: str = "File storage operation failed"):
        super().__init__(message, 500)


class OTPError(AppException):
    def __init__(self, message: str = "Invalid or expired OTP"):
        super().__init__(message, 400)
