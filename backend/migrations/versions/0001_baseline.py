"""baseline: the schema as it exists in the real database (November 2026)

This is a snapshot of what the old create_tables() built up over time, checked
against a pg_dump of the real database. It includes some leftovers the code no
longer uses (old tables, edited_at columns, schema_flags); 0002 removes them.

Existing database (already has these tables):  alembic stamp 0001
Empty database:                                 alembic upgrade head

Revision ID: 0001
Revises:
"""
from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


TABLES = [
    """
    CREATE TABLE users (
        id              SERIAL PRIMARY KEY,
        email           VARCHAR(255) NOT NULL UNIQUE,
        hashed_password VARCHAR(255) NOT NULL,
        created_at      TIMESTAMP DEFAULT NOW(),
        -- FALSE = public (follows are instant), TRUE = follow requests need approval
        is_private      BOOLEAN NOT NULL DEFAULT FALSE
    )
    """,
    """
    CREATE TABLE meals (
        id              SERIAL PRIMARY KEY,
        user_email      VARCHAR(255) NOT NULL REFERENCES users(email) ON DELETE CASCADE,
        restaurant_name VARCHAR(255) NOT NULL,
        title           VARCHAR(255),
        rating          NUMERIC(2,1) NOT NULL CHECK (rating >= 0.5 AND rating <= 5),
        review          TEXT,
        logged_at       TIMESTAMP DEFAULT NOW(),
        edited_at       TIMESTAMP,
        forked_from_id  INTEGER REFERENCES meals(id) ON DELETE SET NULL
    )
    """,
    """
    CREATE TABLE dish_reviews (
        id                 SERIAL PRIMARY KEY,
        user_email         VARCHAR(255) NOT NULL REFERENCES users(email) ON DELETE CASCADE,
        dish_name          VARCHAR(255) NOT NULL,
        type               VARCHAR(20) NOT NULL CHECK (type IN ('restaurant', 'homemade')),
        restaurant_name    VARCHAR(255),
        recipe             TEXT,
        rating             NUMERIC(2,1) NOT NULL CHECK (rating >= 0.5 AND rating <= 5),
        review             TEXT,
        logged_at          TIMESTAMP DEFAULT NOW(),
        meal_id            INTEGER REFERENCES meals(id) ON DELETE CASCADE,
        -- NULL = your own recipe, otherwise the email of the recipe's author
        recipe_owner_email VARCHAR(255) REFERENCES users(email) ON DELETE SET NULL,
        edited_at          TIMESTAMP,
        forked_from_id     INTEGER REFERENCES dish_reviews(id) ON DELETE SET NULL
    )
    """,
    """
    CREATE TABLE recipe_ingredients (
        id        SERIAL PRIMARY KEY,
        review_id INTEGER NOT NULL REFERENCES dish_reviews(id) ON DELETE CASCADE,
        position  SMALLINT NOT NULL,
        name      VARCHAR(120) NOT NULL,
        quantity  NUMERIC(8,2) NOT NULL CHECK (quantity > 0),
        unit      VARCHAR(10) NOT NULL
                  CHECK (unit IN ('g','kg','ml','l','tsp','tbsp','cup','pcs','pinch'))
    )
    """,
    """
    CREATE TABLE meal_likes (
        id         SERIAL PRIMARY KEY,
        meal_id    INTEGER NOT NULL REFERENCES meals(id) ON DELETE CASCADE,
        user_email VARCHAR(255) NOT NULL REFERENCES users(email) ON DELETE CASCADE,
        created_at TIMESTAMP DEFAULT NOW(),
        UNIQUE (meal_id, user_email)
    )
    """,
    """
    CREATE TABLE meal_comments (
        id         SERIAL PRIMARY KEY,
        meal_id    INTEGER NOT NULL REFERENCES meals(id) ON DELETE CASCADE,
        user_email VARCHAR(255) NOT NULL REFERENCES users(email) ON DELETE CASCADE,
        content    TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT NOW(),
        parent_id  INTEGER REFERENCES meal_comments(id) ON DELETE CASCADE,
        edited_at  TIMESTAMP
    )
    """,
    """
    CREATE TABLE meal_comment_likes (
        id         SERIAL PRIMARY KEY,
        comment_id INTEGER NOT NULL REFERENCES meal_comments(id) ON DELETE CASCADE,
        user_email VARCHAR(255) NOT NULL REFERENCES users(email) ON DELETE CASCADE,
        created_at TIMESTAMP DEFAULT NOW(),
        UNIQUE (comment_id, user_email)
    )
    """,
    """
    CREATE TABLE review_likes (
        id         SERIAL PRIMARY KEY,
        review_id  INTEGER NOT NULL REFERENCES dish_reviews(id) ON DELETE CASCADE,
        user_email VARCHAR(255) NOT NULL REFERENCES users(email) ON DELETE CASCADE,
        created_at TIMESTAMP DEFAULT NOW(),
        UNIQUE (review_id, user_email)
    )
    """,
    """
    CREATE TABLE review_comments (
        id         SERIAL PRIMARY KEY,
        review_id  INTEGER NOT NULL REFERENCES dish_reviews(id) ON DELETE CASCADE,
        user_email VARCHAR(255) NOT NULL REFERENCES users(email) ON DELETE CASCADE,
        content    TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT NOW(),
        parent_id  INTEGER REFERENCES review_comments(id) ON DELETE CASCADE,
        edited_at  TIMESTAMP
    )
    """,
    """
    CREATE TABLE review_comment_likes (
        id         SERIAL PRIMARY KEY,
        comment_id INTEGER NOT NULL REFERENCES review_comments(id) ON DELETE CASCADE,
        user_email VARCHAR(255) NOT NULL REFERENCES users(email) ON DELETE CASCADE,
        created_at TIMESTAMP DEFAULT NOW(),
        UNIQUE (comment_id, user_email)
    )
    """,
    """
    CREATE TABLE friendships (
        id              SERIAL PRIMARY KEY,
        requester_email VARCHAR(255) NOT NULL REFERENCES users(email) ON DELETE CASCADE,
        addressee_email VARCHAR(255) NOT NULL REFERENCES users(email) ON DELETE CASCADE,
        status          VARCHAR(20) NOT NULL DEFAULT 'pending'
                        CHECK (status IN ('pending', 'accepted', 'declined')),
        created_at      TIMESTAMP DEFAULT NOW(),
        updated_at      TIMESTAMP DEFAULT NOW(),
        UNIQUE (requester_email, addressee_email)
    )
    """,
    """
    CREATE TABLE trylists (
        id              SERIAL PRIMARY KEY,
        user_email      VARCHAR(255) NOT NULL REFERENCES users(email) ON DELETE CASCADE,
        item_type       VARCHAR(20) NOT NULL CHECK (item_type IN ('dish', 'restaurant')),
        dish_name       VARCHAR(255),
        restaurant_name VARCHAR(255),
        added_at        TIMESTAMP DEFAULT NOW(),
        edited_at       TIMESTAMP,
        UNIQUE (user_email, item_type, dish_name, restaurant_name)
    )
    """,
    """
    CREATE TABLE custom_lists (
        id          SERIAL PRIMARY KEY,
        user_email  VARCHAR(255) NOT NULL REFERENCES users(email) ON DELETE CASCADE,
        name        VARCHAR(255) NOT NULL,
        description TEXT,
        created_at  TIMESTAMP DEFAULT NOW(),
        updated_at  TIMESTAMP DEFAULT NOW(),
        is_public   BOOLEAN NOT NULL DEFAULT TRUE,
        edited_at   TIMESTAMP
    )
    """,
    """
    CREATE TABLE list_items (
        id                 SERIAL PRIMARY KEY,
        list_id            INTEGER NOT NULL REFERENCES custom_lists(id) ON DELETE CASCADE,
        item_type          VARCHAR(20) NOT NULL CHECK (item_type IN ('dish', 'restaurant', 'recipe')),
        name               VARCHAR(255) NOT NULL,
        restaurant_name    VARCHAR(255),
        note               TEXT,
        added_at           TIMESTAMP DEFAULT NOW(),
        edited_at          TIMESTAMP,
        recipe_owner_email VARCHAR(255)
    )
    """,
    # retired (replaced by list_items); dropped in 0002
    """
    CREATE TABLE custom_list_items (
        id              SERIAL PRIMARY KEY,
        list_id         INTEGER NOT NULL REFERENCES custom_lists(id) ON DELETE CASCADE,
        item_type       VARCHAR(20) NOT NULL CHECK (item_type IN ('dish', 'restaurant')),
        dish_name       VARCHAR(255),
        restaurant_name VARCHAR(255),
        added_at        TIMESTAMP DEFAULT NOW(),
        UNIQUE (list_id, item_type, dish_name, restaurant_name)
    )
    """,
    # retired (replaced by custom_lists); dropped in 0002
    """
    CREATE TABLE user_lists (
        id         SERIAL PRIMARY KEY,
        user_email VARCHAR(255) NOT NULL REFERENCES users(email) ON DELETE CASCADE,
        name       VARCHAR(255) NOT NULL,
        is_public  BOOLEAN NOT NULL DEFAULT TRUE,
        created_at TIMESTAMP DEFAULT NOW(),
        updated_at TIMESTAMP DEFAULT NOW()
    )
    """,
    """
    CREATE TABLE group_lists (
        id          SERIAL PRIMARY KEY,
        name        VARCHAR(255) NOT NULL,
        owner_email VARCHAR(255) NOT NULL REFERENCES users(email) ON DELETE CASCADE,
        created_at  TIMESTAMP DEFAULT NOW(),
        is_public   BOOLEAN NOT NULL DEFAULT FALSE,
        edited_at   TIMESTAMP
    )
    """,
    """
    CREATE TABLE group_list_members (
        id            SERIAL PRIMARY KEY,
        group_list_id INTEGER NOT NULL REFERENCES group_lists(id) ON DELETE CASCADE,
        user_email    VARCHAR(255) NOT NULL REFERENCES users(email) ON DELETE CASCADE,
        role          VARCHAR(20) NOT NULL DEFAULT 'member' CHECK (role IN ('owner', 'member')),
        status        VARCHAR(20) NOT NULL DEFAULT 'pending'
                      CHECK (status IN ('pending', 'accepted', 'declined')),
        invited_by    VARCHAR(255),
        invited_at    TIMESTAMP DEFAULT NOW(),
        responded_at  TIMESTAMP,
        UNIQUE (group_list_id, user_email)
    )
    """,
    """
    CREATE TABLE group_list_items (
        id                 SERIAL PRIMARY KEY,
        group_list_id      INTEGER NOT NULL REFERENCES group_lists(id) ON DELETE CASCADE,
        added_by           VARCHAR(255) NOT NULL REFERENCES users(email) ON DELETE CASCADE,
        item_type          VARCHAR(20) NOT NULL CHECK (item_type IN ('dish', 'restaurant', 'recipe')),
        name               VARCHAR(255) NOT NULL,
        restaurant_name    VARCHAR(255),
        note               TEXT,
        added_at           TIMESTAMP DEFAULT NOW(),
        edited_at          TIMESTAMP,
        recipe_owner_email VARCHAR(255)
    )
    """,
    # companion tags ("went with"): shown on the owner's post only
    """
    CREATE TABLE post_tags (
        id           SERIAL PRIMARY KEY,
        post_type    VARCHAR(10) NOT NULL CHECK (post_type IN ('review', 'meal')),
        post_id      INTEGER NOT NULL,
        tagged_email VARCHAR(255) NOT NULL REFERENCES users(email) ON DELETE CASCADE,
        created_at   TIMESTAMP DEFAULT NOW(),
        UNIQUE (post_type, post_id, tagged_email)
    )
    """,
    """
    CREATE TABLE post_reposts (
        id             SERIAL PRIMARY KEY,
        post_type      VARCHAR(10) NOT NULL CHECK (post_type IN ('review', 'meal')),
        post_id        INTEGER NOT NULL,
        reposter_email VARCHAR(255) NOT NULL REFERENCES users(email) ON DELETE CASCADE,
        created_at     TIMESTAMP DEFAULT NOW(),
        UNIQUE (post_type, post_id, reposter_email)
    )
    """,
    # used by the old create_tables() for one-time fixes; dropped in 0002
    """
    CREATE TABLE schema_flags (
        flag       VARCHAR(100) PRIMARY KEY,
        applied_at TIMESTAMP DEFAULT NOW()
    )
    """,
]

INDEXES = [
    "CREATE INDEX dish_reviews_fork_idx ON dish_reviews (forked_from_id)",
    "CREATE INDEX dish_reviews_meal_idx ON dish_reviews (meal_id)",
    "CREATE INDEX meals_fork_idx ON meals (forked_from_id)",
    "CREATE INDEX recipe_ingredients_review_idx ON recipe_ingredients (review_id)",
    "CREATE INDEX group_list_members_user_idx ON group_list_members (user_email, status)",
    """CREATE UNIQUE INDEX group_list_items_unique_idx ON group_list_items
           (group_list_id, item_type, LOWER(name), COALESCE(LOWER(restaurant_name), ''))""",
    """CREATE UNIQUE INDEX list_items_unique_idx ON list_items
           (list_id, item_type, name, COALESCE(restaurant_name, ''))""",
    "CREATE INDEX post_tags_lookup_idx ON post_tags (post_type, post_id)",
    "CREATE INDEX post_tags_tagged_idx ON post_tags (tagged_email, created_at DESC)",
    "CREATE INDEX post_reposts_reposter_idx ON post_reposts (reposter_email, created_at DESC)",
]

# reverse of creation order, so nothing is dropped while another table still points at it
DROP_ORDER = [
    "schema_flags", "post_reposts", "post_tags", "group_list_items", "group_list_members",
    "group_lists", "user_lists", "custom_list_items", "list_items", "custom_lists", "trylists",
    "friendships", "review_comment_likes", "review_comments", "review_likes",
    "meal_comment_likes", "meal_comments", "meal_likes", "recipe_ingredients",
    "dish_reviews", "meals", "users",
]


def upgrade() -> None:
    for sql in TABLES + INDEXES:
        op.execute(sql)


def downgrade() -> None:
    for table in DROP_ORDER:
        op.execute(f"DROP TABLE {table}")
