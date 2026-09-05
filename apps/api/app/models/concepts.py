import uuid

from sqlalchemy import Enum, Float, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, uuid_pk

concept_relation_enum = Enum(
    "prerequisite_of", "part_of", "related_to", name="concept_relation", create_type=False
)


class Concept(Base, TimestampMixin):
    __tablename__ = "concepts"

    id: Mapped[uuid.UUID] = uuid_pk()
    course_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("courses.id", ondelete="CASCADE"), nullable=False
    )
    slug: Mapped[str] = mapped_column(Text, nullable=False)
    canonical_name: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    # Duplicate concepts are merged rather than deleted, so old attempts keep
    # pointing somewhere meaningful.
    merged_into_id: Mapped[uuid.UUID | None] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("concepts.id")
    )


class ConceptEdge(Base):
    __tablename__ = "concept_edges"

    from_concept_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("concepts.id", ondelete="CASCADE"), primary_key=True
    )
    to_concept_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("concepts.id", ondelete="CASCADE"), primary_key=True
    )
    relation: Mapped[str] = mapped_column(concept_relation_enum, primary_key=True)
    weight: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)


class ConceptEvidence(Base):
    __tablename__ = "concept_evidence"

    concept_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("concepts.id", ondelete="CASCADE"), primary_key=True
    )
    chunk_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("source_chunks.id", ondelete="CASCADE"), primary_key=True
    )
    note: Mapped[str | None] = mapped_column(Text)


class Misconception(Base):
    __tablename__ = "misconceptions"

    id: Mapped[uuid.UUID] = uuid_pk()
    concept_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("concepts.id", ondelete="CASCADE"), nullable=False
    )
    slug: Mapped[str] = mapped_column(Text, nullable=False)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    # Written as the learner would hold it, not as "the student got X wrong".
    incorrect_model: Mapped[str] = mapped_column(Text, nullable=False)
    typical_signals: Mapped[str | None] = mapped_column(Text)
