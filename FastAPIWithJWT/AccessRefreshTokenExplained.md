### 🎭 Think of “tokens” like movie tickets
You know, when you go to a movie hall:
- At the entrance, you show your main ticket to enter.
- Once inside, if you want to leave and come back (popcorn / washroom), you get a hand stamp.

#### Now compare with backend authentication:
| Real world   | Computers         |
| ------------ | ----------------- |
| Movie hall   | Backend APIs      |
| Entry ticket | **Access Token**  |
| Hand stamp   | **Refresh Token** |

Both prove you're allowed to be inside, but their purpose and lifespan are different.

### 🔥 ACCESS TOKEN (short-lived “entry ticket”)
- Given after user logs in
- Sent with every API call:
- Authorization: Bearer <access token>
- Backend uses it to identify the user
- Expires quickly (like 5–15 minutes)

### 👉 Why short expiry?
If someone steals this token, they can only use it for a few minutes.

### 🔄 REFRESH TOKEN (long-lived “hand stamp”)
- Also given during login
- NOT sent with every API request
- Only used to get a new access token when it expires
- Lasts longer (days or weeks)

### 👉 Why long expiry?
So the user doesn't need to enter password again and again.

### 🔁 How they work together
User logs in →
Backend gives two tokens:
| Real world   | Computers         |
| ------------ | ----------------- |
| Movie hall   | Backend APIs      |
| Entry ticket | **Access Token**  |
| Hand stamp   | **Refresh Token** |

User makes requests using only access token.
### When access token expires:

Instead of forcing user to login again,
client calls:
```
bash
POST /refresh
{
   "refresh_token": "<refresh-token>"
}
```

Backend answers:
```
pgsql
Here is a new access token (and maybe a new refresh token)
```

👉 User stays logged in without typing password again.

### 📌 SUPER SIMPLE VISUAL
```
pgsql
           Login (/login)
               ↓
     ┌─────────────────────┐
     │  access_token       │  → used in every request, expires fast
     │  refresh_token      │  → used rarely, expires slowly
     └─────────────────────┘
```

When access token expires:
```
pgsql
   FRONTEND → /refresh?refresh_token=XYZ
                          ↓
                  new access_token
```
### 😎 Why not only 1 token?

Because security.

**If a long-lived token is stolen → DANGER**

Hacker gets months of access.

**If only access token exists and expires in 10 minutes**

User would need to login every 10 minutes → terrible UX

So the combo solves it:

| Token   | Lifetime | Purpose                               |
| ------- | -------- | ------------------------------------- |
| Access  | short    | Protects APIs                         |
| Refresh | long     | Keeps user logged in without password |

### ⚠️ Big Rule

👉 Access token sends with every request
👉 Refresh token should NOT send with every request

Otherwise refresh token might leak → then it’s over.

### 🕵️ Where each token should be stored (Frontends)
| Token         | Where normally stored            |
| ------------- | -------------------------------- |
| access_token  | memory / localStorage            |
| refresh_token | HttpOnly cookie / secure storage |


(So JS can't steal refresh token)

## 🧠 Final summary in 1 line

- Access token = to access API
- Refresh token = to get new access token without logging in again