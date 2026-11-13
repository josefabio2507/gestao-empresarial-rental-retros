"""Unifica as heads de migrations do deploy.

Esta migration não altera tabelas; apenas conecta a cadeia histórica
da migration de observações à cadeia principal.
"""

revision = "b0c1d2e3f4a5"
down_revision = ("z7q8r9s0t1u2", "z9a8b7c6d5e4")
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    pass
