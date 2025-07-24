from abc import ABC, abstractmethod
from typing import Any, Dict

class BaseAgent(ABC):
    """
    Abstract base class for all agents.
    Concrete agents must implement the run method.
    """
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}

    @abstractmethod
    async def run(self, input_data: Any, *args, **kwargs) -> Any:
        """
        Run the agent with the provided input and return the result.
        This method should be implemented as async in concrete classes.
        """
        pass

    def setup(self):
        """
        Optional setup logic before the agent runs (e.g. tool loading).
        """
        pass

    def teardown(self):
        """
        Optional teardown logic (e.g. closing resources, logging).
        """
        pass
