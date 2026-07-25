"""Create the initial fiadobot database schema."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "0001_initial_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create tables and the pg_trgm extension."""

    op.execute(sa.text("CREATE EXTENSION IF NOT EXISTS pg_trgm"))

    op.create_table(
        "clientes",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("nombre", sa.String(length=150), nullable=False, unique=True),
        sa.Column("alias", sa.String(length=150), nullable=True),
        sa.Column("telefono", sa.String(length=30), nullable=True),
        sa.Column(
            "creado_en",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.PrimaryKeyConstraint("id", name="pk_clientes"),
        sa.UniqueConstraint("nombre", name="uq_clientes_nombre"),
    )

    op.execute(
        sa.text(
            """
            CREATE INDEX IF NOT EXISTS ix_clientes_busqueda_trgm
            ON clientes
            USING GIN ((lower(nombre || ' ' || coalesce(alias, ''))) gin_trgm_ops)
            """
        )
    )

    op.create_table(
        "productos",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("nombre", sa.String(length=100), nullable=False, unique=True),
        sa.Column("precio_actual", sa.Numeric(12, 2), nullable=False),
        sa.Column(
            "activo",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
        sa.PrimaryKeyConstraint("id", name="pk_productos"),
        sa.UniqueConstraint("nombre", name="uq_productos_nombre"),
    )

    op.create_table(
        "transacciones",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column(
            "cliente_id",
            sa.Integer(),
            sa.ForeignKey("clientes.id"),
            nullable=False,
        ),
        sa.Column(
            "fecha",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("monto_total", sa.Numeric(12, 2), nullable=False),
        sa.Column(
            "estado",
            sa.String(length=20),
            nullable=False,
            server_default=sa.text("'activa'"),
        ),
        sa.Column("motivo_anulacion", sa.Text(), nullable=True),
        sa.Column("anulada_en", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("estado IN ('activa', 'anulada')", name="status_valid"),
        sa.PrimaryKeyConstraint("id", name="pk_transacciones"),
    )

    op.create_index("ix_transacciones_cliente_id", "transacciones", ["cliente_id"])

    op.create_table(
        "transaccion_detalle",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column(
            "transaccion_id",
            sa.Integer(),
            sa.ForeignKey("transacciones.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "producto_id",
            sa.Integer(),
            sa.ForeignKey("productos.id"),
            nullable=False,
        ),
        sa.Column("cantidad", sa.Numeric(10, 2), nullable=False),
        sa.Column(
            "precio_unitario_congelado",
            sa.Numeric(12, 2),
            nullable=False,
        ),
        sa.Column("subtotal", sa.Numeric(12, 2), nullable=False),
        sa.CheckConstraint("cantidad > 0", name="quantity_positive"),
        sa.CheckConstraint("subtotal >= 0", name="subtotal_non_negative"),
        sa.PrimaryKeyConstraint("id", name="pk_transaccion_detalle"),
    )

    op.create_index(
        "ix_transaccion_detalle_transaccion_id",
        "transaccion_detalle",
        ["transaccion_id"],
    )
    op.create_index(
        "ix_transaccion_detalle_producto_id",
        "transaccion_detalle",
        ["producto_id"],
    )

    op.create_table(
        "pagos",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column(
            "cliente_id",
            sa.Integer(),
            sa.ForeignKey("clientes.id"),
            nullable=False,
        ),
        sa.Column("monto", sa.Numeric(12, 2), nullable=False),
        sa.Column(
            "fecha",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.PrimaryKeyConstraint("id", name="pk_pagos"),
    )

    op.create_index("ix_pagos_cliente_id", "pagos", ["cliente_id"])

    op.create_table(
        "estado_conversacion",
        sa.Column("chat_id", sa.BigInteger(), primary_key=True, nullable=False),
        sa.Column(
            "accion_pendiente",
            sa.String(length=50),
            nullable=False,
        ),
        sa.Column(
            "contexto",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column(
            "creado_en",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.PrimaryKeyConstraint("chat_id", name="pk_estado_conversacion"),
    )

    op.create_table(
        "usuarios_autorizados",
        sa.Column("chat_id", sa.BigInteger(), primary_key=True, nullable=False),
        sa.Column("rol", sa.String(length=20), nullable=False),
        sa.Column(
            "agregado_en",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.CheckConstraint("rol IN ('vendedor', 'tester')", name="role_valid"),
        sa.PrimaryKeyConstraint("chat_id", name="pk_usuarios_autorizados"),
    )


def downgrade() -> None:
    """Drop the initial schema and extension artifacts."""

    op.drop_table("usuarios_autorizados")
    op.drop_table("estado_conversacion")
    op.drop_index("ix_pagos_cliente_id", table_name="pagos")
    op.drop_table("pagos")
    op.drop_index(
        "ix_transaccion_detalle_producto_id",
        table_name="transaccion_detalle",
    )
    op.drop_index(
        "ix_transaccion_detalle_transaccion_id",
        table_name="transaccion_detalle",
    )
    op.drop_table("transaccion_detalle")
    op.drop_index("ix_transacciones_cliente_id", table_name="transacciones")
    op.drop_table("transacciones")
    op.drop_table("productos")
    op.execute(sa.text("DROP INDEX IF EXISTS ix_clientes_busqueda_trgm"))
    op.drop_table("clientes")
