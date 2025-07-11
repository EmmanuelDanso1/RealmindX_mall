"""changed db to postgresql

Revision ID: 90c9e72ace72
Revises: 
Create Date: 2025-07-11 06:26:02.545639

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '90c9e72ace72'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('category',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(length=100), nullable=False),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_category')),
    sa.UniqueConstraint('name', name=op.f('uq_category_name'))
    )
    op.create_table('info_document',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('title', sa.String(length=255), nullable=False),
    sa.Column('source', sa.String(length=255), nullable=False),
    sa.Column('filename', sa.String(length=255), nullable=False),
    sa.Column('image', sa.String(length=255), nullable=True),
    sa.Column('upload_date', sa.DateTime(), nullable=True),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_info_document'))
    )
    op.create_table('newsletter_subscriber',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('email', sa.String(length=120), nullable=False),
    sa.Column('is_verified', sa.Boolean(), nullable=True),
    sa.Column('subscribed_on', sa.DateTime(), nullable=True),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_newsletter_subscriber')),
    sa.UniqueConstraint('email', name=op.f('uq_newsletter_subscriber_email'))
    )
    op.create_table('promotion_flier',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('title', sa.String(length=150), nullable=False),
    sa.Column('image_filename', sa.String(length=200), nullable=False),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_promotion_flier'))
    )
    op.create_table('user',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('username', sa.String(length=80), nullable=False),
    sa.Column('email', sa.String(length=120), nullable=False),
    sa.Column('password', sa.String(length=200), nullable=False),
    sa.Column('date_joined', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_user')),
    sa.UniqueConstraint('email', name=op.f('uq_user_email')),
    sa.UniqueConstraint('username', name=op.f('uq_user_username'))
    )
    op.create_table('order',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('order_id', sa.String(length=50), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=True),
    sa.Column('full_name', sa.String(length=120), nullable=False),
    sa.Column('email', sa.String(length=120), nullable=False),
    sa.Column('address', sa.Text(), nullable=False),
    sa.Column('total_amount', sa.Float(), nullable=False),
    sa.Column('payment_method', sa.String(length=50), nullable=False),
    sa.Column('status', sa.String(length=50), nullable=True),
    sa.Column('date_created', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['user_id'], ['user.id'], name=op.f('fk_order_user_id_user')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_order')),
    sa.UniqueConstraint('order_id', name=op.f('uq_order_order_id'))
    )
    op.create_table('product',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(length=120), nullable=False),
    sa.Column('description', sa.Text(), nullable=False),
    sa.Column('price', sa.Float(), nullable=False),
    sa.Column('discount_percentage', sa.Float(), nullable=True),
    sa.Column('image_filename', sa.String(length=120), nullable=True),
    sa.Column('in_stock', sa.Boolean(), nullable=True),
    sa.Column('date_created', sa.DateTime(), nullable=True),
    sa.Column('author', sa.String(length=120), nullable=True),
    sa.Column('brand', sa.String(length=120), nullable=True),
    sa.Column('grade', sa.String(length=50), nullable=True),
    sa.Column('level', sa.String(length=50), nullable=True),
    sa.Column('subject', sa.String(length=100), nullable=True),
    sa.Column('category_id', sa.Integer(), nullable=True),
    sa.ForeignKeyConstraint(['category_id'], ['category.id'], name=op.f('fk_product_category_id_category')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_product'))
    )
    op.create_table('order_item',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('order_id', sa.Integer(), nullable=False),
    sa.Column('product_id', sa.Integer(), nullable=False),
    sa.Column('quantity', sa.Integer(), nullable=False),
    sa.Column('price', sa.Float(), nullable=False),
    sa.ForeignKeyConstraint(['order_id'], ['order.id'], name=op.f('fk_order_item_order_id_order')),
    sa.ForeignKeyConstraint(['product_id'], ['product.id'], name=op.f('fk_order_item_product_id_product')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_order_item'))
    )
    op.create_table('product_rating',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('product_id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('rating', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['product_id'], ['product.id'], name=op.f('fk_product_rating_product_id_product')),
    sa.ForeignKeyConstraint(['user_id'], ['user.id'], name=op.f('fk_product_rating_user_id_user')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_product_rating'))
    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('product_rating')
    op.drop_table('order_item')
    op.drop_table('product')
    op.drop_table('order')
    op.drop_table('user')
    op.drop_table('promotion_flier')
    op.drop_table('newsletter_subscriber')
    op.drop_table('info_document')
    op.drop_table('category')
    # ### end Alembic commands ###
