from abc import ABC, abstractmethod

# The three possible outcomes a rule can produce
MERGE = "MERGE"
NO_MATCH = "NO_MATCH"
DEFER = "DEFER"

class ResolutionRule(ABC):
    """
    Abstract Base Class for all resolution rules.
    Each rule evaluates a pair of entities and returns a decision.
    """
    @abstractmethod
    def evaluate(self, entity1, entity2, similarity_model):
        """
        Evaluates two entities and returns a decision tuple.

        Args:
            entity1 (dict): The first entity.
            entity2 (dict): The second entity.
            similarity_model: The semantic similarity computation model.

        Returns:
            tuple: A tuple containing (decision_status, confidence_score).
                   decision_status is one of MERGE, NO_MATCH, DEFER.
        """
        pass