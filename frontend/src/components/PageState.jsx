import shared from './shared.module.css'

/**
 * <PageState loading error empty emptyIcon emptyTitle emptyHint emptyAction />
 *
 * Renders the right state automatically:
 *   loading → spinner
 *   error   → warning + message
 *   empty   → empty-state card
 *   none    → null (caller renders content)
 */
export default function PageState({ loading, error, empty, emptyIcon, emptyTitle, emptyHint, emptyAction }) {
  if (loading) return (
    <div className={shared.state}>
      <div className={shared.spinner} />
      <p>Loading…</p>
    </div>
  )

  if (error) return (
    <div className={shared.state}>
      <span className={shared.stateIcon}>⚠️</span>
      <p>{error}</p>
    </div>
  )

  if (empty) return (
    <div className={shared.empty}>
      {emptyIcon && <div className={shared.emptyIcon}>{emptyIcon}</div>}
      {emptyTitle && <p className={shared.emptyTitle}>{emptyTitle}</p>}
      {emptyHint  && <p className={shared.emptyHint}>{emptyHint}</p>}
      {emptyAction}
    </div>
  )

  return null
}
