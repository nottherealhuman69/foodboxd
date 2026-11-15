"""SQL fragments shared by personal and group lists."""


# Community avg, review count, and the viewer's own avg for each list item.
# Recipes have no restaurant, so they get NULLs (and sort last on rating sorts).
LIST_ITEM_STATS = """
    LEFT JOIN LATERAL (
        SELECT ROUND(AVG(r.rating)::numeric, 1)::float AS avg_rating,
               COUNT(*)                                AS review_count,
               ROUND((AVG(r.rating) FILTER (WHERE r.user_email = %s))::numeric, 1)::float AS my_rating
        FROM dish_reviews r
        WHERE r.type = 'restaurant'
          AND r.restaurant_name ILIKE CASE WHEN i.item_type = 'restaurant'
                                           THEN i.name ELSE i.restaurant_name END
          AND (i.item_type = 'restaurant' OR r.dish_name ILIKE i.name)
    ) s ON i.item_type IN ('dish', 'restaurant')
"""
