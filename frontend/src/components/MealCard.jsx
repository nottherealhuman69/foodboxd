import { useState } from 'react'
import { StarRating } from './StarRating'
import shared from './shared.module.css'
import styles from './MealCard.module.css'

export default function MealCard({ meal, onViewMeal, onViewDish, onViewRestaurant, onDelete }) {
  console.log('MealCard render', meal.id, 'onViewMeal is', typeof onViewMeal)
  const [open, setOpen] = useState(false)
  const date = new Date(meal.loggedAt).toLocaleDateString('en-IN', {
    day: 'numeric', month: 'short', year: 'numeric',
  })

  return (
    <div
      className={shared.card}
      style={{ cursor: onViewMeal ? 'pointer' : 'default' }}
      onClick={() => { console.log('meal card clicked', meal.id); onViewMeal?.(meal.id, 'comments') }}
    >
      <div className={shared.cardTop}>
        <div>
          <p className={shared.dishName}>{meal.title || 'Meal'}</p>
          <button
            type="button"
            className={styles.restaurantLink}
            onClick={e => { e.stopPropagation(); onViewRestaurant?.(meal.restaurantName) }}
          >
            {meal.restaurantName}
          </button>
        </div>
        <span className={shared.typePill} data-type="meal">🍽️ Meal</span>
      </div>

      <div className={styles.ratingRow}>
        <StarRating rating={meal.rating} showLabel />
        {meal.dishAvg != null && <span className={styles.dishAvg}>dishes avg {meal.dishAvg}</span>}
        <span className={shared.dot}>·</span>
        <span className={shared.date}>{date}</span>
      </div>

      {meal.review && <p className={shared.reviewText}>{meal.review}</p>}

      <button
        type="button"
        className={styles.expandBtn}
        onClick={e => { e.stopPropagation(); setOpen(o => !o) }}
      >
        {open ? 'Hide' : 'Show'} {meal.dishCount} dish{meal.dishCount !== 1 ? 'es' : ''}
        <span className={open ? styles.chevronOpen : styles.chevron}>▾</span>
      </button>

      {open && (
        <div className={styles.dishList}>
          {meal.dishes.map(d => (
            <div key={d.id} className={styles.dishItem}>
              <button
                type="button"
                className={styles.dishNameBtn}
                onClick={e => { e.stopPropagation(); onViewDish?.(d.dishName, meal.restaurantName) }}
              >
                {d.dishName}
              </button>
              <StarRating rating={d.rating} size={12} />
              {d.review && <p className={styles.dishNote}>{d.review}</p>}
            </div>
          ))}
        </div>
      )}

      {onDelete && (
        <button
          type="button"
          className={styles.deleteBtn}
          onClick={e => {
            e.stopPropagation()
            if (window.confirm(`Delete this meal? Its ${meal.dishCount} dish ratings will be removed too.`)) {
              onDelete(meal.id)
            }
          }}
        >
          Delete
        </button>
      )}
    </div>
  )
}