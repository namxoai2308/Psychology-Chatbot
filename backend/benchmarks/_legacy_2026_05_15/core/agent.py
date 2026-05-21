from abc import ABC, abstractmethod

class BaseTherapistAgent(ABC):
    """Base class for all therapist agents used in benchmarking."""
    
    def __init__(self, name: str):
        self.name = name

    @abstractmethod
    async def get_response(self, history: str, user_msg: str) -> str:
        """Get response from the therapist agent."""
        pass

    def __str__(self):
        return f"Agent({self.name})"
