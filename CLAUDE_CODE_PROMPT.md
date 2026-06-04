# Premier prompt pour Claude Code — Intégration Home Assistant Nestor

Place ce fichier avec `STRUCTURE.md`, `manifest.json`, `firestore_rest.md`,
`SENSORS.md` et `lovelace-dashboard.yaml` dans le dossier de travail, puis colle
le prompt ci-dessous dans Claude Code.

---

## Prompt à coller

> Je développe **Nestor for Home Assistant**, un custom component HACS qui
> connecte Home Assistant à Firestore (la base de mon app Nestor) pour exposer
> l'inventaire, la liste de courses et les routines d'**un seul foyer**.
>
> **Contexte technique important :**
> - Cible : **HA OS sur Home Assistant Green (ARM64)**. On n'utilise donc PAS
>   `firebase-admin` (trop lourd, dépendances natives). On parle à Firestore via
>   son **API REST** avec `aiohttp` (déjà dans HA) et on authentifie un
>   **Service Account** en forgeant un JWT (PyJWT + cryptography). Tout doit être
>   **asynchrone**.
> - `STRUCTURE.md`, `manifest.json`, `firestore_rest.md` et `SENSORS.md`
>   décrivent l'arborescence, les dépendances, le pattern d'auth REST et les
>   entités/services à créer. Lis-les avant de commencer et respecte-les.
>
> **Étape 1 — Squelette + connexion.** Mets en place :
> 1. La structure `custom_components/nestor/` avec `manifest.json` (fourni),
>    `const.py`, `__init__.py`, `strings.json` et `translations/` (fr + en).
> 2. `firestore.py` : le client REST async — forge du JWT, obtention et
>    rafraîchissement de l'access token, helpers `parse_fields` / `to_fields`
>    pour le format typé Firestore, et une méthode `list_collection(path)`.
> 3. `config_flow.py` : un formulaire qui demande (a) le **contenu de la clé
>    Service Account JSON** (champ texte multiligne) et (b) le **householdId**.
>    À la validation, teste la connexion en lisant `households/{id}` ; refuse si
>    échec. Stocke dans le config entry.
> 4. `coordinator.py` : un `DataUpdateCoordinator` qui lit toutes les ~3 min les
>    sous-collections `inventoryItems`, `shoppingItems`, `routines` du foyer.
>
> But de l'étape 1 : l'intégration s'installe via l'UI, se configure avec la clé
> + le householdId, se connecte, et le coordinator récupère les données (visible
> dans les logs). Pas encore de capteurs.
>
> À la fin, propose-moi le plan des étapes suivantes (capteurs, services, Assist).
>
> Important : la clé Service Account ne doit jamais être loggée ni écrite en clair
> ailleurs que dans le config entry HA. Respecte les conventions HA (async,
> DataUpdateCoordinator, config_flow, pas d'I/O bloquante).

---

## Ordre des itérations

1. **Squelette + connexion** (ci-dessus) : install, config_flow, coordinator.
2. **Capteurs** (`sensor.py`) : les 5 sensors récap + le binary_sensor urgent
   (cf `SENSORS.md`). Validation : les entités apparaissent dans HA.
3. **Services** (`services.yaml` + `services.py`) : `add_to_shopping_list`,
   `mark_bought`, `complete_routine`, `refresh`. Validation : appel depuis
   Outils de développement → Actions, et l'item apparaît dans la PWA.
4. **Assist** : `custom_sentences/fr/nestor.yaml` + `intent_script` pour les
   commandes vocales (cf `SENSORS.md`).
5. **Dashboard** : adapter et coller `lovelace-dashboard.yaml`.
6. **Packaging HACS** : `hacs.json`, README, structure repo, puis ajout en
   "custom repository" dans HACS pour tester l'installation.

## Tester en local sur HA OS (avant HACS)
- Copier `custom_components/nestor/` dans le dossier `/config/custom_components/`
  de HA (via l'add-on Samba ou File editor / Studio Code Server).
- Redémarrer Home Assistant.
- Paramètres → Appareils et services → Ajouter une intégration → "Nestor".

## Récupérer la clé Service Account
Console Firebase → ⚙️ Paramètres du projet → **Comptes de service** →
**Générer une nouvelle clé privée** → fichier JSON. On en colle le **contenu**
dans le config_flow. NE PAS committer ce fichier.

## Packaging HACS (étape 6) — hacs.json minimal
```json
{
  "name": "Nestor",
  "render_readme": true,
  "homeassistant": "2024.1.0"
}
```
Le repo GitHub doit avoir `custom_components/nestor/` à la racine. Pour tester
avant publication officielle : HACS → menu ⋮ → "Custom repositories" → coller
l'URL du repo, catégorie "Integration".
