export const UNITS = ['g', 'kg', 'ml', 'l', 'tsp', 'tbsp', 'cup', 'pcs', 'pinch']
const MAX_INGREDIENTS = 30
let uid = 0
export const emptyIngredient = () => ({ key: ++uid, name: '', quantity: '', unit: 'g' })
export const ingredientsFrom = (list = []) =>
  list.length ? list.map(i => ({ key: ++uid, name: i.name, quantity: String(i.quantity), unit: i.unit }))
              : [emptyIngredient(), emptyIngredient()]
export const toPayload = (rows) => rows
  .filter(r => r.name.trim())
  .map(r => ({ name: r.name.trim(), quantity: parseFloat(r.quantity), unit: r.unit }))
export const ingredientsValid = (rows) => {
  const filled = rows.filter(r => r.name.trim())
  return filled.length > 0 && filled.every(r => parseFloat(r.quantity) > 0)
}

export default function IngredientRows({ rows, onChange, styles }) {
  const patch  = (key, ch) => onChange(rows.map(r => r.key === key ? { ...r, ...ch } : r))
  const remove = (key) => onChange(rows.filter(r => r.key !== key))
  return (
    <>
      <div className={styles.dishList}>
        {rows.map(r => (
          <div key={r.key} className={styles.ingredientRow}>
            <input className={styles.input} placeholder="e.g. Basmati rice"
              value={r.name} onChange={e => patch(r.key, { name: e.target.value })} />
            <input className={`${styles.input} ${styles.qtyInput}`} type="number"
              min="0" step="any" inputMode="decimal" placeholder="Qty"
              value={r.quantity} onChange={e => patch(r.key, { quantity: e.target.value })} />
            <select className={`${styles.input} ${styles.unitSelect}`}
              value={r.unit} onChange={e => patch(r.key, { unit: e.target.value })}>
              {UNITS.map(u => <option key={u} value={u}>{u}</option>)}
            </select>
            <button type="button" className={styles.removeDishBtn}
              onClick={() => remove(r.key)} disabled={rows.length <= 1}
              aria-label="Remove ingredient">×</button>
          </div>
        ))}
      </div>
      <button type="button" className={styles.addDishBtn}
        onClick={() => onChange([...rows, emptyIngredient()])}
        disabled={rows.length >= MAX_INGREDIENTS}>
        + Add ingredient
      </button>
    </>
  )
}