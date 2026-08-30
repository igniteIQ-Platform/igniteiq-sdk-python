"""
IgniteIQ Vault SDK — error types.
"""

# Kept for consistency with client.py / langchain.py / llamaindex.py, not because the
# `int | None` below still needs it: PEP 604 unions evaluate fine from 3.10, and the floor
# is now >=3.10. It mattered under the old >=3.9 floor, and its ABSENCE here is what made
# both published releases fail on import for every 3.9 user with
# `TypeError: unsupported operand type(s) for |` — this was the only module missing it.
from __future__ import annotations


class VaultError(Exception):
    """Raised for all API-level errors returned by the IgniteIQ Vault API.

    Attributes
    ----------
    code : str
        Machine-readable error code.  Common values:

        - ``UNAUTHORIZED``  — invalid or missing API key
        - ``FORBIDDEN``     — key exists but lacks permission for this operation
        - ``NOT_FOUND``     — resource (org, dimension, measure) not found
        - ``RATE_LIMITED``  — request quota exceeded
        - ``BAD_REQUEST``   — malformed query payload
        - ``API_ERROR``     — unexpected server error

    message : str
        Human-readable description.

    status : int | None
        HTTP status code, if the error originated from an HTTP response.

    Example
    -------
    >>> try:
    ...     await client.query({"measures": ["fact_jobs.total_revenue"]})
    ... except VaultError as e:
    ...     print(e.code, e.status, e)
    """

    def __init__(self, code: str, message: str, status: int | None = None) -> None:
        super().__init__(message)
        self.code = code
        self.status = status

    def __repr__(self) -> str:
        return f"VaultError(code={self.code!r}, status={self.status!r}, message={str(self)!r})"
