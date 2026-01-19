# Workflow API Cooker (`cooker_app`)

Ce document présente le workflow logique pour un cuisinier. 

> [!IMPORTANT]
> **L'Étape 1 (Inscription) est obligatoire avant de pouvoir passer à l'Étape 2 (Authentification).**  
> Toute tentative d'authentification (`/auth/` ou `/token/`) pour un numéro de téléphone non enregistré ou non activé retournera une erreur 404 ou 403.

---

## 🟢 Étape 1 : Inscription & Activation

### 1.1 Inscription du Cuisinier
**Endpoint** : `POST /api/v1/cookers/`  
**Format** : `multipart/form-data`  

**Exemple d'Entrée (JSON simulé)** :
```json
{
  "firstname": "Jean",
  "lastname": "Cuisinier",
  "phone": "+33612345678",
  "siret": "12345678901234",
  "street_number": "10",
  "street_name": "Rue de la Paix",
  "postal_code": "75001",
  "town": "Paris",
  "max_order_number": 5
}
```

### 1.2 Vérification du Code OTP
**Endpoint** : `POST /api/v1/cookers/otp-verify/`

**Entrée** :
```json
{
  "phone": "+33612345678",
  "code": "123456"
}
```
**Sortie** :
```json
{
  "success": true,
  "message": "Le compte a été activé avec succès",
  "data": null
}
```

---

## 🔵 Étape 2 : Authentification (Login)

### 2.1 Demande de Connexion (Envoi OTP)
**Endpoint** : `POST /api/v1/cookers/auth/`

**Entrée** :
```json
{
  "phone": "+33612345678"
}
```

### 2.2 Obtention des Tokens JWT
**Endpoint** : `POST /api/v1/token/`  
**Header Requis** : `App-Origin: cooker`

**Entrée** :
```json
{
  "phone": "+33612345678"
}
```
**Sortie** :
```json
{
  "success": true,
  "message": "Token généré avec succès",
  "data": {
    "token": {
      "refresh": "eyJhbG...",
      "access": "eyJhbG..."
    },
    "user_id": 12
  }
}
```

---

## 🟡 Étape 3 : Configuration de la Cuisine

### 3.1 Ajout d'un Plat
**Endpoint** : `POST /api/v1/dishes/`  
**Format** : `multipart/form-data`

**Exemple d'Entrée** :
```json
{
  "cooker": 12,
  "name": "Lasagnes Maison",
  "price": 12.50,
  "category": "dish",
  "country": "Italy",
  "description": "De délicieuses lasagnes au boeuf",
  "photo": "(fichier image)"
}
```

---

## 🟠 Étape 4 : Gestion des Commandes (Opérations)

### 4.1 Voir les Commandes Actives
**Endpoint** : `GET /api/v1/cookers-orders/?status=PENDING`

**Sortie** :
```json
{
  "success": true,
  "data": [
    {
      "id": 101,
      "status": "PENDING",
      "customer": {
        "firstname": "Alice",
        "lastname": "Dupont"
      },
      "dishes_items": [
        {
          "dish": { "name": "Lasagnes Maison", "price": 12.5 },
          "dish_quantity": 2
        }
      ],
      "sub_total": 25.0,
      "service_fees": 3.75,
      "total_amount": 33.65,
      "delivery_fees": 4.90
    }
  ]
}
```

### 4.2 Accepter/Mettre à jour une Commande
**Endpoint** : `PATCH /api/v1/cookers-orders/{id}/`

**Entrée** :
```json
{
  "status": "PROCESSING"
}
```

---

## 🔴 Étape 5 : Pilotage & Historique

### 5.1 Dashboard (KPIs)
**Endpoint** : `GET /api/v1/cookers-dashboard/?start_date=2024-01-01&end_date=2024-01-31`

**Sortie** :
```json
{
  "success": true,
  "data": {
    "COMPLETED": 45,
    "CANCELLED_BY_COOKER": 2,
    "DELIVERED": 40
  }
}
```

### 5.2 Historique Complet
**Endpoint** : `GET /api/v1/cookers-orders-history/`
