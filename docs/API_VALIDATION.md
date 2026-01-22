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
- `created_after` ne peut pas être antérieur à **2 ans** (date glissante).
- Toute requête dépassant cette limite renverra une erreur HTTP 400.

