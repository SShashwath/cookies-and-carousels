"""Create FoodMatch tables"""

from alembic import op
import sqlalchemy as sa


revision = '0001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    postgres = op.get_context().dialect.name == "postgresql"
    host_constraint = [] if postgres else [
        sa.ForeignKeyConstraint(['id', 'host_participant_id'], ['participants.room_id', 'participants.id'], name='fk_room_host', ondelete='NO ACTION', initially='DEFERRED', deferrable=True, use_alter=True)
    ]
    op.create_table('restaurants',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('source', sa.String(length=12), nullable=False),
    sa.Column('provider_id', sa.String(length=300), nullable=False),
    sa.Column('google_place_id', sa.String(length=300), nullable=True),
    sa.Column('name', sa.String(length=240), nullable=True),
    sa.Column('address', sa.String(length=300), nullable=True),
    sa.Column('latitude', sa.Float(), nullable=True),
    sa.Column('longitude', sa.Float(), nullable=True),
    sa.Column('cuisines', sa.JSON(), nullable=True),
    sa.Column('rating', sa.Float(), nullable=True),
    sa.Column('price_level', sa.String(length=40), nullable=True),
    sa.Column('photo_reference', sa.String(length=300), nullable=True),
    sa.Column('maps_url', sa.String(length=500), nullable=True),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('google_place_id'),
    sa.UniqueConstraint('provider_id')
    )
    op.create_table('rooms',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('room_code', sa.String(length=6), nullable=False),
    sa.Column('host_participant_id', sa.Uuid(), nullable=False),
    sa.Column('status', sa.String(length=12), nullable=False),
    sa.Column('location_name', sa.String(length=100), nullable=False),
    sa.Column('latitude', sa.Float(), nullable=False),
    sa.Column('longitude', sa.Float(), nullable=False),
    sa.Column('radius_km', sa.Float(), nullable=False),
    sa.Column('min_budget', sa.Integer(), nullable=False),
    sa.Column('max_budget', sa.Integer(), nullable=False),
    sa.Column('cuisine_preferences', sa.JSON(), nullable=False),
    sa.Column('vegetarian_only', sa.Boolean(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('round_number', sa.Integer(), nullable=False),
    sa.CheckConstraint("status IN ('lobby', 'swiping', 'finished')", name='ck_room_status'),
    sa.CheckConstraint('min_budget >= 0 AND max_budget >= min_budget', name='ck_room_budget'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('room_code'),
    *host_constraint,
    )
    op.create_index(op.f('ix_rooms_expires_at'), 'rooms', ['expires_at'], unique=False)
    op.create_table('participants',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('room_id', sa.Uuid(), nullable=False),
    sa.Column('display_name', sa.String(length=40), nullable=False),
    sa.Column('name_key', sa.String(length=120), nullable=False),
    sa.Column('guest_token_hash', sa.String(length=64), nullable=False),
    sa.Column('joined_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('completed_swiping', sa.Boolean(), nullable=False),
    sa.Column('left_at', sa.DateTime(timezone=True), nullable=True),
    sa.ForeignKeyConstraint(['room_id'], ['rooms.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('guest_token_hash'),
    sa.UniqueConstraint('room_id', 'id', name='uq_participant_room_id'),
    sa.UniqueConstraint('room_id', 'name_key', name='uq_participant_room_name')
    )
    if postgres:
        op.create_foreign_key(
            "fk_room_host", "rooms", "participants", ["id", "host_participant_id"],
            ["room_id", "id"], deferrable=True, initially="DEFERRED",
        )
    op.create_table('room_restaurants',
    sa.Column('room_id', sa.Uuid(), nullable=False),
    sa.Column('restaurant_id', sa.Uuid(), nullable=False),
    sa.Column('display_order', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['restaurant_id'], ['restaurants.id'], ),
    sa.ForeignKeyConstraint(['room_id'], ['rooms.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('room_id', 'restaurant_id'),
    sa.UniqueConstraint('room_id', 'display_order', name='uq_pool_order')
    )
    op.create_table('matches',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('room_id', sa.Uuid(), nullable=False),
    sa.Column('restaurant_id', sa.Uuid(), nullable=False),
    sa.Column('match_score', sa.Float(), nullable=False),
    sa.Column('like_count', sa.Integer(), nullable=False),
    sa.Column('dislike_count', sa.Integer(), nullable=False),
    sa.Column('participant_count', sa.Integer(), nullable=False),
    sa.Column('unanimous', sa.Boolean(), nullable=False),
    sa.Column('rank', sa.Integer(), nullable=False),
    sa.Column('calculated_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['room_id', 'restaurant_id'], ['room_restaurants.room_id', 'room_restaurants.restaurant_id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('room_id', 'rank', name='uq_match_rank'),
    sa.UniqueConstraint('room_id', 'restaurant_id', name='uq_room_match')
    )
    op.create_table('votes',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('room_id', sa.Uuid(), nullable=False),
    sa.Column('participant_id', sa.Uuid(), nullable=False),
    sa.Column('restaurant_id', sa.Uuid(), nullable=False),
    sa.Column('vote', sa.String(length=7), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.CheckConstraint("vote IN ('like', 'dislike')", name='ck_vote_choice'),
    sa.ForeignKeyConstraint(['room_id', 'participant_id'], ['participants.room_id', 'participants.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['room_id', 'restaurant_id'], ['room_restaurants.room_id', 'room_restaurants.restaurant_id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('room_id', 'participant_id', 'restaurant_id', name='uq_room_vote')
    )


def downgrade():
    op.drop_table('votes')
    op.drop_table('matches')
    op.drop_table('room_restaurants')
    if op.get_context().dialect.name == "postgresql":
        op.drop_constraint("fk_room_host", "rooms", type_="foreignkey")
    op.drop_table('participants')
    op.drop_index(op.f('ix_rooms_expires_at'), table_name='rooms')
    op.drop_table('rooms')
    op.drop_table('restaurants')
