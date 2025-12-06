"""Data models for ERP Voice Chat System."""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


class InconsistencyType(Enum):
    """Types of data inconsistencies."""

    REFERENTIAL = "referential"
    CALCULATION = "calculation"
    FORMAT = "format"
    BUSINESS_RULE = "business_rule"


@dataclass
class DuplicateGroup:
    """Represents a group of duplicate records."""

    id: str
    table_name: str
    record_ids: List[str]
    similarity_score: float
    matching_fields: Dict[str, Any]
    status: str
    created_at: datetime
    resolved_at: Optional[datetime] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DuplicateGroup":
        """Create DuplicateGroup from dictionary."""
        return cls(
            id=data["id"],
            table_name=data["table_name"],
            record_ids=data["record_ids"],
            similarity_score=float(data["similarity_score"]),
            matching_fields=data["matching_fields"],
            status=data["status"],
            created_at=data["created_at"]
            if isinstance(data["created_at"], datetime)
            else datetime.fromisoformat(data["created_at"]),
            resolved_at=data.get("resolved_at")
            if data.get("resolved_at") is None
            or isinstance(data.get("resolved_at"), datetime)
            else datetime.fromisoformat(data["resolved_at"]),
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert DuplicateGroup to dictionary."""
        return {
            "id": self.id,
            "table_name": self.table_name,
            "record_ids": self.record_ids,
            "similarity_score": self.similarity_score,
            "matching_fields": self.matching_fields,
            "status": self.status,
            "created_at": self.created_at.isoformat(),
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
        }


@dataclass
class Inconsistency:
    """Represents a data inconsistency."""

    id: str
    type: InconsistencyType
    table_name: str
    record_id: str
    field_name: Optional[str]
    description: str
    suggested_fix: Optional[Dict[str, Any]]
    status: str
    created_at: datetime
    resolved_at: Optional[datetime] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Inconsistency":
        """Create Inconsistency from dictionary."""
        return cls(
            id=data["id"],
            type=InconsistencyType(data["type"]),
            table_name=data["table_name"],
            record_id=data["record_id"],
            field_name=data.get("field_name"),
            description=data["description"],
            suggested_fix=data.get("suggested_fix"),
            status=data["status"],
            created_at=data["created_at"]
            if isinstance(data["created_at"], datetime)
            else datetime.fromisoformat(data["created_at"]),
            resolved_at=data.get("resolved_at")
            if data.get("resolved_at") is None
            or isinstance(data.get("resolved_at"), datetime)
            else datetime.fromisoformat(data["resolved_at"]),
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert Inconsistency to dictionary."""
        return {
            "id": self.id,
            "type": self.type.value,
            "table_name": self.table_name,
            "record_id": self.record_id,
            "field_name": self.field_name,
            "description": self.description,
            "suggested_fix": self.suggested_fix,
            "status": self.status,
            "created_at": self.created_at.isoformat(),
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
        }


@dataclass
class ERPRecord:
    """Represents a generic ERP record."""

    id: str
    table_name: str
    data: Dict[str, Any]
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_dict(cls, table_name: str, data: Dict[str, Any]) -> "ERPRecord":
        """Create ERPRecord from dictionary."""
        return cls(
            id=data["id"],
            table_name=table_name,
            data=data,
            created_at=data["created_at"]
            if isinstance(data["created_at"], datetime)
            else datetime.fromisoformat(data["created_at"]),
            updated_at=data["updated_at"]
            if isinstance(data["updated_at"], datetime)
            else datetime.fromisoformat(data["updated_at"]),
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert ERPRecord to dictionary."""
        return self.data
