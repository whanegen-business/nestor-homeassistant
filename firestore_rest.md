# Accès Firestore en REST depuis Home Assistant

Pourquoi REST plutôt que `firebase-admin` : sur HA OS (ARM64), on évite les
dépendances natives lourdes (`grpcio`). On utilise `aiohttp` (déjà dans HA) +
un JWT signé avec `PyJWT`/`cryptography` (légers). Tout est **asynchrone**,
comme HA l'exige.

## 1. Authentification Service Account (flux OAuth2 JWT)

La clé Service Account JSON contient notamment :
- `client_email`
- `private_key` (PEM RSA)
- `token_uri` (= `https://oauth2.googleapis.com/token`)
- `project_id`

### Étapes
1. **Forger un JWT** signé RS256 avec la clé privée :
   - `iss` = `client_email`
   - `scope` = `https://www.googleapis.com/auth/datastore`
   - `aud` = `token_uri`
   - `iat` = maintenant, `exp` = maintenant + 3600 s
2. **Échanger le JWT** contre un access token : POST sur `token_uri` avec
   `grant_type=urn:ietf:params:oauth:grant-type:jwt-bearer` et `assertion=<jwt>`.
   Réponse : `{ "access_token": "...", "expires_in": 3599 }`.
3. **Utiliser le token** : header `Authorization: Bearer <access_token>` sur les
   appels REST Firestore.
4. **Rafraîchir** le token avant expiration (toutes les ~50 min).

> Pseudo-code (à implémenter dans `firestore.py`, en async avec aiohttp) :
> ```python
> import time, jwt, aiohttp
>
> def build_jwt(sa: dict) -> str:
>     now = int(time.time())
>     payload = {
>         "iss": sa["client_email"],
>         "scope": "https://www.googleapis.com/auth/datastore",
>         "aud": sa["token_uri"],
>         "iat": now,
>         "exp": now + 3600,
>     }
>     return jwt.encode(payload, sa["private_key"], algorithm="RS256")
>
> async def get_access_token(session, sa) -> tuple[str, float]:
>     assertion = build_jwt(sa)
>     data = {
>         "grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
>         "assertion": assertion,
>     }
>     async with session.post(sa["token_uri"], data=data) as r:
>         j = await r.json()
>         return j["access_token"], time.time() + j["expires_in"] - 60
> ```

## 2. Endpoints REST Firestore

Base : `https://firestore.googleapis.com/v1/projects/{project_id}/databases/(default)/documents`

- **Lister une collection** :
  `GET {base}/households/{hid}/inventoryItems`
- **Lire un document** :
  `GET {base}/households/{hid}/shoppingItems/{docId}`
- **Créer un document** (auto-id) :
  `POST {base}/households/{hid}/shoppingItems`
- **Mettre à jour des champs** :
  `PATCH {base}/households/{hid}/.../{docId}?updateMask.fieldPaths=bought`

## 3. Le format typé Firestore (à désérialiser)

L'API REST renvoie les champs **typés**. Exemple de document `shoppingItems` :

```json
{
  "name": "projects/nestor-c3e19/.../shoppingItems/abc123",
  "fields": {
    "name":     { "stringValue": "Lait demi-écrémé" },
    "quantity": { "stringValue": "2 L" },
    "bought":   { "booleanValue": false }
  },
  "createTime": "2026-06-01T10:00:00Z"
}
```

Prévoir un helper `parse_fields(doc)` qui convertit `fields` en dict plat :
- `stringValue` → str
- `booleanValue` → bool
- `integerValue` → int (attention : renvoyé en string par l'API)
- `arrayValue.values[]` → list (chaque élément est lui-même typé)
- `mapValue.fields` → dict (récursif) — utile pour les `units` de l'inventaire

Et l'inverse `to_fields(dict)` pour les écritures (services).

## 4. Sécurité de la clé

- La clé Service Account donne un **accès admin** à toute la base. Elle est
  stockée par HA dans `.storage` (config entry), jamais en clair dans un YAML
  versionné, jamais sur GitHub.
- Si compromission : Console Firebase → Comptes de service → supprimer/regénérer
  la clé. L'ancienne est immédiatement invalidée.
