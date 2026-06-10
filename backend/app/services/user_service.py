from app.core.mock_identity import MOCK_USER_EMAIL, MOCK_USER_FULL_NAME, MOCK_USER_ID
from app.repositories.user_repository import UserRepository
from app.schemas.user import UserRead


class UserService:
    def __init__(self, user_repository: UserRepository) -> None:
        self.user_repository = user_repository

    def get_current_user_placeholder(self) -> UserRead:
        user = self.user_repository.get_by_id(MOCK_USER_ID)
        if user is None:
            user = self.user_repository.create(
                user_id=MOCK_USER_ID,
                email=MOCK_USER_EMAIL,
                full_name=MOCK_USER_FULL_NAME,
            )

        return UserRead.model_validate(user)
