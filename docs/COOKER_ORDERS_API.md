# API Cuisinier — Documentation Commandes

**Base URL :** `/api/v1/`  
**Auth :** Bearer JWT — header `Authorization: Bearer <access_token>` obligatoire sur tous les endpoints.

---

## Format des réponses

### Succès

```json
{
  "success": true,
  "message": "Operation successful",
  "data": { ... }
}
```

### Erreur

```json
{
  "success": false,
  "error": {
    "code": "TRANSITION_ERROR",
    "message": "Cannot transition from PendingState to PreparingState",
    "details": {}
  }
}
```

### Réponse paginée

```json
{
  "success": true,
  "message": "Operation successful",
  "data": {
    "results": [ ... ],
    "pagination": {
      "current_page": 1,
      "total_pages": 3,
      "total_items": 27,
      "items_per_page": 10
    }
  }
}
```

> **Pagination :** paramètres `?page=2&page_size=20` (max 100). Défaut : 10 par page.

---

## Cycle de vie d'une commande

```
PENDING ──[accept]──▶ ACCEPTED ──[start-preparation]──▶ PREPARING ──[mark-ready]──▶ READY
   │                      │                                  │
   └──[cancel]──▶         └──[cancel]──▶                    └──[cancel]──▶
               CANCELLED                CANCELLED                        CANCELLED
```

| Statut | Description |
|---|---|
| `pending` | Commande en attente de réponse du cuisinier |
| `accepted` | Cuisinier a accepté |
| `preparing` | Cuisinier a commencé la préparation |
| `ready` | Commande prête pour la livraison |
| `delivering` | En cours de livraison (géré par le livreur) |
| `completed` | Livré — état terminal |
| `cancelled` | Annulée — état terminal. Voir champ `cancelled_by` |
| `not_accepted` | Délai dépassé, cuisinier n'a pas répondu — état terminal |

> **Note :** les transitions `delivering` et `completed` sont gérées par l'application livreur, pas par le cuisinier.

---

## Endpoints

### 1. Lister les commandes actives

```
GET /api/v1/cookers-orders/
```

Retourne les commandes actives du cuisinier connecté.

**Query params :**

| Param | Type | Obligatoire | Valeurs acceptées | Défaut |
|---|---|---|---|---|
| `status` | string | Non | `pending`, `accepted`, `preparing`, `ready` | `pending` |
| `page` | integer | Non | — | `1` |
| `page_size` | integer | Non | max `100` | `10` |

> ⚠️ Si `status` n'est pas une valeur valide, l'API retourne **HTTP 400** avec le code `INVALID_ORDER_STATUS`.

**Réponse 200 :**

```json
{
  "success": true,
  "message": "Operation successful",
  "data": {
    "results": [
      {
        "id": 1582,
        "status": "pending",
        "created": "2026-05-15T08:41:18Z",
        "customer": {
          "id": 13,
          "firstname": "Jane",
          "lastname": "Smith"
        },
        "address": {
          "id": 10,
          "postal_code": "75008",
          "town": "Paris"
        },
        "dishes_items": [
          {
            "id": 44,
            "name": "Homemade Burger",
            "category": "dish",
            "image": "https://s3.../burger.jpg",
            "quantity": 2,
            "unit_price": 12.5
          }
        ],
        "drinks_items": [
          {
            "id": 5,
            "name": "Red Wine",
            "capacity": "75cl",
            "image": "https://s3.../wine.jpg",
            "quantity": 1,
            "unit_price": 4.0
          }
        ],
        "items_count": 3,
        "sub_total": 29.0,
        "delivery_fees": 5.0,
        "service_fees": 2.03,
        "total_amount": 36.03
      }
    ],
    "pagination": {
      "current_page": 1,
      "total_pages": 1,
      "total_items": 1,
      "items_per_page": 10
    }
  }
}
```

---

### 2. Détail d'une commande

```
GET /api/v1/cookers-orders/{id}/
```

**Réponse 200 :**

```json
{
  "success": true,
  "message": "Operation successful",
  "data": {
    "id": 1582,
    "status": "pending",
    "created": "2026-05-15T08:41:18.646583Z",
    "accepted_date": null,
    "preparing_date": null,
    "ready_date": null,
    "delivering_date": null,
    "completed_date": null,
    "cancelled_date": null,
    "cancelled_by": null,
    "scheduled_delivery_date": null,
    "is_scheduled": false,
    "delivery_fees": 5.0,
    "delivery_fees_bonus": null,
    "delivery_distance": 1200.0,
    "delivery_initial_distance": null,
    "paid_date": "2026-05-15T08:40:50Z",
    "rating": 0.0,
    "comment": null,
    "customer": {
      "id": 13,
      "firstname": "Jane",
      "lastname": "Smith"
    },
    "address": {
      "id": 10,
      "postal_code": "75008",
      "town": "Paris"
    },
    "delivery_man": null,
    "dishes_items": [
      {
        "id": 44,
        "name": "Homemade Burger",
        "description": "Juicy beef burger...",
        "price": 12.5,
        "category": "dish",
        "image": "https://s3.../burger.jpg",
        "ingredients": [],
        "ratings": [],
        "is_enabled": true,
        "is_suitable_for_quick_delivery": false,
        "is_suitable_for_scheduled_delivery": false,
        "cost": null,
        "preparation_time": null,
        "max_concurrent_orders": 10,
        "margin": null,
        "cooker": {
          "id": 6,
          "firstname": "John",
          "lastname": "Doe"
        },
        "quantity": 2
      }
    ],
    "drinks_items": [
      {
        "id": 5,
        "name": "Red Wine",
        "description": "Full-bodied red wine.",
        "price": 4.0,
        "unit": "centiliters",
        "capacity": 75,
        "is_enabled": true,
        "available": true,
        "image": "https://s3.../wine.jpg",
        "ingredients": [],
        "ratings": [],
        "nutritional_info": {},
        "cost": null,
        "margin": null,
        "created_at": "2026-05-15T08:00:00Z",
        "updated_at": "2026-05-15T08:00:00Z",
        "quantity": 1
      }
    ],
    "items_count": 3,
    "sub_total": 29.0,
    "service_fees": 2.03,
    "total_amount": 36.03
  }
}
```

> **Structure items :** `dishes_items` et `drinks_items` exposent tous les champs du plat/boisson directement à la racine de l'objet. Le champ `quantity` indique la quantité commandée.

**Erreurs :**

| Code HTTP | Cause |
|---|---|
| `404` | Commande introuvable ou appartient à un autre cuisinier |

---

### 3. Accepter une commande

```
POST /api/v1/cookers-orders/{id}/accept/
```

**Body :** aucun  
**Transition :** `pending` → `accepted`  
**Effet :** enregistre `accepted_date`

**Réponse 200 :** objet commande complet (même format que le détail)

**Erreurs :**

| Code HTTP | `error.code` | Cause |
|---|---|---|
| `404` | — | Commande introuvable |
| `409` | `TRANSITION_ERROR` | Commande pas en `pending` |
| `500` | `INTERNAL_SERVER_ERROR` | Erreur serveur |

---

### 4. Démarrer la préparation

```
POST /api/v1/cookers-orders/{id}/start-preparation/
```

**Body :** aucun  
**Transition :** `accepted` → `preparing`  
**Effet :** enregistre `preparing_date`

**Réponse 200 :** objet commande complet

**Erreurs :**

| Code HTTP | `error.code` | Cause |
|---|---|---|
| `404` | — | Commande introuvable |
| `409` | `TRANSITION_ERROR` | Commande pas en `accepted` |
| `500` | `INTERNAL_SERVER_ERROR` | Erreur serveur |

---

### 5. Marquer comme prête

```
POST /api/v1/cookers-orders/{id}/mark-ready/
```

**Body :** aucun  
**Transition :** `preparing` → `ready`  
**Effet :** enregistre `ready_date`

**Réponse 200 :** objet commande complet

**Erreurs :**

| Code HTTP | `error.code` | Cause |
|---|---|---|
| `404` | — | Commande introuvable |
| `409` | `TRANSITION_ERROR` | Commande pas en `preparing` |
| `500` | `INTERNAL_SERVER_ERROR` | Erreur serveur |

---

### 6. Annuler une commande

```
POST /api/v1/cookers-orders/{id}/cancel/
```

**Body :** aucun  
**Transitions autorisées :** `pending` → `cancelled` / `accepted` → `cancelled` / `preparing` → `cancelled`  
**Effets :**
- Enregistre `cancelled_date`
- Pose `cancelled_by = "cooker"`
- Déclenche un **remboursement Stripe 100 %** au client
- Diminue le `acceptance_rate` du cuisinier de **10 points**

**Réponse 200 :** objet commande complet

**Erreurs :**

| Code HTTP | `error.code` | Cause |
|---|---|---|
| `404` | — | Commande introuvable |
| `409` | `TRANSITION_ERROR` | Commande en `ready`, `delivering`, `completed` ou `cancelled` |
| `500` | `INTERNAL_SERVER_ERROR` | Erreur serveur |

---

### 7. Historique des commandes

```
GET /api/v1/cookers-orders-history/
```

Retourne les commandes terminales (`completed`, `cancelled`, `not_accepted`) du cuisinier connecté, triées par date de modification décroissante.

**Query params :**

| Param | Type | Obligatoire | Valeurs acceptées | Description |
|---|---|---|---|---|
| `status` | string | Non | `completed`, `cancelled`, `not_accepted` | Filtre par statut |
| `cancelled_by` | string | Non | `cooker`, `customer`, `system` | Filtre par initiateur d'annulation |
| `start_date` | datetime ISO 8601 | Non | — | Commandes créées **après** cette date |
| `end_date` | datetime ISO 8601 | Non | — | Commandes créées **avant** cette date |
| `page` | integer | Non | — | Défaut `1` |
| `page_size` | integer | Non | max `100` | Défaut `10` |

> ⚠️ Si `status` n'est pas une valeur valide → HTTP 400 code `INVALID_ORDER_STATUS`.  
> ⚠️ Si `cancelled_by` n'est pas une valeur valide → HTTP 400 code `INVALID_DATA`.  
> ⚠️ Si `start_date > end_date` → HTTP 400 message `"La date de début ne peut pas être supérieure à la date de fin."`.

**Réponse 200 :**

```json
{
  "success": true,
  "message": "Operation successful",
  "data": {
    "results": [
      {
        "id": 1582,
        "status": "completed",
        "created": "2026-05-10T15:00:00Z",
        "accepted_date": "2026-05-10T15:05:00Z",
        "preparing_date": "2026-05-10T15:10:00Z",
        "ready_date": "2026-05-10T15:30:00Z",
        "delivering_date": "2026-05-10T15:45:00Z",
        "completed_date": "2026-05-10T16:00:00Z",
        "cancelled_date": null,
        "cancelled_by": null,
        "customer": {
          "id": 13,
          "firstname": "Jane",
          "lastname": "Smith"
        },
        "address": {
          "id": 10,
          "postal_code": "75008",
          "town": "Paris"
        },
        "dishes_items": [
          {
            "id": 44,
            "name": "Homemade Burger",
            "category": "dish",
            "image": "https://s3.../burger.jpg",
            "quantity": 1,
            "unit_price": 12.5
          }
        ],
        "drinks_items": [],
        "items_count": 1,
        "sub_total": 12.5,
        "service_fees": 0.88,
        "total_amount": 18.38
      },
      {
        "id": 1241,
        "status": "cancelled",
        "created": "2026-05-08T12:00:00Z",
        "accepted_date": null,
        "preparing_date": null,
        "ready_date": null,
        "delivering_date": null,
        "completed_date": null,
        "cancelled_date": "2026-05-08T12:05:00Z",
        "cancelled_by": "cooker",
        "customer": {
          "id": 8,
          "firstname": "Marc",
          "lastname": "Dupont"
        },
        "address": {
          "id": 7,
          "postal_code": "69001",
          "town": "Lyon"
        },
        "dishes_items": [],
        "drinks_items": [],
        "items_count": 0,
        "sub_total": 0.0,
        "service_fees": 0.0,
        "total_amount": 3.5
      }
    ],
    "pagination": {
      "current_page": 1,
      "total_pages": 1,
      "total_items": 2,
      "items_per_page": 10
    }
  }
}
```

> **Note :** le champ `cooker` est absent de toutes les réponses commandes. L'identité du cuisinier connecté est disponible via son token JWT.

---

## Règles de calcul des montants

| Champ | Calcul |
|---|---|
| `sub_total` | Somme de `(prix_unitaire × quantité)` pour tous les items |
| `service_fees` | `sub_total × 0.07` arrondi à 2 décimales |
| `delivery_fees` | Calculé à la création selon la distance (Google Maps) |
| `total_amount` | `sub_total + service_fees + delivery_fees` |

---

## Taux d'acceptation (`acceptance_rate`)

Mis à jour automatiquement lors des actions suivantes :

| Événement | Variation |
|---|---|
| Cuisinier annule (`cancel`) | **−10 points** |
| Délai dépassé (`not_accepted`) | **−10 points** |
| Commande complétée (`completed`) | **+2 points** |

**Bornes :** `[0, 100]` — ne peut pas dépasser 100 ni descendre sous 0.

---

## Codes d'erreur

| `error.code` | Code HTTP | Signification |
|---|---|---|
| `TRANSITION_ERROR` | `409` | Transition de statut invalide |
| `INVALID_ORDER_STATUS` | `400` | Valeur de `status` non autorisée |
| `INVALID_DATA` | `400` | Valeur de `cancelled_by` non autorisée |
| `INTERNAL_SERVER_ERROR` | `500` | Erreur serveur inattendue |
| `token_not_valid` | `401` | Token JWT expiré ou invalide |
| `PERMISSION_DENIED` | `403` | Accès refusé |
