"""Database schema setup. Runs once at startup (to be replaced by Alembic migrations)."""

import psycopg2
from psycopg2.extras import RealDictCursor

from app.core.config import DB_URL
from app.utils import with_cursor


def create_tables():
    conn = psycopg2.connect(DB_URL, cursor_factory=RealDictCursor)
    with with_cursor(conn) as cur:
        
        cur.execute("""
            CREATE TABLE IF NOT EXISTS group_lists (
                id          SERIAL PRIMARY KEY,
                name        VARCHAR(255) NOT NULL,
                owner_email VARCHAR(255) NOT NULL REFERENCES users(email) ON DELETE CASCADE,
                created_at  TIMESTAMP DEFAULT NOW()
            )
        """)
        cur.execute("""
            ALTER TABLE group_lists
            ADD COLUMN IF NOT EXISTS is_public BOOLEAN NOT NULL DEFAULT FALSE
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS group_list_members (
                id            SERIAL PRIMARY KEY,
                group_list_id INTEGER NOT NULL REFERENCES group_lists(id) ON DELETE CASCADE,
                user_email    VARCHAR(255) NOT NULL REFERENCES users(email) ON DELETE CASCADE,
                role          VARCHAR(20) NOT NULL DEFAULT 'member'
                              CHECK (role IN ('owner', 'member')),
                status        VARCHAR(20) NOT NULL DEFAULT 'pending'
                              CHECK (status IN ('pending', 'accepted', 'declined')),
                invited_by    VARCHAR(255),
                invited_at    TIMESTAMP DEFAULT NOW(),
                responded_at  TIMESTAMP,
                UNIQUE (group_list_id, user_email)
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS group_list_items (
                id              SERIAL PRIMARY KEY,
                group_list_id   INTEGER NOT NULL REFERENCES group_lists(id) ON DELETE CASCADE,
                added_by        VARCHAR(255) NOT NULL REFERENCES users(email) ON DELETE CASCADE,
                item_type       VARCHAR(20) NOT NULL
                                CHECK (item_type IN ('dish', 'restaurant', 'recipe')),
                name            VARCHAR(255) NOT NULL,
                restaurant_name VARCHAR(255),
                note            TEXT,
                added_at        TIMESTAMP DEFAULT NOW()
            )
        """)
        cur.execute("""
            CREATE UNIQUE INDEX IF NOT EXISTS group_list_items_unique_idx
            ON group_list_items (group_list_id, item_type, LOWER(name),
                                 COALESCE(LOWER(restaurant_name), ''))
        """)
        cur.execute("""
            CREATE INDEX IF NOT EXISTS group_list_members_user_idx
            ON group_list_members (user_email, status)
        """)
 
        cur.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                email VARCHAR(255) UNIQUE NOT NULL,
                hashed_password VARCHAR(255) NOT NULL,
                created_at TIMESTAMP DEFAULT NOW()
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS meals (
                id              SERIAL PRIMARY KEY,
                user_email      VARCHAR(255) NOT NULL REFERENCES users(email) ON DELETE CASCADE,
                restaurant_name VARCHAR(255) NOT NULL,
                title           VARCHAR(255),
                rating          INTEGER NOT NULL CHECK (rating BETWEEN 1 AND 5),
                review          TEXT,
                logged_at       TIMESTAMP DEFAULT NOW()
            )
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS meal_likes (
                id         SERIAL PRIMARY KEY,
                meal_id    INTEGER NOT NULL REFERENCES meals(id) ON DELETE CASCADE,
                user_email VARCHAR(255) NOT NULL REFERENCES users(email) ON DELETE CASCADE,
                created_at TIMESTAMP DEFAULT NOW(),
                UNIQUE (meal_id, user_email)
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS meal_comments (
                id         SERIAL PRIMARY KEY,
                meal_id    INTEGER NOT NULL REFERENCES meals(id) ON DELETE CASCADE,
                user_email VARCHAR(255) NOT NULL REFERENCES users(email) ON DELETE CASCADE,
                content    TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT NOW()
            )
        """)

        cur.execute("""
            ALTER TABLE dish_reviews
            ADD COLUMN IF NOT EXISTS meal_id INTEGER REFERENCES meals(id) ON DELETE CASCADE
        """)
        cur.execute("""
            CREATE INDEX IF NOT EXISTS dish_reviews_meal_idx ON dish_reviews (meal_id)
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS dish_reviews (
                id SERIAL PRIMARY KEY,
                user_email VARCHAR(255) NOT NULL REFERENCES users(email) ON DELETE CASCADE,
                dish_name VARCHAR(255) NOT NULL,
                type VARCHAR(20) NOT NULL CHECK (type IN ('restaurant', 'homemade')),
                restaurant_name VARCHAR(255),
                recipe TEXT,
                rating INTEGER NOT NULL CHECK (rating BETWEEN 1 AND 5),
                review TEXT,
                logged_at TIMESTAMP DEFAULT NOW()
            )
        """)
        # Recipe ownership: NULL = original/your own recipe, else the tagged author's email.
        cur.execute("""
            ALTER TABLE dish_reviews
            ADD COLUMN IF NOT EXISTS recipe_owner_email VARCHAR(255)
                REFERENCES users(email) ON DELETE SET NULL
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS recipe_ingredients (
                id         SERIAL PRIMARY KEY,
                review_id  INTEGER NOT NULL REFERENCES dish_reviews(id) ON DELETE CASCADE,
                position   SMALLINT NOT NULL,
                name       VARCHAR(120) NOT NULL,
                quantity   NUMERIC(8,2) NOT NULL CHECK (quantity > 0),
                unit       VARCHAR(10) NOT NULL
                        CHECK (unit IN ('g','kg','ml','l','tsp','tbsp','cup','pcs','pinch'))
            )
        """)
        cur.execute("CREATE INDEX IF NOT EXISTS recipe_ingredients_review_idx ON recipe_ingredients (review_id)")

        # Half-star ratings: widen INTEGER → NUMERIC(2,1) and allow 0.5 as the floor.
        cur.execute("ALTER TABLE dish_reviews DROP CONSTRAINT IF EXISTS dish_reviews_rating_check")
        cur.execute("ALTER TABLE dish_reviews ALTER COLUMN rating TYPE NUMERIC(2,1)")
        cur.execute("ALTER TABLE dish_reviews ADD CONSTRAINT dish_reviews_rating_check CHECK (rating >= 0.5 AND rating <= 5)")
        cur.execute("ALTER TABLE meals DROP CONSTRAINT IF EXISTS meals_rating_check")
        cur.execute("ALTER TABLE meals ALTER COLUMN rating TYPE NUMERIC(2,1)")
        cur.execute("ALTER TABLE meals ADD CONSTRAINT meals_rating_check CHECK (rating >= 0.5 AND rating <= 5)")
        cur.execute("""
            CREATE TABLE IF NOT EXISTS friendships (
                id SERIAL PRIMARY KEY,
                requester_email VARCHAR(255) NOT NULL REFERENCES users(email) ON DELETE CASCADE,
                addressee_email VARCHAR(255) NOT NULL REFERENCES users(email) ON DELETE CASCADE,
                status VARCHAR(20) NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'accepted', 'declined')),
                created_at TIMESTAMP DEFAULT NOW(),
                updated_at TIMESTAMP DEFAULT NOW(),
                UNIQUE (requester_email, addressee_email)
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS trylists (
                id               SERIAL PRIMARY KEY,
                user_email       VARCHAR(255) NOT NULL REFERENCES users(email) ON DELETE CASCADE,
                item_type        VARCHAR(20)  NOT NULL CHECK (item_type IN ('dish', 'restaurant')),
                dish_name        VARCHAR(255),
                restaurant_name  VARCHAR(255),
                added_at         TIMESTAMP DEFAULT NOW(),
                UNIQUE (user_email, item_type, dish_name, restaurant_name)
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS review_likes (
                id SERIAL PRIMARY KEY,
                review_id INTEGER NOT NULL REFERENCES dish_reviews(id) ON DELETE CASCADE,
                user_email VARCHAR(255) NOT NULL REFERENCES users(email) ON DELETE CASCADE,
                created_at TIMESTAMP DEFAULT NOW(),
                UNIQUE (review_id, user_email)
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS review_comments (
                id SERIAL PRIMARY KEY,
                review_id INTEGER NOT NULL REFERENCES dish_reviews(id) ON DELETE CASCADE,
                user_email VARCHAR(255) NOT NULL REFERENCES users(email) ON DELETE CASCADE,
                content TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT NOW()
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS custom_lists (
                id         SERIAL PRIMARY KEY,
                user_email VARCHAR(255) NOT NULL REFERENCES users(email) ON DELETE CASCADE,
                name       VARCHAR(255) NOT NULL,
                is_public  BOOLEAN NOT NULL DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT NOW()
            )
        """)
        cur.execute("""
            ALTER TABLE custom_lists
            ADD COLUMN IF NOT EXISTS is_public BOOLEAN NOT NULL DEFAULT TRUE
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS list_items (
                id              SERIAL PRIMARY KEY,
                list_id         INTEGER NOT NULL REFERENCES custom_lists(id) ON DELETE CASCADE,
                item_type       VARCHAR(20) NOT NULL CHECK (item_type IN ('dish', 'restaurant', 'recipe')),
                name            VARCHAR(255) NOT NULL,
                restaurant_name VARCHAR(255),
                note            TEXT,
                added_at        TIMESTAMP DEFAULT NOW()
            )
        """)
        cur.execute("""
            DELETE FROM list_items a
            USING list_items b
            WHERE a.id > b.id
            AND a.list_id = b.list_id
            AND a.item_type = b.item_type
            AND LOWER(a.name) = LOWER(b.name)
            AND COALESCE(LOWER(a.restaurant_name), '') = COALESCE(LOWER(b.restaurant_name), '')
        """)
        cur.execute("""
            CREATE UNIQUE INDEX IF NOT EXISTS list_items_unique_idx
            ON list_items (list_id, item_type, name, COALESCE(restaurant_name, ''))
        """)
        # Old databases have list_items.list_id pointing at the retired user_lists
        # table. Repoint it at custom_lists. NOT VALID leaves existing rows alone.
        cur.execute("""
            DO $$
            BEGIN
                IF EXISTS (
                    SELECT 1 FROM pg_constraint
                    WHERE conname = 'list_items_list_id_fkey'
                      AND conrelid = 'list_items'::regclass
                      AND confrelid <> 'custom_lists'::regclass
                ) THEN
                    ALTER TABLE list_items DROP CONSTRAINT list_items_list_id_fkey;
                    ALTER TABLE list_items
                        ADD CONSTRAINT list_items_list_id_fkey
                        FOREIGN KEY (list_id) REFERENCES custom_lists(id)
                        ON DELETE CASCADE NOT VALID;
                END IF;
            END $$;
        """)
        cur.execute("ALTER TABLE list_items       ADD COLUMN IF NOT EXISTS recipe_owner_email VARCHAR(255)")
        cur.execute("ALTER TABLE group_list_items ADD COLUMN IF NOT EXISTS recipe_owner_email VARCHAR(255)")
        # Older recipe items have no owner: assume whoever added them
        cur.execute("""
            UPDATE list_items li SET recipe_owner_email = cl.user_email
            FROM custom_lists cl
            WHERE li.list_id = cl.id AND li.item_type = 'recipe' AND li.recipe_owner_email IS NULL
        """)
        cur.execute("""
            UPDATE group_list_items SET recipe_owner_email = added_by
            WHERE item_type = 'recipe' AND recipe_owner_email IS NULL
        """)

        # ── Public/private accounts ──────────────────────────────────────────
        # FALSE = public (anyone can follow instantly); TRUE = private (follow
        # requests must be approved).
        cur.execute("""
            ALTER TABLE users
            ADD COLUMN IF NOT EXISTS is_private BOOLEAN NOT NULL DEFAULT FALSE
        """)

        # ── Companion tags ("went with") ─────────────────────────────────────
        # Display-only: a tag never shows in the tagged user's own diary/feed,
        # only on the post owner's post.
        cur.execute("""
            CREATE TABLE IF NOT EXISTS post_tags (
                id           SERIAL PRIMARY KEY,
                post_type    VARCHAR(10) NOT NULL CHECK (post_type IN ('review', 'meal')),
                post_id      INTEGER NOT NULL,
                tagged_email VARCHAR(255) NOT NULL REFERENCES users(email) ON DELETE CASCADE,
                created_at   TIMESTAMP DEFAULT NOW(),
                UNIQUE (post_type, post_id, tagged_email)
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS post_reposts (
                id             SERIAL PRIMARY KEY,
                post_type      VARCHAR(10) NOT NULL CHECK (post_type IN ('review', 'meal')),
                post_id        INTEGER NOT NULL,
                reposter_email VARCHAR(255) NOT NULL REFERENCES users(email) ON DELETE CASCADE,
                created_at     TIMESTAMP DEFAULT NOW(),
                UNIQUE (post_type, post_id, reposter_email)
            )
        """)
        cur.execute("""
            CREATE INDEX IF NOT EXISTS post_reposts_reposter_idx
            ON post_reposts (reposter_email, created_at DESC)
        """)
        cur.execute("""
            CREATE INDEX IF NOT EXISTS post_tags_tagged_idx
            ON post_tags (tagged_email, created_at DESC)
        """)

        cur.execute("""
            ALTER TABLE dish_reviews
            ADD COLUMN IF NOT EXISTS forked_from_id INTEGER
                REFERENCES dish_reviews(id) ON DELETE SET NULL
        """)
        cur.execute("""
            ALTER TABLE meals
            ADD COLUMN IF NOT EXISTS forked_from_id INTEGER
                REFERENCES meals(id) ON DELETE SET NULL
        """)
        cur.execute("CREATE INDEX IF NOT EXISTS dish_reviews_fork_idx ON dish_reviews (forked_from_id)")
        cur.execute("CREATE INDEX IF NOT EXISTS meals_fork_idx        ON meals (forked_from_id)")

        # ── Threaded comments (full nesting via self-referential parent_id) ──
        cur.execute("""
            ALTER TABLE review_comments
            ADD COLUMN IF NOT EXISTS parent_id INTEGER
                REFERENCES review_comments(id) ON DELETE CASCADE
        """)
        cur.execute("""
            ALTER TABLE meal_comments
            ADD COLUMN IF NOT EXISTS parent_id INTEGER
                REFERENCES meal_comments(id) ON DELETE CASCADE
        """)

        # ── Comment likes (separate tables so FK cascade cleans them up) ─────
        cur.execute("""
            CREATE TABLE IF NOT EXISTS review_comment_likes (
                id         SERIAL PRIMARY KEY,
                comment_id INTEGER NOT NULL REFERENCES review_comments(id) ON DELETE CASCADE,
                user_email VARCHAR(255) NOT NULL REFERENCES users(email) ON DELETE CASCADE,
                created_at TIMESTAMP DEFAULT NOW(),
                UNIQUE (comment_id, user_email)
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS meal_comment_likes (
                id         SERIAL PRIMARY KEY,
                comment_id INTEGER NOT NULL REFERENCES meal_comments(id) ON DELETE CASCADE,
                user_email VARCHAR(255) NOT NULL REFERENCES users(email) ON DELETE CASCADE,
                created_at TIMESTAMP DEFAULT NOW(),
                UNIQUE (comment_id, user_email)
            )
        """)

        # ── One-time backfill: preserve existing mutual friendships ──────────
        # Pre-follow-model, a single accepted friendship row meant a *mutual*
        # relationship. Moving to a directional follow graph, we backfill the
        # reverse row once so existing friends keep seeing each other's posts.
        cur.execute("""
            CREATE TABLE IF NOT EXISTS schema_flags (
                flag       VARCHAR(100) PRIMARY KEY,
                applied_at TIMESTAMP DEFAULT NOW()
            )
        """)
        cur.execute("SELECT 1 FROM schema_flags WHERE flag = 'friendship_backfill_v1'")
        if not cur.fetchone():
            cur.execute("""
                INSERT INTO friendships (requester_email, addressee_email, status)
                SELECT f.addressee_email, f.requester_email, 'accepted'
                FROM friendships f
                WHERE f.status = 'accepted'
                  AND NOT EXISTS (
                      SELECT 1 FROM friendships r
                      WHERE r.requester_email = f.addressee_email
                        AND r.addressee_email = f.requester_email
                  )
                ON CONFLICT (requester_email, addressee_email) DO NOTHING
            """)
            cur.execute("INSERT INTO schema_flags (flag) VALUES ('friendship_backfill_v1')")

        # ── One-time: existing accounts become private ───────────────────────
        # Preserves the old mutual-friendship behaviour — their existing
        # (backfilled) mutual follows keep working, and any *new* follower now
        # needs approval, just like the old friend-request flow. New signups
        # still default to public (column default) and can switch in Settings.
        cur.execute("SELECT 1 FROM schema_flags WHERE flag = 'users_private_v1'")
        if not cur.fetchone():
            cur.execute("UPDATE users SET is_private = TRUE")
            cur.execute("INSERT INTO schema_flags (flag) VALUES ('users_private_v1')")

        conn.commit()
    conn.close()
