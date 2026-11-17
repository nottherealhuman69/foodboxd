"""remove leftovers the code no longer uses

- user_lists, custom_list_items: retired tables (replaced by custom_lists / list_items)
- edited_at on 9 tables, custom_lists.description / updated_at: never read or written
- schema_flags: only tracked the old create_tables() one-time fixes, which are done
- list_items rows whose list no longer exists (left over from user_lists); once they
  are gone the list_items -> custom_lists foreign key is fully validated
  (the real database had it as NOT VALID)

WARNING: this deletes data. In the real database, everything removed here was old
test data the app could no longer show (checked November 2026).
downgrade() brings the tables/columns back, but empty; deleted rows are not restored.

Revision ID: 0002
Revises: 0001
"""
from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None

EDITED_AT_TABLES = [
    "custom_lists", "dish_reviews", "group_list_items", "group_lists", "list_items",
    "meal_comments", "meals", "review_comments", "trylists",
]


def upgrade() -> None:
    op.execute("""
        DELETE FROM list_items li
        WHERE NOT EXISTS (SELECT 1 FROM custom_lists c WHERE c.id = li.list_id)
    """)
    op.execute("ALTER TABLE list_items VALIDATE CONSTRAINT list_items_list_id_fkey")
    op.execute("DROP TABLE custom_list_items")
    op.execute("DROP TABLE user_lists")
    op.execute("DROP TABLE schema_flags")
    for table in EDITED_AT_TABLES:
        op.execute(f"ALTER TABLE {table} DROP COLUMN edited_at")
    op.execute("ALTER TABLE custom_lists DROP COLUMN description, DROP COLUMN updated_at")


def downgrade() -> None:
    op.execute("ALTER TABLE custom_lists ADD COLUMN description TEXT, "
               "ADD COLUMN updated_at TIMESTAMP DEFAULT NOW()")
    for table in EDITED_AT_TABLES:
        op.execute(f"ALTER TABLE {table} ADD COLUMN edited_at TIMESTAMP")
    op.execute("""
        CREATE TABLE schema_flags (
            flag       VARCHAR(100) PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT NOW()
        )
    """)
    op.execute("""
        CREATE TABLE user_lists (
            id         SERIAL PRIMARY KEY,
            user_email VARCHAR(255) NOT NULL REFERENCES users(email) ON DELETE CASCADE,
            name       VARCHAR(255) NOT NULL,
            is_public  BOOLEAN NOT NULL DEFAULT TRUE,
            created_at TIMESTAMP DEFAULT NOW(),
            updated_at TIMESTAMP DEFAULT NOW()
        )
    """)
    op.execute("""
        CREATE TABLE custom_list_items (
            id              SERIAL PRIMARY KEY,
            list_id         INTEGER NOT NULL REFERENCES custom_lists(id) ON DELETE CASCADE,
            item_type       VARCHAR(20) NOT NULL CHECK (item_type IN ('dish', 'restaurant')),
            dish_name       VARCHAR(255),
            restaurant_name VARCHAR(255),
            added_at        TIMESTAMP DEFAULT NOW(),
            UNIQUE (list_id, item_type, dish_name, restaurant_name)
        )
    """)
