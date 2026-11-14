from app.domain.shared.errors import DomainError


class InvalidReply(DomainError):
    code = "invalid_reply"
