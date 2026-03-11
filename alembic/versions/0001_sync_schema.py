"""sync schema

Revision ID: 0001
Revises: 
Create Date: 2026-03-11

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── users ──────────────────────────────────────────────────────────────
    op.add_column(
        "users",
        sa.Column(
            "gender",
            sa.Enum("MALE", "FEMALE", "PREFER_NOT_TO_SAY", name="gender_type", native_enum=False),
            nullable=True,
        ),
    )
    op.add_column(
        "users",
        sa.Column("profile_pic_url", sa.String(500), nullable=True),
    )

    # ── agent_profiles ─────────────────────────────────────────────────────
    op.add_column("agent_profiles", sa.Column("age", sa.Integer(), nullable=True))
    op.add_column("agent_profiles", sa.Column("town", sa.String(100), nullable=True))
    op.add_column("agent_profiles", sa.Column("city", sa.String(100), nullable=True))
    op.add_column("agent_profiles", sa.Column("country", sa.String(100), nullable=True))
    op.add_column(
        "agent_profiles",
        sa.Column(
            "education_level",
            sa.Enum("HIGHSCHOOL", "CERTIFICATE", "DIPLOMA", "DEGREE", "ADVANCED",
                    name="education_level_enum", native_enum=False),
            nullable=True,
        ),
    )
    op.add_column(
        "agent_profiles",
        sa.Column(
            "english_level",
            sa.Enum("BASIC", "ADVANCED", "FLUENT", name="english_level_enum", native_enum=False),
            nullable=True,
        ),
    )
    op.add_column(
        "agent_profiles",
        sa.Column(
            "computer_experience",
            sa.Enum("NO_EXPERIENCE", "YRS_0_2", "YRS_2_5", "YRS_5_PLUS",
                    name="computer_exp_enum", native_enum=False),
            nullable=True,
        ),
    )
    op.add_column(
        "agent_profiles",
        sa.Column("have_a_computer", sa.Boolean(), nullable=False, server_default="false"),
    )
    op.add_column(
        "agent_profiles",
        sa.Column("access_to_internet", sa.Boolean(), nullable=False, server_default="false"),
    )
    op.add_column("agent_profiles", sa.Column("internet_speed", sa.String(100), nullable=True))
    op.add_column("agent_profiles", sa.Column("description_of_self", sa.Text(), nullable=True))
    op.add_column(
        "agent_profiles",
        sa.Column("total_bookings", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "agent_profiles",
        sa.Column("total_refunds", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "agent_profiles",
        sa.Column("total_disputes", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "agent_profiles",
        sa.Column("avg_rating", sa.Float(), nullable=False, server_default="0.0"),
    )
    op.add_column(
        "agent_profiles",
        sa.Column("hours_worked", sa.Float(), nullable=False, server_default="0.0"),
    )
    op.add_column(
        "agent_profiles",
        sa.Column("quality_score", sa.Float(), nullable=False, server_default="0.0"),
    )
    # change id_type from VARCHAR to enum string
    op.alter_column(
        "agent_profiles",
        "id_type",
        existing_type=sa.String(100),
        type_=sa.Enum("NATIONAL", "DRIVING_LICENSE", "PASSPORT",
                      name="id_type_agent", native_enum=False),
        existing_nullable=True,
    )

    # ── partner_profiles ───────────────────────────────────────────────────
    op.add_column(
        "partner_profiles",
        sa.Column("services_provided", postgresql.ARRAY(sa.String()), nullable=True),
    )
    op.alter_column(
        "partner_profiles",
        "id_type",
        existing_type=sa.String(100),
        type_=sa.Enum("NATIONAL", "DRIVING_LICENSE", "PASSPORT",
                      name="id_type_partner", native_enum=False),
        existing_nullable=True,
    )


def downgrade() -> None:
    # partner_profiles
    op.alter_column(
        "partner_profiles", "id_type",
        existing_type=sa.Enum("NATIONAL", "DRIVING_LICENSE", "PASSPORT",
                              name="id_type_partner", native_enum=False),
        type_=sa.String(100), existing_nullable=True,
    )
    op.drop_column("partner_profiles", "services_provided")

    # agent_profiles
    op.alter_column(
        "agent_profiles", "id_type",
        existing_type=sa.Enum("NATIONAL", "DRIVING_LICENSE", "PASSPORT",
                              name="id_type_agent", native_enum=False),
        type_=sa.String(100), existing_nullable=True,
    )
    for col in ["quality_score", "hours_worked", "avg_rating", "total_disputes",
                "total_refunds", "total_bookings", "description_of_self",
                "internet_speed", "access_to_internet", "have_a_computer",
                "computer_experience", "english_level", "education_level",
                "country", "city", "town", "age"]:
        op.drop_column("agent_profiles", col)

    # users
    op.drop_column("users", "profile_pic_url")
    op.drop_column("users", "gender")
