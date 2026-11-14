from sqlalchemy.orm import Session

from ..schemas.validation import SequenceValidationRequest
from .agricultural_validator import AgriculturalValidator


class RotationEngine:
    def __init__(self, session: Session):
        self.validator = AgriculturalValidator(session)

    def evaluate_sequence(self, request: SequenceValidationRequest | dict):
        return self.validator.validate_sequence(request)
