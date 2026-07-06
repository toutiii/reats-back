# API Customer — Documentation complète

**Base URL :** `/api/v1/`  
**Version :** v1

---

## Headers requis

### Endpoints publics (inscription, auth, OTP)

| Header | Valeur | Obligatoire |
|---|---|---|
| `App-Origin` | `customer` | ✅ |
| `X-Api-Key` | `<CUSTOMER_APP_API_KEY>` | ✅ |
| `Content-Type` | `application/json` | ✅ |

### Endpoints authentifiés (profil, logout, etc.)

| Header | Valeur | Obligatoire |
|---|---|---|
| `Authorization` | `Bearer <access_token>` | ✅ |
| `Content-Type` | `application/json` | ✅ |

---

## Format des réponses

### Succès

```json
{
  "success": true,
  "message": "Operation successful",
  "data": {}
}
```

### Erreur

```json
{
  "success": false,
  "error": {
    "code": "ERROR_CODE",
    "message": "Description de l'erreur",
    "details": {}
  }
}
```

---

## Endpoints

### 1. Inscription

```
POST /api/v1/customers/
```

**Auth :** API Key  
**Effet :** Crée le compte customer + envoie un OTP par SMS automatiquement + crée un compte Stripe.

**Request :**

```json
{
  "firstname": "Jean",
  "lastname": "Dupont",
  "phone": "0612345678"
}
```

| Champ | Type | Obligatoire | Description |
|---|---|---|---|
| `firstname` | string | ✅ | Prénom — max 100 caractères |
| `lastname` | string | ✅ | Nom — max 100 caractères |
| `phone` | string | ✅ | Numéro — min 10 caractères, converti automatiquement en E.164 |

**Response `201` :**

```json
{
  "success": true,
  "message": "Operation successful",
  "data": {
    "id": 42,
    "firstname": "Jean",
    "lastname": "Dupont",
    "phone": "+33612345678",
    "is_activated": false,
    "stripe_id": null,
    "is_deleted": false
  }
}
```

**Erreurs :**

| HTTP | `error.code` | Cause |
|---|---|---|
| `400` | `USER_ALREADY_EXISTS` | Numéro déjà utilisé |
| `400` | `VALIDATION_ERROR` | Données invalides |
| `403` | — | API Key ou App-Origin invalide |

---

### 2. Vérification OTP

```
POST /api/v1/customers/otp-verify/
```

**Auth :** API Key  
**Effet :** Valide le code OTP reçu par SMS et active le compte (`is_activated` → `true`).

**Request :**

```json
{
  "phone": "+33612345678",
  "otp": "123456"
}
```

| Champ | Type | Obligatoire | Description |
|---|---|---|---|
| `phone` | string | ✅ | Numéro E.164 |
| `otp` | string | ✅ | Code OTP reçu par SMS |

**Response `200` — succès :**

```json
{
  "success": true,
  "message": "Account successfully activated",
  "data": {}
}
```

**Response `400` — échec :**

```json
{
  "success": false,
  "error": {
    "code": "OTP_INVALID",
    "message": "Invalid OTP code",
    "details": {}
  }
}
```

---

### 3. Connexion (Auth)

```
POST /api/v1/customers/auth/
```

**Auth :** API Key  
**Effet :** Vérifie que le customer existe et est activé, puis envoie un OTP par SMS.

**Request :**

```json
{
  "phone": "0612345678"
}
```

| Champ | Type | Obligatoire | Description |
|---|---|---|---|
| `phone` | string | ✅ | Numéro (national ou E.164) |

**Response `200` :**

```json
{
  "success": true,
  "message": "OTP sent successfully",
  "data": {}
}
```

**Erreurs :**

| HTTP | `error.code` | Cause |
|---|---|---|
| `400` | `PHONE_REQUIRED` | Champ `phone` absent |
| `400` | `PHONE_INVALID_FORMAT` | Numéro non parsable |
| `400` | `USER_NOT_FOUND` | Aucun customer avec ce numéro |
| `400` | `ACCOUNT_NOT_ACTIVATED` | Compte non activé |
| `503` | `OTP_SEND_FAILED` | Échec d'envoi SMS |

---

### 4. Re-demander un OTP

```
POST /api/v1/customers/otp/ask/
```

**Auth :** API Key  
**Effet :** Renvoie un OTP par SMS.

**Request :**

```json
{
  "phone": "0612345678"
}
```

**Response `200` :**

```json
{
  "success": true,
  "message": "OTP sent successfully",
  "data": {}
}
```

**Erreurs :**

| HTTP | `error.code` | Cause |
|---|---|---|
| `400` | `PHONE_INVALID_FORMAT` | Numéro non parsable |
| `400` | `USER_NOT_FOUND` | Aucun customer avec ce numéro |

---

### 5. Obtenir les tokens JWT

```
POST /api/v1/token/
```

**Auth :** API Key

> ⚠️ Le header `App-Origin: customer` est **obligatoire**. Ce endpoint est partagé entre les 3 apps. C'est `App-Origin` qui détermine le type d'utilisateur.

**Request :**

```json
{
  "phone": "+33612345678"
}
```

| Champ | Type | Obligatoire | Description |
|---|---|---|---|
| `phone` | string | ✅ | Numéro E.164 |

**Response `200` :**

```json
{
  "success": true,
  "message": "Token generated successfully",
  "data": {
    "token": {
      "refresh": "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9...",
      "access": "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9..."
    },
    "user_id": 42
  }
}
```

| Champ | Type | Description |
|---|---|---|
| `token.access` | string | JWT access — durée : **30 minutes** |
| `token.refresh` | string | JWT refresh — durée : **24 heures** |
| `user_id` | integer | ID du customer |

**Erreurs :**

| HTTP | `error.code` | Cause |
|---|---|---|
| `400` | `USER_NOT_FOUND` | Aucun customer pour ce numéro (avec `App-Origin: customer`) |
| `403` | — | API Key invalide |

---

### 6. Rafraîchir le token

```
POST /api/v1/token/refresh/
```

**Auth :** aucun header spécifique

**Request :**

```json
{
  "refresh": "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

**Response `200` :**

```json
{
  "success": true,
  "message": "Token refreshed successfully",
  "data": {
    "access": "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9...",
    "refresh": "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9..."
  }
}
```

> La rotation est activée : chaque refresh **invalide l'ancien** refresh token et en retourne un nouveau.

**Erreurs :**

| HTTP | `error.code` | Cause |
|---|---|---|
| `401` | `token_not_valid` | Refresh token expiré, blacklisté ou invalide |

---

### 7. Déconnexion

```
POST /api/v1/logout/
```

**Auth :** Bearer JWT  
**Effet :** Blackliste le refresh token.

**Request :**

```json
{
  "refresh": "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

**Response `200` :**

```json
{
  "success": true,
  "message": "Deconnexion reussie",
  "data": {}
}
```

**Erreurs :**

| HTTP | `error.code` | Cause |
|---|---|---|
| `400` | `MISSING_PARAMETERS` | Champ `refresh` absent |
| `400` | `INVALID_DATA` | Refresh token invalide ou déjà blacklisté |
| `401` | `token_not_valid` | Access token expiré ou invalide |

---

## Endpoints Profil (post-onboarding)

> Auth : `Authorization: Bearer <access_token>`

### 8. Récupérer le profil

```
GET /api/v1/customers/{id}/
```

**Response `200` :**

```json
{
  "success": true,
  "message": "Operation successful",
  "data": {
    "id": 42,
    "firstname": "Jean",
    "lastname": "Dupont",
    "phone": "+33612345678",
    "photo": "customers/42/profile_pics/default-profile-pic.jpg",
    "is_activated": true,
    "stripe_id": "cus_abc123",
    "is_deleted": false
  }
}
```

---

### 9. Modifier le profil

```
PATCH /api/v1/customers/{id}/
```

**Content-Type :** `application/json`

**Request :**

```json
{
  "firstname": "Jean",
  "lastname": "Martin"
}
```

| Champ | Type | Obligatoire | Description |
|---|---|---|---|
| `firstname` | string | Non | Nouveau prénom |
| `lastname` | string | Non | Nouveau nom |
| `phone` | string | Non | Nouveau numéro |

**Response `200` :**

```json
{
  "success": true,
  "message": "Operation successful",
  "data": {
    "id": 42,
    "firstname": "Jean",
    "lastname": "Martin",
    "phone": "+33612345678",
    "photo": "customers/42/profile_pics/avatar.jpg",
    "is_activated": true,
    "stripe_id": "cus_abc123",
    "is_deleted": false
  }
}
```

---

### 10. Modifier la photo de profil

```
PATCH /api/v1/customers/{id}/photo/
```

**Content-Type :** `multipart/form-data`

**Request (form-data) :**

| Champ | Type | Obligatoire | Description |
|---|---|---|---|
| `photo` | file | ✅ | Nouvelle photo de profil |

**Response `200` :**

```json
{
  "success": true,
  "message": "Operation successful",
  "data": {
    "photo": "customers/42/profile_pics/avatar.jpg"
  }
}
```

---

### 11. Supprimer le compte

```
DELETE /api/v1/customers/{id}/
```

**Effet :** Soft delete (`is_deleted = true`) + suppression du compte Stripe.

**Response `200` :**

```json
{
  "success": true,
  "message": "compte supprimé avec succès",
  "data": {}
}
```

---

## Discovery & Commande

> Auth : `Authorization: Bearer <access_token>`

### 12. Discovery — Liste des plats

```
GET /api/v1/customers-dishes/
```

**Auth :** Bearer JWT

**Query params :**

| Paramètre | Type | Obligatoire | Description |
|---|---|---|---|
| `search_address_id` | integer | ✅ | ID de l'adresse de livraison du client |
| `delivery_mode` | string | Non | `now` ou `scheduled` |
| `category` | string | Non | Filtre par catégorie |
| `country` | string | Non | Filtre par pays d'origine |
| `search_radius` | integer | Non | Rayon en km (défaut : 10) |
| `sort` | string | Non | `new` ou `famous` |

**Comportement :** Retourne les plats des cuisiniers en ligne dans la zone géographique du client, triés aléatoirement. Si aucun cuisinier trouvé dans la zone, retourne une liste vide.

**Response `200` :**

```json
{
  "success": true,
  "message": "Operation successful",
  "data": [
    {
      "id": 5,
      "name": "Poulet braisé",
      "price": 3500,
      "category": "dish",
      "country": "Cameroun",
      "is_enabled": true,
      "cooker": { "id": 1, "firstname": "Marie" }
    }
  ]
}
```

---

### 13. Menu du cuisinier (EDB)

```
GET /api/v1/customers-cookers/{cooker_id}/menu/
```

**Auth :** Bearer JWT

**Quand l'appeler :** immédiatement après que le client a sélectionné un plat. Permet de savoir quelles étapes upsell afficher dans le tunnel de commande.

**Règle d'affichage :** si une liste est vide, ne pas afficher l'étape correspondante. Entre 0 et 3 étapes supplémentaires selon ce que le cuisinier propose.

**Response `200` :**

```json
{
  "success": true,
  "message": "Operation successful",
  "data": {
    "extras": [
      { "id": 10, "name": "Salade de feuilles", "price": 1500, "category": "starter" }
    ],
    "desserts": [
      { "id": 11, "name": "Beignets", "price": 500, "category": "dessert" }
    ],
    "drinks": [
      { "id": 12, "name": "Bissap", "price": 500 }
    ]
  }
}
```

**Erreurs :**

| HTTP | `error.code` | Cause |
|---|---|---|
| `404` | `NOT_FOUND` | Cuisinier introuvable |

---

## Configuration JWT

| Paramètre | Valeur |
|---|---|
| Algorithme | RS256 |
| Access token | 30 minutes |
| Refresh token | 24 heures |
| Rotation | Activée |
| Blacklist après rotation | Activée |

---

## Codes d'erreur

| `error.code` | HTTP | Signification |
|---|---|---|
| `USER_ALREADY_EXISTS` | `400` | Numéro déjà utilisé |
| `PHONE_REQUIRED` | `400` | Champ phone absent |
| `PHONE_INVALID_FORMAT` | `400` | Numéro non parsable |
| `USER_NOT_FOUND` | `400` | Aucun customer trouvé |
| `ACCOUNT_NOT_ACTIVATED` | `400` | Compte non activé |
| `OTP_INVALID` | `400` | Code OTP invalide ou expiré |
| `OTP_SEND_FAILED` | `503` | Échec d'envoi SMS |
| `VALIDATION_ERROR` | `400` | Données invalides |
| `MISSING_PARAMETERS` | `400` | Paramètre requis manquant |
| `INVALID_DATA` | `400` | Données invalides |
| `token_not_valid` | `401` | JWT expiré ou invalide |
| `PERMISSION_DENIED` | `403` | Accès refusé |
| `NOT_FOUND` | `404` | Ressource introuvable |
