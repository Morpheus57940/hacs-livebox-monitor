# 📦 Procédure complète — Dépôt GitHub & Publication HACS

## Étape 1 — Préparer votre compte GitHub

1. Créer un compte sur [github.com](https://github.com) si ce n'est pas fait
2. Installer Git sur votre machine :
   - **Windows** : https://git-scm.com/download/win
   - **macOS** : `brew install git`
   - **Linux** : `sudo apt install git`

---

## Étape 2 — Créer le dépôt GitHub

1. Aller sur https://github.com/new
2. Remplir :
   - **Repository name** : `hacs-livebox-monitor`
   - **Description** : `Livebox Orange monitor integration for Home Assistant`
   - **Visibility** : ✅ **Public** (obligatoire pour HACS)
   - **Add a README** : ❌ non (on en a déjà un)
3. Cliquer **Create repository**

---

## Étape 3 — Remplacer "votre-pseudo-github"

Dans les fichiers suivants, remplacer `votre-pseudo-github` par votre vrai pseudo GitHub :

- `custom_components/livebox_monitor/manifest.json` → champ `codeowners`
- `README.md` → toutes les URLs GitHub
- `www/livebox-monitor-card/livebox-monitor-card.js` → champ `documentationURL`

---

## Étape 4 — Pousser le code sur GitHub

Ouvrir un terminal dans le dossier `hacs-livebox-monitor/` :

```bash
# Initialiser Git
git init
git add .
git commit -m "feat: initial release v1.0.0"

# Connecter à GitHub (remplacer votre-pseudo-github)
git remote add origin https://github.com/votre-pseudo-github/hacs-livebox-monitor.git
git branch -M main
git push -u origin main
```

---

## Étape 5 — Créer la première release

```bash
# Créer le tag v1.0.0
git tag v1.0.0
git push origin v1.0.0
```

GitHub Actions va automatiquement :
- Valider l'intégration (hassfest + HACS)
- Créer une release avec les zips téléchargeables

Vérifier sur : `https://github.com/votre-pseudo-github/hacs-livebox-monitor/actions`

---

## Étape 6 — Tester en local avant publication HACS

### Installation dans HA via dépôt custom

1. Dans HA → HACS → ⋮ (menu) → **Dépôts personnalisés**
2. **URL** : `https://github.com/votre-pseudo-github/hacs-livebox-monitor`
3. **Catégorie** : Integration
4. Cliquer **Ajouter**
5. Rechercher "Livebox Monitor" dans HACS → Télécharger
6. Redémarrer HA
7. Aller dans **Paramètres → Appareils & Services** → Ajouter Livebox Monitor

### Copier la Lovelace card

```bash
# Depuis votre machine, copier via SSH ou Samba vers /config/www/ de HA
cp -r www/livebox-monitor-card/ /chemin/vers/ha/config/www/
```

Dans HA → **Paramètres → Tableaux de bord → Ressources** :
- URL : `/local/livebox-monitor-card/livebox-monitor-card.js`
- Type : Module JavaScript

---

## Étape 7 — Soumettre au store officiel HACS

> ⚠️ Faire cela seulement après avoir testé et validé l'intégration.

### Prérequis de soumission HACS

Vérifier que votre dépôt respecte :
- ✅ Dépôt **public** sur GitHub
- ✅ Fichier `hacs.json` à la racine
- ✅ Au moins **une release** taguée (ex: `v1.0.0`)
- ✅ CI passing (badge vert sur les GitHub Actions)
- ✅ `README.md` en anglais avec description claire
- ✅ `manifest.json` valide avec `version`, `domain`, `codeowners`

### Soumettre la PR

1. Forker le dépôt : https://github.com/hacs/default
2. Cloner votre fork :
   ```bash
   git clone https://github.com/VOTRE-PSEUDO/default.git
   cd default
   ```
3. Ajouter votre intégration dans `custom_components` (fichier JSON) :
   ```bash
   echo '"votre-pseudo-github/hacs-livebox-monitor"' >> custom_components
   ```
4. Commit + push + ouvrir une Pull Request sur `hacs/default`
5. L'équipe HACS review en 1 à 4 semaines

---

## Étape 8 — Mettre à jour l'intégration

Pour chaque nouvelle version :

```bash
# Modifier les fichiers, puis :
git add .
git commit -m "feat: description de la mise à jour"

# Mettre à jour la version dans manifest.json et hacs.json
# Exemple : "version": "1.1.0"

git tag v1.1.0
git push origin main
git push origin v1.1.0
```

Les utilisateurs HACS verront une mise à jour disponible automatiquement.

---

## 📁 Arborescence finale du dépôt

```
hacs-livebox-monitor/
├── hacs.json                          ← requis HACS
├── README.md                          ← documentation
├── LICENSE                            ← MIT
├── custom_components/
│   └── livebox_monitor/
│       ├── __init__.py                ← setup HA
│       ├── manifest.json              ← métadonnées
│       ├── config_flow.py             ← UI configuration
│       ├── coordinator.py             ← DataUpdateCoordinator
│       ├── api.py                     ← client Livebox
│       ├── const.py                   ← constantes
│       ├── sensor.py                  ← capteurs
│       ├── binary_sensor.py           ← capteurs binaires
│       ├── device_tracker.py          ← suivi de présence
│       ├── switch.py                  ← blocage appareils
│       ├── services.yaml              ← déclaration services
│       ├── strings.json               ← i18n
│       └── translations/
│           ├── fr.json
│           └── en.json
├── www/
│   └── livebox-monitor-card/
│       └── livebox-monitor-card.js    ← Lovelace card
└── .github/
    └── workflows/
        ├── validate.yaml              ← CI validation
        └── release.yaml               ← CI release auto
```
