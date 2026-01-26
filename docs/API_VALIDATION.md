# API Input Validation Rules

## Search Filter (`?search=`)

**Caractères autorisés :**
- Lettres (a-z, A-Z) avec accents français (àâäéèêëïîôùûüÿçÀÂÄÉÈÊËÏÎÔÙÛÜŸÇ)
- Chiffres (0-9)
- Espaces
- Tirets (-)
- Apostrophes (')

**Regex de validation (Backend) :**
```regex
^[\w\sàâäéèêëïîôùûüÿçÀÂÄÉÈÊËÏÎÔÙÛÜŸÇ'-]+$
```

**Exemples valides :**
- `très bon`
- `commande-test`
- `l'ordre du jour`
- `Test 123`

**Exemples invalides (retournent HTTP 400) :**
- `test@email.com` (arobase interdit)
- `test&co` (esperluette interdite)
- `test#123` (dièse interdit)
- `<script>` (symboles HTML interdits)

**Réponse d'erreur (HTTP 400 Bad Request) :**
```json
{
  "search": [
    "Le champ de recherche contient des caractères non autorisés. Seuls les lettres, chiffres, espaces, tirets et apostrophes sont acceptés."
  ]
}
```

> [!IMPORTANT]
> **Pour l'équipe Frontend :**
> Veuillez implémenter une validation similaire côté client pour améliorer l'expérience utilisateur et éviter des appels API inutiles.

## Filtres de Date

**Limitation :**
- `created_after` (ou `start_date`) ne peut pas être antérieur à **2 ans** (date glissante).
- `created_after` ne peut pas être supérieure à `created_before`.
- Toute requête dépassant ces limites renverra une erreur HTTP 400.

**Réponse d'erreur (HTTP 400 Bad Request) :**
```json
{
  "created_after": "La date de début ne peut pas être supérieure à la date de fin."
}
// OU
{
  "created_after": "La date ne peut pas remonter à plus de 2 ans (limite: 2024-01-26)."
}
```

> [!TIP]
> **Pour l'équipe Frontend :**
> Voici un exemple de validation en TypeScript pour anticiper les erreurs :
>
> ```typescript
> const validateOrderDates = (after: Date, before?: Date) => {
>   const twoYearsAgo = new Date();
>   twoYearsAgo.setFullYear(twoYearsAgo.getFullYear() - 2);
>
>   if (after < twoYearsAgo) {
>     return "La date ne peut pas remonter à plus de 2 ans.";
>   }
>
>   if (before && after > before) {
>     return "La date de début ne peut pas être supérieure à la date de fin.";
>   }
>
>   return null;
> };
> ```

## Liste Exhaustive des Filtres (Backend)

Voici la liste des paramètres de filtrage disponibles pour les endpoints de commandes :

### Statuts & Dates
| Paramètre | Description |
|-----------|-------------|
| `status` | Filtrage par statut exact (`pending`, `processing`, etc.) |
| `status_in` | Filtrage par plusieurs statuts (CSV, ex: `pending,processing`) |
| `created_after` / `start_date` | Date de création supérieure ou égale (limite 2 ans) |
| `created_before` / `end_date` | Date de création inférieure ou égale |
| `modified_after` / `updated_after` | Date de modification supérieure ou égale |
| `modified_before` / `updated_before` | Date de modification inférieure ou égale |
| `scheduled_date_after` | Date de livraison prévue supérieure ou égale |
| `scheduled_date_before` | Date de livraison prévue inférieure ou égale |

### Montants & Relations
| Paramètre | Description |
|-----------|-------------|
| `min_total` / `min_total_amount` | Montant total (articles + livraison) >= |
| `max_total` / `max_total_amount` | Montant total (articles + livraison) <= |
| `cooker_id` | ID unique du cuisinier |
| `customer_id` | ID unique du client |
| `deliver_id` | ID unique du livreur |
| `dish_id` | Filtre les commandes contenant ce plat |
| `drink_id` | Filtre les commandes contenant cette boisson |

### Notes & Avis
| Paramètre | Description |
|-----------|-------------|
| `rating` | Note exacte (0-5) |
| `min_rating` | Note supérieure ou égale |
| `max_rating` | Note inférieure ou égale |
| `has_rating` | Filtre si la commande a été notée (`true`/`false`) |
| `has_comment` | Filtre si la commande a un commentaire (`true`/`false`) |

### Divers
| Paramètre | Description |
|-----------|-------------|
| `is_scheduled` | Commande planifiée (`true`) ou immédiate (`false`) |
| `period` | Raccourcis temporels : `today`, `yesterday`, `last_7_days`, `last_30_days`, `this_month`, `last_month`, `this_year` |
| `search` | Recherche sur commentaire, plats, boissons et noms (Regex validation active) |
| `ordering` | Tri des résultats. Champs autorisés : `created`, `modified`, `delivery_fees`, `scheduled_date`, `rating` (prefix `-` pour DESC) |

