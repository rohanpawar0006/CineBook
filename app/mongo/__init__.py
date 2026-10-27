"""MongoDB Big-Data & Analytics package for CineBook."""

from app.mongo.schemas import COLLECTION_SCHEMAS, apply_collection_schemas

__all__ = ["COLLECTION_SCHEMAS", "apply_collection_schemas"]
