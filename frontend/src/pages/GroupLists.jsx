import { useState, useEffect, useCallback, useRef } from 'react'
import { apiFetch } from '../hooks/useApi'
import PageState from '../components/PageState'
import styles from './GroupLists.module.css'

/* ── Icons ── */
function GroupIcon() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
      <circle cx="9" cy="8" r="3.2" stroke="currentColor" strokeWidth="1.5"/>
      <path d="M3.5 19c0-3 2.5-4.8 5.5-4.8s5.5 1.8 5.5 4.8" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
      <path d="M16 5.4a3.2 3.2 0 010 5.2M17.5 14.6c2 .7 3.3 2.3 3.3 4.4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
    </svg>
  )
}
function PlusIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
      <path d="M12 5v14M5 12h14" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/>
    </svg>
  )
}
function BackIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
      <path d="M19 12H5M5 12l7 7M5 12l7-7" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round"/>
    </svg>
  )
}
function TrashIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none">
      <path d="M3 6h18M8 6V4h8v2M19 6l-1 14H6L5 6" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
    </svg>
  )
}
function CheckIcon() {
  return (
    <svg width="12" height="12" viewBox="0 0 24 24" fill="none">
      <path d="M20 6L9 17l-5-5" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round"/>
    </svg>
  )
}

const TYPE_ICONS  = { dish: '🍽️', restaurant: '🏠', recipe: '📖' }
const TYPE_LABELS = { dish: 'Dish', restaurant: 'Restaurant', recipe: 'Recipe' }

const initials = (email) => (email || '?')[0].toUpperCase()

/* ══════════════════════════════════════════════════════════════════════════
   Friend picker — shared by "Create group list" and "Invite more"
   ══════════════════════════════════════════════════════════════════════════ */
function FriendPicker({ selected, onToggle, excludeEmails = [] }) {
  const [friends, setFriends] = useState(null)
  const [loading, setLoading] = useState(true)
  const [query, setQuery]     = useState('')

  useEffect(() => {
    apiFetch('/api/friends')
      .then(r => (r.ok ? r.json() : []))
      .then(setFriends)
      .catch(() => setFriends([]))
      .finally(() => setLoading(false))
  }, [])

  const available = (friends || []).filter(f => !excludeEmails.includes(f.email))
  const shown = available.filter(f =>
    f.username.toLowerCase().includes(query.toLowerCase()) ||
    f.email.toLowerCase().includes(query.toLowerCase())
  )

  if (loading) return <p className={styles.pickerHint}>Loading your friends…</p>

  if (available.length === 0) {
    return (
      <p className={styles.pickerHint}>
        {friends?.length
          ? 'All your friends are already in this list.'
          : 'Add friends first — you can only build group lists with people you follow.'}
      </p>
    )
  }

  return (
    <>
      {available.length > 6 && (
        <input
          className={styles.input}
          placeholder="Search friends"
          value={query}
          onChange={e => setQuery(e.target.value)}
          style={{ marginBottom: 10 }}
        />
      )}
      <div className={styles.friendPicker}>
        {shown.map(f => {
          const isOn = selected.includes(f.email)
          return (
            <button
              key={f.email}
              type="button"
              className={`${styles.friendRow} ${isOn ? styles.friendRowOn : ''}`}
              onClick={() => onToggle(f.email)}
            >
              <span className={styles.avatarSm}>{initials(f.email)}</span>
              <span className={styles.friendName}>@{f.username}</span>
              <span className={`${styles.checkbox} ${isOn ? styles.checkboxOn : ''}`}>
                {isOn && <CheckIcon />}
              </span>
            </button>
          )
        })}
        {shown.length === 0 && <p className={styles.pickerHint}>No friends match "{query}".</p>}
      </div>
    </>
  )
}

/* ══════════════════════════════════════════════════════════════════════════
   Create group list modal
   ══════════════════════════════════════════════════════════════════════════ */
function CreateGroupListModal({ onClose, onCreated }) {
  const [name, setName]         = useState('')
  const [selected, setSelected] = useState([])
  const [saving, setSaving]     = useState(false)
  const [err, setErr]           = useState('')

  const toggle = (email) =>
    setSelected(prev => prev.includes(email) ? prev.filter(e => e !== email) : [...prev, email])

  const submit = async () => {
    if (!name.trim()) { setErr('Give the list a name.'); return }
    setSaving(true); setErr('')
    try {
      const res = await apiFetch('/api/group-lists', {
        method: 'POST',
        body: JSON.stringify({ name: name.trim(), invite_emails: selected }),
      })
      if (!res.ok) {
        const d = await res.json().catch(() => ({}))
        setErr(d.detail || 'Could not create the list.')
        return
      }
      onCreated(await res.json())
    } catch { setErr('Could not reach the server.') }
    finally { setSaving(false) }
  }

  return (
    <div className={styles.modalBackdrop} onClick={onClose}>
      <div className={styles.modal} onClick={e => e.stopPropagation()}>
        <h3 className={styles.modalTitle}>Create a group list</h3>
        <p className={styles.modalSub}>
          Everyone who joins can add dishes and restaurants to it.
        </p>

        <div className={styles.field}>
          <label className={styles.label}>List name</label>
          <input
            className={styles.input}
            placeholder="e.g. Goa trip 2026"
            value={name}
            autoFocus
            onChange={e => { setName(e.target.value); setErr('') }}
            onKeyDown={e => e.key === 'Enter' && submit()}
          />
        </div>

        <div className={styles.field}>
          <label className={styles.label}>
            Invite friends {selected.length > 0 && <span className={styles.countTag}>{selected.length} selected</span>}
          </label>
          <FriendPicker selected={selected} onToggle={toggle} />
        </div>

        {err && <p className={styles.errText}>{err}</p>}

        <div className={styles.modalActions}>
          <button className={styles.cancelBtn} onClick={onClose}>Cancel</button>
          <button className={styles.primaryBtn} onClick={submit} disabled={saving}>
            {saving ? 'Creating…' : selected.length ? `Create and invite ${selected.length}` : 'Create list'}
          </button>
        </div>
      </div>
    </div>
  )
}

/* ══════════════════════════════════════════════════════════════════════════
   Invite more friends to an existing group list
   ══════════════════════════════════════════════════════════════════════════ */
function InviteMoreModal({ listId, existingEmails, onClose, onInvited }) {
  const [selected, setSelected] = useState([])
  const [saving, setSaving]     = useState(false)
  const [err, setErr]           = useState('')

  const toggle = (email) =>
    setSelected(prev => prev.includes(email) ? prev.filter(e => e !== email) : [...prev, email])

  const submit = async () => {
    if (selected.length === 0) { setErr('Pick at least one friend.'); return }
    setSaving(true); setErr('')
    try {
      const res = await apiFetch(`/api/group-lists/${listId}/invite`, {
        method: 'POST',
        body: JSON.stringify({ emails: selected }),
      })
      if (!res.ok) {
        const d = await res.json().catch(() => ({}))
        setErr(d.detail || 'Could not send the invites.')
        return
      }
      onInvited(await res.json())
    } catch { setErr('Could not reach the server.') }
    finally { setSaving(false) }
  }

  return (
    <div className={styles.modalBackdrop} onClick={onClose}>
      <div className={styles.modal} onClick={e => e.stopPropagation()}>
        <h3 className={styles.modalTitle}>Invite more friends</h3>
        <p className={styles.modalSub}>They'll get a notification and join once they accept.</p>
        <FriendPicker selected={selected} onToggle={toggle} excludeEmails={existingEmails} />
        {err && <p className={styles.errText}>{err}</p>}
        <div className={styles.modalActions}>
          <button className={styles.cancelBtn} onClick={onClose}>Cancel</button>
          <button className={styles.primaryBtn} onClick={submit} disabled={saving}>
            {saving ? 'Sending…' : 'Send invites'}
          </button>
        </div>
      </div>
    </div>
  )
}

/* ══════════════════════════════════════════════════════════════════════════
   Add item modal (group variant)
   ══════════════════════════════════════════════════════════════════════════ */
function AddItemModal({ listId, onClose, onAdded }) {
  const [itemType, setItemType]   = useState('dish')
  const [name, setName]           = useState('')
  const [restaurant, setRestaurant] = useState('')
  const [note, setNote]           = useState('')
  const [saving, setSaving]       = useState(false)
  const [err, setErr]             = useState('')
  const [suggestions, setSuggestions]   = useState([])
  const [showDropdown, setShowDropdown] = useState(false)
  const debounceRef = useRef(null)

  const fetchSuggestions = useCallback((q, type) => {
    if (type === 'recipe' || !q.trim()) { setSuggestions([]); setShowDropdown(false); return }
    clearTimeout(debounceRef.current)
    debounceRef.current = setTimeout(async () => {
      try {
        const res = await apiFetch(
          `/api/search/dishes-restaurants?q=${encodeURIComponent(q)}&item_type=${type}`
        )
        if (res.ok) {
          const data = await res.json()
          setSuggestions(data)
          setShowDropdown(data.length > 0)
        }
      } catch {}
    }, 250)
  }, [])

  const handleTypeChange = (t) => {
    setItemType(t); setName(''); setRestaurant('')
    setSuggestions([]); setShowDropdown(false); setErr('')
  }

  const selectSuggestion = (s) => {
    setName(s.name)
    if (s.restaurant_name) setRestaurant(s.restaurant_name)
    setSuggestions([]); setShowDropdown(false)
  }

  const submit = async () => {
    if (!name.trim()) { setErr('Enter a name.'); return }
    if (itemType === 'dish' && !restaurant.trim()) { setErr('Enter the restaurant name.'); return }
    setSaving(true); setErr('')
    try {
      const res = await apiFetch(`/api/group-lists/${listId}/items`, {
        method: 'POST',
        body: JSON.stringify({
          item_type: itemType,
          name: name.trim(),
          restaurant_name: itemType === 'dish' ? restaurant.trim() : null,
          note: note.trim() || null,
        }),
      })
      if (!res.ok) {
        const d = await res.json().catch(() => ({}))
        setErr(d.detail || 'Could not add the item.')
        return
      }
      onAdded(await res.json())
    } catch { setErr('Could not reach the server.') }
    finally { setSaving(false) }
  }

  return (
    <div className={styles.modalBackdrop} onClick={onClose}>
      <div className={styles.modal} onClick={e => e.stopPropagation()}>
        <h3 className={styles.modalTitle}>Add to the group list</h3>

        <div className={styles.field}>
          <label className={styles.label}>Type</label>
          <div className={styles.typeRow}>
            {['dish', 'restaurant', 'recipe'].map(t => (
              <button
                key={t}
                className={`${styles.typeBtn} ${itemType === t ? styles.typeBtnActive : ''}`}
                onClick={() => handleTypeChange(t)}
              >
                <span>{TYPE_ICONS[t]}</span> {TYPE_LABELS[t]}
              </button>
            ))}
          </div>
        </div>

        <div className={styles.field}>
          <label className={styles.label}>
            {itemType === 'dish' ? 'Dish name' : itemType === 'restaurant' ? 'Restaurant name' : 'Recipe name'}
          </label>
          <div className={styles.searchWrap}>
            <input
              className={styles.input}
              placeholder={
                itemType === 'dish' ? 'e.g. Chicken Biryani'
                : itemType === 'restaurant' ? 'e.g. Paradise Biryani'
                : 'e.g. Amma\u2019s dal'
              }
              value={name}
              autoFocus
              onChange={e => { setName(e.target.value); setErr(''); fetchSuggestions(e.target.value, itemType) }}
            />
            {showDropdown && (
              <div className={styles.suggestions}>
                {suggestions.map((s, i) => (
                  <button key={i} className={styles.suggestionItem} onClick={() => selectSuggestion(s)}>
                    <span>{s.name}</span>
                    {s.restaurant_name && <span className={styles.suggestionSub}>at {s.restaurant_name}</span>}
                  </button>
                ))}
              </div>
            )}
          </div>
        </div>

        {itemType === 'dish' && (
          <div className={styles.field}>
            <label className={styles.label}>Restaurant</label>
            <input
              className={styles.input}
              placeholder="e.g. Paradise, Secunderabad"
              value={restaurant}
              onChange={e => { setRestaurant(e.target.value); setErr('') }}
            />
          </div>
        )}

        <div className={styles.field}>
          <label className={styles.label}>Note <span className={styles.optional}>optional</span></label>
          <input
            className={styles.input}
            placeholder="Tell the group why"
            value={note}
            onChange={e => setNote(e.target.value)}
          />
        </div>

        {err && <p className={styles.errText}>{err}</p>}

        <div className={styles.modalActions}>
          <button className={styles.cancelBtn} onClick={onClose}>Cancel</button>
          <button className={styles.primaryBtn} onClick={submit} disabled={saving}>
            {saving ? 'Adding…' : 'Add item'}
          </button>
        </div>
      </div>
    </div>
  )
}

/* ══════════════════════════════════════════════════════════════════════════
   Group list detail
   ══════════════════════════════════════════════════════════════════════════ */
function GroupListDetail({ listId, onBack, onChanged, onViewDish, onViewRestaurant, currentEmail }) {
  const [list, setList]       = useState(null)
  const [items, setItems]     = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError]     = useState('')
  const [showAdd, setShowAdd]       = useState(false)
  const [showInvite, setShowInvite] = useState(false)
  const [removing, setRemoving]     = useState({})

  const load = useCallback(async () => {
    setLoading(true); setError('')
    try {
      const [lRes, iRes] = await Promise.all([
        apiFetch(`/api/group-lists/${listId}`),
        apiFetch(`/api/group-lists/${listId}/items`),
      ])
      if (!lRes.ok) throw new Error()
      setList(await lRes.json())
      setItems(iRes.ok ? await iRes.json() : [])
    } catch { setError('Could not load this list. Try again.') }
    finally { setLoading(false) }
  }, [listId])

  useEffect(() => { load() }, [load])

  const removeItem = async (itemId) => {
    setRemoving(p => ({ ...p, [itemId]: true }))
    try {
      const res = await apiFetch(`/api/group-lists/${listId}/items/${itemId}`, { method: 'DELETE' })
      if (res.ok) { setItems(p => p.filter(i => i.id !== itemId)); onChanged?.() }
    } catch {}
    finally { setRemoving(p => { const n = { ...p }; delete n[itemId]; return n }) }
  }

  const leave = async () => {
    if (!confirm('Leave this group list? You\u2019ll stop seeing it, but the list stays for everyone else.')) return
    const res = await apiFetch(`/api/group-lists/${listId}/leave`, { method: 'POST' })
    if (res.ok) { onChanged?.(); onBack() }
  }

  const deleteList = async () => {
    if (!confirm('Delete this group list for everyone? This can\u2019t be undone.')) return
    const res = await apiFetch(`/api/group-lists/${listId}`, { method: 'DELETE' })
    if (res.ok) { onChanged?.(); onBack() }
  }

  if (loading || error || !list) {
    return (
      <div className={styles.page}>
        <button className={styles.backBtn} onClick={onBack}><BackIcon /> Back to group lists</button>
        <PageState loading={loading} error={error} />
      </div>
    )
  }

  const isOwner  = list.my_role === 'owner'
  const accepted = list.members.filter(m => m.status === 'accepted')
  const pending  = list.members.filter(m => m.status === 'pending')

  return (
    <div className={styles.page}>
      {showAdd && (
        <AddItemModal
          listId={listId}
          onClose={() => setShowAdd(false)}
          onAdded={item => { setItems(p => [...p, item]); setShowAdd(false); onChanged?.() }}
        />
      )}
      {showInvite && (
        <InviteMoreModal
          listId={listId}
          existingEmails={list.members.map(m => m.email)}
          onClose={() => setShowInvite(false)}
          onInvited={() => { setShowInvite(false); load() }}
        />
      )}

      <button className={styles.backBtn} onClick={onBack}><BackIcon /> Back to group lists</button>

      <div className={styles.detailHeader}>
        <div>
          <h2 className={styles.detailTitle}>{list.name}</h2>
          <p className={styles.detailSub}>
            Started by @{list.owner_username} · {accepted.length} member{accepted.length !== 1 ? 's' : ''}
          </p>
        </div>
        <div className={styles.detailActions}>
          <button className={styles.ghostBtn} onClick={() => setShowInvite(true)}>Invite friends</button>
          <button className={styles.addBtn} onClick={() => setShowAdd(true)}><PlusIcon /> Add item</button>
        </div>
      </div>

      {/* Members */}
      <div className={styles.memberStrip}>
        {accepted.map(m => (
          <span key={m.email} className={styles.memberChip} title={m.email}>
            <span className={styles.avatarSm}>{initials(m.email)}</span>
            @{m.username}
            {m.role === 'owner' && <span className={styles.ownerTag}>owner</span>}
          </span>
        ))}
        {pending.map(m => (
          <span key={m.email} className={`${styles.memberChip} ${styles.memberPending}`} title="Hasn't responded yet">
            <span className={`${styles.avatarSm} ${styles.avatarMuted}`}>{initials(m.email)}</span>
            @{m.username}
            <span className={styles.pendingTag}>invited</span>
          </span>
        ))}
      </div>
      {pending.length > 0 && (
        <p className={styles.pendingNote}>
          {pending.length} invite{pending.length !== 1 ? 's' : ''} still open. The list works fine without them —
          they'll see everything so far whenever they accept.
        </p>
      )}

      {/* Items */}
      {items.length === 0 ? (
        <div className={styles.empty}>
          <div className={styles.emptyIcon}>🍜</div>
          <p className={styles.emptyTitle}>Nothing added yet</p>
          <p className={styles.emptyHint}>Add the first dish or restaurant — everyone in the group will see it.</p>
          <button className={styles.addBtn} onClick={() => setShowAdd(true)}><PlusIcon /> Add the first item</button>
        </div>
      ) : (
        <div className={styles.itemsList}>
          {items.map((item, idx) => {
            const clickable = (item.item_type === 'dish' && item.restaurant_name) || item.item_type === 'restaurant'
            const open = () => {
              if (item.item_type === 'dish' && item.restaurant_name) onViewDish?.(item.name, item.restaurant_name)
              else if (item.item_type === 'restaurant') onViewRestaurant?.(item.name)
            }
            const canRemove = isOwner || item.added_by === currentEmail
            return (
              <div
                key={item.id}
                className={styles.itemCard}
                style={{ cursor: clickable ? 'pointer' : 'default' }}
                onClick={clickable ? open : undefined}
              >
                <span className={styles.itemIndex}>{idx + 1}</span>
                <span className={styles.itemTypeIcon}>{TYPE_ICONS[item.item_type]}</span>
                <div className={styles.itemBody}>
                  <p className={styles.itemName}>{item.name}</p>
                  {item.restaurant_name && <p className={styles.itemSub}>at {item.restaurant_name}</p>}
                  {item.note && <p className={styles.itemNote}>"{item.note}"</p>}
                  <p className={styles.addedBy}>added by @{item.added_by_username}</p>
                </div>
                {canRemove && (
                  <button
                    className={styles.removeBtn}
                    onClick={e => { e.stopPropagation(); removeItem(item.id) }}
                    disabled={!!removing[item.id]}
                    title="Remove"
                  >
                    {removing[item.id] ? <span className={styles.removingDot} /> : <TrashIcon />}
                  </button>
                )}
              </div>
            )
          })}
        </div>
      )}

      <div className={styles.dangerRow}>
        {isOwner
          ? <button className={styles.dangerBtn} onClick={deleteList}>Delete group list</button>
          : <button className={styles.dangerBtn} onClick={leave}>Leave group list</button>}
      </div>
    </div>
  )
}

/* ══════════════════════════════════════════════════════════════════════════
   Main Group Lists tab
   ══════════════════════════════════════════════════════════════════════════ */
export default function GroupLists({ onViewDish, onViewRestaurant, currentEmail }) {
  const myEmail = currentEmail || localStorage.getItem('email') || ''
  const [lists, setLists]     = useState([])
  const [invites, setInvites] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError]     = useState('')
  const [showCreate, setShowCreate] = useState(false)
  const [openId, setOpenId]   = useState(null)
  const [acting, setActing]   = useState({})

  const load = useCallback(async () => {
    setLoading(true); setError('')
    try {
      const [lRes, iRes] = await Promise.all([
        apiFetch('/api/group-lists'),
        apiFetch('/api/group-lists/invites'),
      ])
      if (!lRes.ok) throw new Error()
      setLists(await lRes.json())
      setInvites(iRes.ok ? await iRes.json() : [])
    } catch { setError('Could not load group lists. Try again.') }
    finally { setLoading(false) }
  }, [])

  useEffect(() => { load() }, [load])

  const respond = async (groupListId, action) => {
    setActing(p => ({ ...p, [groupListId]: action }))
    try {
      const res = await apiFetch(`/api/group-lists/${groupListId}/invite`, {
        method: 'PATCH',
        body: JSON.stringify({ action }),
      })
      if (res.ok) {
        setInvites(p => p.filter(i => i.group_list_id !== groupListId))
        if (action === 'accept') load()
      }
    } catch {}
    finally { setActing(p => { const n = { ...p }; delete n[groupListId]; return n }) }
  }

  if (openId) {
    return (
      <GroupListDetail
        listId={openId}
        currentEmail={myEmail}
        onBack={() => setOpenId(null)}
        onChanged={load}
        onViewDish={onViewDish}
        onViewRestaurant={onViewRestaurant}
      />
    )
  }

  return (
    <div className={styles.page}>
      {showCreate && (
        <CreateGroupListModal
          onClose={() => setShowCreate(false)}
          onCreated={list => { setLists(p => [list, ...p]); setShowCreate(false); setOpenId(list.id) }}
        />
      )}

      <div className={styles.header}>
        <div className={styles.headerLeft}>
          <div className={styles.headerIcon}><GroupIcon /></div>
          <div>
            <h2 className={styles.title}>Group lists</h2>
            <p className={styles.sub}>
              {lists.length === 0 ? 'Build a list with your friends' : `${lists.length} list${lists.length !== 1 ? 's' : ''} you're in`}
            </p>
          </div>
        </div>
        <button className={styles.createBtn} onClick={() => setShowCreate(true)}>
          <PlusIcon /> Create a group list
        </button>
      </div>

      {/* Pending invites */}
      {invites.length > 0 && (
        <div className={styles.inviteBlock}>
          <p className={styles.inviteHeading}>Invites waiting for you</p>
          {invites.map(inv => (
            <div key={inv.group_list_id} className={styles.inviteCard}>
              <div className={styles.avatar}>{initials(inv.invited_by)}</div>
              <div className={styles.inviteBody}>
                <p className={styles.inviteName}>{inv.name}</p>
                <p className={styles.inviteSub}>
                  @{inv.invited_by_username} invited you · {inv.member_count} member{inv.member_count !== 1 ? 's' : ''} so far
                </p>
              </div>
              <div className={styles.inviteActions}>
                <button
                  className={styles.acceptBtn}
                  disabled={!!acting[inv.group_list_id]}
                  onClick={() => respond(inv.group_list_id, 'accept')}
                >
                  {acting[inv.group_list_id] === 'accept' ? '…' : 'Join'}
                </button>
                <button
                  className={styles.declineBtn}
                  disabled={!!acting[inv.group_list_id]}
                  onClick={() => respond(inv.group_list_id, 'decline')}
                >
                  {acting[inv.group_list_id] === 'decline' ? '…' : 'Decline'}
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      <PageState loading={loading} error={error} />

      {!loading && !error && lists.length === 0 && (
        <div className={styles.empty}>
          <div className={styles.emptyIcon}>👥</div>
          <p className={styles.emptyTitle}>No group lists yet</p>
          <p className={styles.emptyHint}>
            Start one for a trip, a food crawl, or a running argument about the city's best biryani.
            Pick friends to invite — whoever accepts can add to it.
          </p>
          <button className={styles.createBtn} onClick={() => setShowCreate(true)}>
            <PlusIcon /> Create a group list
          </button>
        </div>
      )}

      {!loading && !error && lists.length > 0 && (
        <div className={styles.grid}>
          {lists.map(l => (
            <div key={l.id} className={styles.listCard} onClick={() => setOpenId(l.id)}>
              <div className={styles.cardTop}>
                <h3 className={styles.listName}>{l.name}</h3>
                {l.my_role === 'owner' && <span className={styles.ownerTag}>owner</span>}
              </div>
              <div className={styles.cardMeta}>
                <span className={styles.metaPill}>
                  {l.member_count} member{l.member_count !== 1 ? 's' : ''}
                </span>
                {l.pending_count > 0 && (
                  <span className={`${styles.metaPill} ${styles.metaPending}`}>
                    {l.pending_count} invited
                  </span>
                )}
                <span className={styles.itemCount}>
                  {l.item_count ?? 0} item{(l.item_count ?? 0) !== 1 ? 's' : ''}
                </span>
              </div>
              <p className={styles.cardHint}>Open list →</p>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}