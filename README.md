# Nestor for Home Assistant

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/hacs/integration)
[![Version](https://img.shields.io/badge/version-0.1.0-blue.svg)](https://github.com/whanegen-business/nestor-homeassistant/releases)
[![HA Version](https://img.shields.io/badge/Home%20Assistant-2024.1%2B-brightgreen.svg)](https://www.home-assistant.io/)

Intégration Home Assistant pour **Nestor** — synchronise votre inventaire, liste de courses et routines depuis Firestore directement dans Home Assistant.

---

## Fonctionnalités

- 📦 **Inventaire** — nombre de produits, répartition par emplacement
- 🛒 **Liste de courses** — articles à acheter, ajout et validation via services ou Assist
- ⚠️ **Péremptions** — alertes sur les produits qui expirent bientôt
- 🔁 **Routines** — suivi des tâches récurrentes et de leurs échéances
- 🎙️ **Assist** — commandes vocales en français pour piloter Nestor

---

## Prérequis

- Home Assistant 2024.1 ou supérieur
- Un projet Firebase avec Firestore
- Un compte de service Firebase (clé JSON)
- [HACS](https://hacs.xyz/) installé

---

## Installation via HACS

1. Dans HACS → **Intégrations** → ⋮ → **Dépôts personnalisés**
2. URL : `https://github.com/whanegen-business/nestor-homeassistant`
3. Catégorie : **Intégration** → **Ajouter**
4. Cherchez **Nestor** dans HACS → **Télécharger**
5. Redémarrez Home Assistant

---

## Configuration

### 1. Obtenir la clé Service Account Firebase

1. [Console Firebase](https://console.firebase.google.com) → votre projet
2. ⚙️ Paramètres du projet → **Comptes de service**
3. **Générer une nouvelle clé privée** → téléchargez le fichier `.json`

### 2. Ajouter l'intégration

1. Paramètres → Intégrations → **+ Ajouter une intégration** → cherchez **Nestor**
2. Collez le contenu complet du fichier `.json` dans le champ prévu
3. Entrez votre `householdId` (identifiant du foyer dans Firestore)
4. Validez — la connexion est testée avant d'enregistrer

### 3. Options

Après installation, vous pouvez ajuster le **seuil de péremption** (nombre de jours avant expiration déclenchant l'alerte, défaut : 3 jours) via :

Paramètres → Intégrations → Nestor → **Configurer**

---

## Entités créées

| Entité | Type | Description |
|--------|------|-------------|
| `sensor.nestor_courses_a_acheter` | Sensor | Nombre d'articles non achetés |
| `sensor.nestor_inventaire_total` | Sensor | Nombre total de produits en inventaire |
| `sensor.nestor_peremptions_proches` | Sensor | Nombre d'unités expirant dans ≤ N jours |
| `sensor.nestor_routines_a_faire` | Sensor | Nombre de routines dues ou en retard |
| `sensor.nestor_prochaine_peremption` | Sensor | Date de la prochaine péremption |
| `binary_sensor.nestor_peremption_urgente` | Binary Sensor | `on` si ≥1 produit expire dans ≤ 1 jour |

---

## Services

### `nestor.add_to_shopping_list`
Ajoute un article à la liste de courses.

```yaml
service: nestor.add_to_shopping_list
data:
  name: "Lait"
  quantity: "2 L"  # optionnel
```

### `nestor.mark_bought`
Marque un article comme acheté (par nom).

```yaml
service: nestor.mark_bought
data:
  name: "Lait"
```

### `nestor.complete_routine`
Valide une routine et recalcule la prochaine échéance.

```yaml
service: nestor.complete_routine
data:
  name: "Changer les draps"
```

### `nestor.refresh`
Force un rafraîchissement immédiat des données.

```yaml
service: nestor.refresh
```

---

## Commandes vocales (Assist)

### 1. Copier le fichier de phrases

Copiez [`custom_sentences/fr/nestor.yaml`](custom_sentences/fr/nestor.yaml) dans `/config/custom_sentences/fr/` sur votre Home Assistant.

### 2. Ajouter l'intent_script dans `configuration.yaml`

```yaml
intent_script:
  NestorAddShopping:
    action:
      service: nestor.add_to_shopping_list
      data:
        name: "{{ item }}"
    speech:
      text: "{{ item }} ajouté à la liste de courses."

  NestorMarkBought:
    action:
      service: nestor.mark_bought
      data:
        name: "{{ item }}"
    speech:
      text: "{{ item }} marqué comme acheté."

  NestorCompleteRoutine:
    action:
      service: nestor.complete_routine
      data:
        name: "{{ routine }}"
    speech:
      text: "Routine {{ routine }} validée."

  NestorRefresh:
    action:
      service: nestor.refresh
    speech:
      text: "Données Nestor actualisées."
```

### 3. Exemples de phrases

| Phrase | Action |
|--------|--------|
| "nestor ajoute lait" | Ajoute le lait à la liste de courses |
| "nestor marque lait acheté" | Coche le lait comme acheté |
| "nestor routine changer les draps faite" | Valide la routine |
| "rafraîchis nestor" | Force la synchronisation |

---

## Architecture technique

- **Authentification** : JWT RS256 signé avec la clé Service Account, échangé contre un token OAuth2 Google (auto-renouvelé toutes les ~50 min)
- **Transport** : API REST Firestore via `aiohttp` (pas de SDK Firebase, compatible ARM64)
- **Polling** : `DataUpdateCoordinator` toutes les 3 minutes
- **Dépendances** : `PyJWT>=2.8.0`, `cryptography>=41.0.0` (installées automatiquement par HA)

---

## Sécurité

La clé Service Account donne un accès admin à votre base Firestore. Elle est stockée uniquement dans le stockage interne de Home Assistant (`.storage/core.config_entries`), jamais en clair dans un fichier YAML versionné.

En cas de compromission : Console Firebase → Comptes de service → supprimez et régénérez la clé.

---

## Licence

MIT — voir [LICENSE](LICENSE)
