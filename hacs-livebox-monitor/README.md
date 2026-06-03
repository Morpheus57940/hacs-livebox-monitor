# 🟠 Livebox Monitor — Intégration Home Assistant

[![HACS](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://hacs.xyz)
[![Version](https://img.shields.io/github/v/release/votre-pseudo-github/hacs-livebox-monitor)](https://github.com/votre-pseudo-github/hacs-livebox-monitor/releases)
[![Validate](https://github.com/votre-pseudo-github/hacs-livebox-monitor/actions/workflows/validate.yaml/badge.svg)](https://github.com/votre-pseudo-github/hacs-livebox-monitor/actions)

Surveillance complète de votre réseau **Livebox Orange** depuis Home Assistant.

---

## ✨ Fonctionnalités

- 📋 **Liste de tous les appareils** connectés ou connus (ethernet + Wi-Fi)
- 📡 **Suivi de présence** (`device_tracker`) pour les automations home/away
- 🔔 **Alertes** lors de la détection d'un appareil inconnu
- 🔒 **Blocage/déblocage** d'appareils directement depuis HA
- 📊 **Sensors** : nombre d'appareils en ligne, statut WAN, uptime
- 🔄 **Services** : reboot Livebox, scan réseau, nommer un appareil
- 🃏 **Lovelace card** : dashboard visuel complet intégré

---

## 📋 Prérequis

- Home Assistant ≥ 2023.1
- HACS installé
- Livebox Orange (génération 4, 5 ou 6) sur votre réseau local
- Accès admin à la Livebox (même réseau que HA)

---

## 🚀 Installation via HACS (recommandée)

### Option A — Dépôt custom (disponible maintenant)

1. Ouvrir HACS dans Home Assistant
2. Cliquer sur ⋮ → **Dépôts personnalisés**
3. Ajouter : `https://github.com/votre-pseudo-github/hacs-livebox-monitor`
4. Catégorie : **Integration**
5. Cliquer **Télécharger**
6. Redémarrer Home Assistant

### Option B — Store officiel HACS (soumission en cours)

Chercher **"Livebox Monitor"** directement dans le store HACS.

---

## ⚙️ Configuration

1. Aller dans **Paramètres → Appareils & Services → Ajouter une intégration**
2. Chercher **Livebox Monitor**
3. Renseigner :
   - **Adresse IP** : `192.168.1.1` (défaut)
   - **Identifiant** : `admin` (défaut)
   - **Mot de passe** : votre mot de passe Livebox

---

## 🃏 Ajouter la Lovelace Card

### Via l'interface (recommandé)

1. Aller dans **Paramètres → Tableaux de bord → Ressources**
2. Ajouter : `/local/livebox-monitor-card/livebox-monitor-card.js`
3. Type : **Module JavaScript**

Puis dans votre dashboard, ajouter une carte **personnalisée** :

```yaml
type: custom:livebox-monitor-card
title: Mon réseau Livebox
```

### Copie manuelle de la card

Copier le dossier `www/livebox-monitor-card/` dans `/config/www/` de votre HA.

---

## 🔧 Services disponibles

| Service | Description | Paramètres |
|---------|-------------|------------|
| `livebox_monitor.block_device` | Bloquer un appareil | `mac: AA:BB:CC:DD:EE:FF` |
| `livebox_monitor.unblock_device` | Débloquer un appareil | `mac: AA:BB:CC:DD:EE:FF` |
| `livebox_monitor.assign_name` | Nommer un appareil | `mac`, `name` |
| `livebox_monitor.reboot` | Redémarrer la Livebox | — |
| `livebox_monitor.scan_network` | Scanner le réseau | — |

---

## 🤖 Exemples d'automations

### Notification quand un appareil inconnu se connecte

```yaml
automation:
  alias: "Alerte appareil inconnu"
  trigger:
    - platform: state
      entity_id: binary_sensor.livebox_appareil_inconnu_detecte
      to: "on"
  action:
    - service: notify.mobile_app_mon_telephone
      data:
        title: "⚠️ Appareil inconnu sur le réseau !"
        message: >
          Un appareil inconnu vient de se connecter à votre Livebox.
          Vérifiez dans Home Assistant.
```

### Bloquer les écrans des enfants à 21h

```yaml
automation:
  alias: "Contrôle parental — 21h"
  trigger:
    - platform: time
      at: "21:00:00"
  action:
    - service: livebox_monitor.block_device
      data:
        mac: "AA:BB:CC:DD:EE:FF"  # MAC de la tablette enfant
```

### Lumières ON quand vous rentrez (device_tracker)

```yaml
automation:
  alias: "Arrivée maison"
  trigger:
    - platform: state
      entity_id: device_tracker.iphone_de_nicolas
      from: "not_home"
      to: "home"
  action:
    - service: light.turn_on
      target:
        entity_id: light.salon
```

---

## 📊 Entités créées

| Entité | Type | Description |
|--------|------|-------------|
| `sensor.livebox_appareils_connectes` | Sensor | Nb d'appareils en ligne |
| `sensor.livebox_appareils_inconnus` | Sensor | Nb d'appareils inconnus |
| `sensor.livebox_appareils_bloques` | Sensor | Nb d'appareils bloqués |
| `sensor.livebox_statut_wan` | Sensor | État de la connexion WAN |
| `sensor.livebox_uptime` | Sensor | Uptime de la box en secondes |
| `binary_sensor.livebox_connectivite` | Binary | Fibre up/down |
| `binary_sensor.livebox_appareil_inconnu_detecte` | Binary | Alerte appareil inconnu |
| `device_tracker.<nom>` | Tracker | Un par appareil connu |
| `switch.<nom>_acces_reseau` | Switch | Blocage par appareil |

---

## 🐛 Dépannage

**Impossible de se connecter :**
- Vérifier que HA et la Livebox sont sur le même réseau
- Essayer l'IP `192.168.1.1` depuis un navigateur
- Le port 80 doit être accessible

**Mot de passe incorrect :**
- Réinitialiser depuis l'interface web Livebox (192.168.1.1)
- Le mot de passe par défaut est imprimé sous la box

**Appareils non détectés :**
- Augmenter l'intervalle de scan dans les options
- Appeler `livebox_monitor.scan_network` manuellement

**Logs HA :**
```yaml
logger:
  logs:
    custom_components.livebox_monitor: debug
```

---

## 🤝 Contribuer

Les PR sont bienvenues ! Pour signaler un bug ou proposer une fonctionnalité, ouvrez une [issue](https://github.com/votre-pseudo-github/hacs-livebox-monitor/issues).

---

## 📄 Licence

MIT — voir [LICENSE](LICENSE)
