# Nestor for Home Assistant — Structure de l'intégration

Custom component HACS qui connecte Home Assistant à Firestore (la base de Nestor)
pour exposer l'inventaire, les courses et les routines d'**un foyer** sous forme
de capteurs et de services.

Cible : **HA OS** sur Home Assistant Green (ARM64). Pas de SDK lourd : on parle à
Firestore via son **API REST** avec `aiohttp`, et on authentifie un Service Account
en forgeant un JWT (PyJWT + cryptography). Voir `firestore_rest.md`.

## Arborescence

```
nestor-homeassistant/                 # racine du repo GitHub (pour HACS)
├── custom_components/
│   └── nestor/
│       ├── __init__.py               # setup/unload de l'entrée de config
│       ├── manifest.json             # métadonnées + requirements légers
│       ├── config_flow.py            # UI de config (clé JSON + householdId)
│       ├── const.py                  # DOMAIN, clés de conf, intervalle
│       ├── firestore.py              # client REST + auth Service Account
│       ├── coordinator.py            # DataUpdateCoordinator (polling)
│       ├── sensor.py                 # entités capteurs
│       ├── services.yaml             # déclaration des services
│       ├── services.py               # implémentation des services (si séparé)
│       ├── strings.json              # textes du config_flow (EN)
│       └── translations/
│           ├── en.json
│           └── fr.json
├── hacs.json                         # métadonnées HACS
├── README.md
└── LICENSE
```

## Rôle de chaque fichier

- **`manifest.json`** — déclare le domaine, la version, les `requirements`
  (dépendances pip installées automatiquement par HA), le `config_flow: true`,
  et `iot_class: cloud_polling`.

- **`config_flow.py`** — l'écran de configuration dans l'UI HA. L'utilisateur
  y colle le **contenu de la clé Service Account JSON** et saisit le
  **`householdId`** du foyer à suivre. Valide la connexion avant d'enregistrer.

- **`firestore.py`** — la couche d'accès : forge le JWT depuis la clé, obtient
  un access token OAuth2 Google, l'utilise sur les endpoints REST Firestore,
  et désérialise le format typé de Firestore en dicts Python. Cf `firestore_rest.md`.

- **`coordinator.py`** — un `DataUpdateCoordinator` qui, toutes les N minutes,
  lit les sous-collections `inventoryItems`, `shoppingItems`, `routines` du foyer
  et met les données à disposition de toutes les entités. Source unique de vérité.

- **`sensor.py`** — crée les capteurs à partir des données du coordinator
  (cf `SENSORS.md`).

- **`services.yaml` / `services.py`** — les actions appelables depuis les
  automatisations et Assist (cf `SENSORS.md`).

## Données : un seul foyer

Le `householdId` est fixé à la configuration. Tous les chemins Firestore sont
de la forme :

```
households/{householdId}/inventoryItems
households/{householdId}/shoppingItems
households/{householdId}/routines
```

L'évolution multi-foyers (plus tard) consistera à créer une entrée de config par
foyer, chacune avec son `DataUpdateCoordinator` — d'où l'intérêt de bien isoler
le `householdId` dans la config dès maintenant.
