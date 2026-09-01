import { useState } from 'react'
import { StarRating } from './StarRating'
import shared from './shared.module.css'
import styles from './MealCard.module.css'

export default function MealCard({ meal, onViewDish, onViewRestaurant, onDelete }) {
  const [open, setOpen] = useState(false)
  const date = new Date(meal.loggedAt).toLocaleDateString('en-IN', {
    day: 'numeric', month: 'short', year: 'numeric',
  })

  return (
    <div className={shared.card}>
      <div className={shared.cardTop}>
        <div>
          <p className={shared.dishName}>{meal.title || 'Meal'}</p>
          <button className={styles.restaurantLink} onClick={() => onViewRestaurant?.(meal.restaurantName)}>
            {meal.restaurantName}
          </button>
        </div>
        <span className={shared.typePill} data-type="meal">🍽️ Meal</span>
      </div>

      <div className={styles.ratingRow}>
        <StarRating rating={meal.rating} showLabel />
        {meal.dishAvg != null && (
          <span className={styles.dishAvg}>dishes avg {meal.dishAvg}</span>
        )}
        <span className={shared.dot}>·</span>
        <span className={shared.date}>{date}</span>
      </div>

      {meal.review && <p className={shared.reviewText}>{meal.review}</p>}

      <button className={styles.expandBtn} onClick={() => setOpen(o => !o)}>
        {open ? 'Hide' : 'Show'} {meal.dishCount} dish{meal.dishCount !== 1 ? 'es' : ''}
        <span className={open ? styles.chevronOpen : styles.chevron}>▾</span>
      </button>

      {open && (
        <div className={styles.dishList}>
          {meal.dishes.map(d => (
            <div key={d.id} className={styles.dishItem}>
              <button className={styles.dishNameBtn}
                onClick={() => onViewDish?.(d.dishName, meal.restaurantName)}>
                {d.dishName}
              </button>
              <StarRating rating={d.rating} size={12} />
              {d.review && <p className={styles.dishNote}>{d.review}</p>}
            </div>
          ))}
        </div>
      )}

      {onDelete && (
        <button className={styles.deleteBtn}
          onClick={() => window.confirm(`Delete this meal? Its ${meal.dishCount} dish ratings will be removed too.`) && onDelete(meal.id)}>
          Delete
        </button>
      )}
    </div>
  )
}