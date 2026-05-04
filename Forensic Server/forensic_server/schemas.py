class LoginSchema:
    """Placeholder login schema for server compatibility."""

    required_fields = ("username", "password")

    @classmethod
    def validate(cls, payload):
        payload = payload or {}
        missing = [field for field in cls.required_fields if not payload.get(field)]
        if missing:
            raise ValueError(f"Missing required fields: {', '.join(missing)}")
        return payload
