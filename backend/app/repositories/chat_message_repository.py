from app.models.chat_message import ChatMessage
from app.repositories.base_repository import BaseRepository


class ChatMessageRepository(BaseRepository[ChatMessage]):
    """Репозиторий сообщений чата."""

    def __init__(self) -> None:
        super().__init__(ChatMessage)


chat_message_repository = ChatMessageRepository()
