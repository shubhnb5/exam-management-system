"""Per-field form errors, returned as `detail = {"errors": {field: message}}`
so frontends can show each message under the matching input."""

from fastapi import HTTPException, status


def field_errors(errors: dict[str, str]) -> HTTPException:
    """Invalid values (422)."""
    return HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail={"errors": errors})


def field_conflicts(errors: dict[str, str]) -> HTTPException:
    """Values already used by another record (409)."""
    return HTTPException(status_code=status.HTTP_409_CONFLICT, detail={"errors": errors})
