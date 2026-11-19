from app.models.opportunity import Opportunity
from app.repositories.base_repository import BaseRepository


class OpportunityRepository(BaseRepository[Opportunity]):
    """Репозиторий связок opportunity."""

    def __init__(self) -> None:
        super().__init__(Opportunity)


opportunity_repository = OpportunityRepository()
