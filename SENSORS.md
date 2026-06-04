# Nestor HA — Capteurs et services

Données lues toutes les ~3 min par le `DataUpdateCoordinator` depuis les
sous-collections du foyer configuré.

## Capteurs (sensor.py)

### Récapitulatifs (toujours présents)
| Entité                              | Valeur                          | Attributs |
|-------------------------------------|----------------------------------|-----------|
| `sensor.nestor_courses_a_acheter`   | nb d'items `bought == false`     | liste des noms |
| `sensor.nestor_inventaire_total`    | nb de produits en inventaire     | par emplacement |
| `sensor.nestor_peremptions_proches` | nb d'unités expirant ≤ N jours   | liste {nom, date, jours_restants} |
| `sensor.nestor_routines_a_faire`    | nb de routines dues ou en retard | liste {nom, due_date} |
| `sensor.nestor_prochaine_peremption`| date de la péremption la + proche| nom du produit concerné |

> Le seuil N (jours avant péremption) est une option de l'intégration
> (par défaut 3), modifiable dans les options du config entry.

### Binaire pratique pour les automatisations
| Entité                                  | État | Usage |
|-----------------------------------------|------|-------|
| `binary_sensor.nestor_peremption_urgente` | on si ≥1 unité expire ≤ 1 jour | déclencheur TTS/notif |

## Services (services.yaml + services.py)

### `nestor.add_to_shopping_list`
Ajoute un article à la liste de courses du foyer.
```yaml
fields:
  name:     { required: true,  example: "Lait" }
  quantity: { required: false, example: "2 L" }
```
→ POST `shoppingItems` avec `bought=false`, `addedBy="homeassistant"`.

### `nestor.mark_bought`
Coche un article comme acheté (par nom ou id).
```yaml
fields:
  name: { required: true, example: "Lait" }
```
→ PATCH `bought=true`, `boughtAt=now`.

### `nestor.complete_routine`
Valide l'occurrence d'une routine et recalcule la prochaine échéance.
```yaml
fields:
  name: { required: true, example: "Changer les draps" }
```
→ PATCH `lastCompletedAt=now`, recalcul `nextDueDate` selon `frequency`.

### `nestor.refresh`
Force un rafraîchissement immédiat du coordinator (utile pour tester).

## Intégration avec Assist (commandes vocales HA)

Une fois les services exposés, on crée des phrases personnalisées Assist
(`custom_sentences/fr/nestor.yaml`) qui mappent une phrase → un service :

```yaml
language: "fr"
intents:
  NestorAddShopping:
    data:
      - sentences:
          - "ajoute {item} à la liste de courses"
          - "ajoute {item} aux courses"
intent_script:        # dans configuration.yaml ou packages
  NestorAddShopping:
    action:
      - service: nestor.add_to_shopping_list
        data:
          name: "{{ item }}"
    speech:
      text: "{{ item }} ajouté à la liste de courses."
```

> Résultat : "OK Nestor, ajoute du lait à la liste de courses" via Assist →
> l'article apparaît dans la PWA en temps réel.
