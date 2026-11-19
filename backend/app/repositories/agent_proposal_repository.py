from app.models.agent_proposal import AgentProposal
from app.repositories.base_repository import BaseRepository


class AgentProposalRepository(BaseRepository[AgentProposal]):
    """Репозиторий предложений агентов."""

    def __init__(self) -> None:
        super().__init__(AgentProposal)


agent_proposal_repository = AgentProposalRepository()
