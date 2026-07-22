from fastapi import HTTPException, status


class AppError(Exception):
    def __init__(self, message: str = "Application error") -> None:
        self.message = message
        super().__init__(self.message)


class NotFoundError(AppError):
    def __init__(self, resource: str = "Resource") -> None:
        super().__init__(f"{resource} not found")


class DependencyUnavailableError(AppError):
    def __init__(self, service: str = "Service") -> None:
        super().__init__(f"{service} is unavailable")


def http_error(status_code: int, detail: str) -> HTTPException:
    return HTTPException(status_code=status_code, detail=detail)


def not_found(detail: str = "Not found") -> HTTPException:
    return http_error(status.HTTP_404_NOT_FOUND, detail)


def service_unavailable(detail: str = "Service unavailable") -> HTTPException:
    return http_error(status.HTTP_503_SERVICE_UNAVAILABLE, detail)
