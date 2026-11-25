"""The owner identity used in local mode, where nobody signs in."""


class LocalOwner:
    """Implements `IdentityVerifier` for local mode: every request is the owner.

    The API only uses it after its local-request check passes.
    """

    def __init__(self, uid: str) -> None:
        self._uid = uid

    def verify(self, token: str | None) -> str:
        return self._uid
