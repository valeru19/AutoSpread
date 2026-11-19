from app.models.payment_instrument import PaymentInstrument
from app.repositories.base_repository import BaseRepository


class PaymentInstrumentRepository(BaseRepository[PaymentInstrument]):
    """Репозиторий инструментов оплаты."""

    def __init__(self) -> None:
        super().__init__(PaymentInstrument)


payment_instrument_repository = PaymentInstrumentRepository()
