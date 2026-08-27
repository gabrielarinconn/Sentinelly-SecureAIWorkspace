from backend.domain.entities import CopilotUsage
from backend.domain.ports import CopilotUsageRepository


class GetCopilotUsageUseCase:
    def __init__(self, copilot_usage_repository: CopilotUsageRepository):
        self._usage = copilot_usage_repository

    def execute(self) -> CopilotUsage:
        return self._usage.get_for_actor()
