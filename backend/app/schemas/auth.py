from pydantic import BaseModel, field_validator


class SignupRequest(BaseModel):
    email: str
    password: str
    full_name: str

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        cleaned_value = value.strip().lower()
        if "@" not in cleaned_value or "." not in cleaned_value.rsplit("@", 1)[-1]:
            raise ValueError("A valid email address is required.")
        return cleaned_value

    @field_validator("password")
    @classmethod
    def validate_password(cls, value: str) -> str:
        if len(value) < 8:
            raise ValueError("Password must be at least 8 characters.")
        if not any(character.isupper() for character in value):
            raise ValueError("Password must include at least 1 capital letter.")
        if not any(character.isdigit() for character in value):
            raise ValueError("Password must include at least 1 number.")
        if not any(not character.isalnum() for character in value):
            raise ValueError("Password must include at least 1 special character.")
        return value

    @field_validator("full_name")
    @classmethod
    def validate_full_name(cls, value: str) -> str:
        cleaned_value = value.strip()
        if cleaned_value == "":
            raise ValueError("Full name is required.")

        return cleaned_value


class LoginRequest(BaseModel):
    email: str
    password: str

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        return value.strip().lower()
