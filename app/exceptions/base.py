class AppError(Exception):
    code = "app_error"
    message = "Application error"

    def __init__(self, message: str | None = None) -> None:
        self.message = message or self.message
        super().__init__(self.message)


class AuthenticationError(AppError):
    code = "authentication_failed"
    message = "Authentication failed"


class SecurityProviderNotConfiguredError(AppError):
    code = "security_provider_not_configured"
    message = "Authentication security provider is not configured"


class UserNotFoundError(AppError):
    code = "user_not_found"
    message = "User not found"


class UserInactiveError(AppError):
    code = "user_inactive"
    message = "User is inactive"


class AccessDeniedError(AppError):
    code = "access_denied"
    message = "Access denied"


class SelfDeactivationError(AppError):
    code = "self_deactivation_forbidden"
    message = "Administrator cannot deactivate the current account"
