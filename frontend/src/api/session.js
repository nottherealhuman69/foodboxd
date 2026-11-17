// Where the logged-in user's token and email are stored.
// This is the only file that touches storage for auth. In the Expo app, swap
// localStorage for expo-secure-store here and nothing else has to change.

const TOKEN_KEY = 'token'
const EMAIL_KEY = 'email'

export const session = {
  getToken: () => localStorage.getItem(TOKEN_KEY),
  getEmail: () => localStorage.getItem(EMAIL_KEY),

  save(token, email) {
    localStorage.setItem(TOKEN_KEY, token)
    localStorage.setItem(EMAIL_KEY, email)
  },

  clear() {
    localStorage.removeItem(TOKEN_KEY)
    localStorage.removeItem(EMAIL_KEY)
  },
}
