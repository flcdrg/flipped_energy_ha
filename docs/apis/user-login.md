# POST /user/login

Purpose:

- Authenticate with account email and password.
- Returns token used for Bearer authentication.

URL:

- <https://api.flipped.energy/user/login>

Auth:

- None

Request:

- Method: POST
- Content-Type: application/json
- Body fields:
  - email: string
  - password: string

Example body:

```json
{
  "email": "user@example.com",
  "password": "your-password"
}
```

Observed responses:

- 200: JSON containing token
- 400: invalid username or password (observed as text/plain)
- 401 or 403: unauthorized

Notes:

- Integration reads the token from response.token.
- Missing token is treated as authentication failure.
