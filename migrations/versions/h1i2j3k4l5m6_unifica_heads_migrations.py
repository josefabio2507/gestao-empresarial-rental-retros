"""Unifica as pontas de migrations antes de aplicar a correção da RTM9D90.

Revision ID: h1i2j3k4l5m6
Revises: a0b1c2d3e4f5, g1h2i3j4k5l6
"""


revision = "h1i2j3k4l5m6"
down_revision = ("a0b1c2d3e4f5", "g1h2i3j4k5l6")
branch_labels = None
depends_on = None


def upgrade():
    # Migration de união: não há alteração adicional de schema ou dados.
    pass


def downgrade():
    pass
