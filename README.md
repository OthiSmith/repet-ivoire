# Répét'Ivoire

Plateforme web de mise en relation entre parents et répétiteurs à domicile en Côte d'Ivoire.
Application Django (templates côté serveur, Bootstrap 5), compatible SQLite (local) et PostgreSQL (production).

> **État du projet : phase 2 (initialisation) terminée.**
> Le socle technique est en place : configuration, modèle utilisateur, gabarit de base, page d'accueil provisoire, tests.
> L'authentification (phase 3), les profils (phase 4) et la mise en relation (phase 5) arrivent ensuite.

---

## 1. Prérequis

| Outil | Version | Vérifier |
|---|---|---|
| Python | 3.12 | `python --version` |
| Git | récent | `git --version` |
| PostgreSQL | 16 (facultatif en local) | `psql --version` |

Sous Windows, installer Python depuis [python.org](https://www.python.org/downloads/) en cochant **« Add python.exe to PATH »**.

## 2. Installation locale

```bash
# 1. Se placer dans le dossier du projet
cd D:\plateforme-repetiteurs

# 2. Créer l'environnement virtuel
python -m venv venv

# 3. L'activer
#    Windows (PowerShell) :
venv\Scripts\activate
#    macOS / Linux :
source venv/bin/activate

# 4. Installer les dépendances
pip install -r requirements.txt

# 5. Créer le fichier de configuration locale
#    Windows : copy .env.example .env      macOS/Linux : cp .env.example .env
#    puis remplacer SECRET_KEY par une valeur générée avec :
python -c "from django.core.management.utils import get_random_secret_key as g; print(g())"

# 6. Créer la base de données
python manage.py migrate

# 7. Créer un compte administrateur (e-mail, téléphone ivoirien, prénom, nom, mot de passe)
python manage.py createsuperuser

# 8. Lancer le serveur
python manage.py runserver
```

Ouvrir ensuite **http://127.0.0.1:8000/** dans le navigateur.
L'administration technique se trouve sur **http://127.0.0.1:8000/admin-technique/**.

> Si PowerShell refuse d'activer l'environnement (« l'exécution de scripts est désactivée »), exécuter une fois :
> `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`

## 3. Utiliser PostgreSQL (facultatif en local)

```sql
-- Dans psql, en tant qu'administrateur PostgreSQL :
CREATE DATABASE repetivoire ENCODING 'UTF8';
CREATE USER repetivoire WITH PASSWORD 'choisir-un-mot-de-passe';
GRANT ALL PRIVILEGES ON DATABASE repetivoire TO repetivoire;
ALTER DATABASE repetivoire OWNER TO repetivoire;
```

Puis, dans `.env` :

```
DATABASE_URL=postgres://repetivoire:choisir-un-mot-de-passe@localhost:5432/repetivoire
```

et relancer `python manage.py migrate`.

## 4. Lancer les tests

```bash
python manage.py test
```

## 5. Organisation du code

```
plateforme-repetiteurs/
├── config/               Configuration Django
│   ├── settings/
│   │   ├── base.py       Paramètres communs (lus depuis .env)
│   │   ├── dev.py        Développement local (utilisé par manage.py)
│   │   └── prod.py       Production (utilisé par wsgi/asgi)
│   └── urls.py           Routage principal
├── core/                 Socle commun : pages publiques, validateurs, gabarits partagés
├── accounts/             Modèle utilisateur (e-mail + téléphone + rôle), comptes parents
├── catalog/              Matières et niveaux scolaires
├── locations/            District → Région → Ville → Commune → Quartier
├── tutors/               Profils répétiteurs, justificatifs, disponibilités
├── tutoring/             Demandes, propositions, mises en relation
├── notifications/        Notifications internes (canaux externes plus tard)
├── reviews/              Avis (désactivés par défaut)
├── backoffice/           Tableau de bord administrateur
├── templates/            Gabarits HTML (base, partials, pages)
├── static/               CSS, JS, images, bibliothèques servies en local
├── media/                Fichiers publics téléversés (photos)        — non versionné
├── private_media/        Justificatifs (jamais servis directement)   — non versionné
├── requirements/         Dépendances (base.txt, dev.txt)
├── .env.example          Modèle de configuration
└── manage.py
```

Chaque application suit la même découpe : `models.py`, `forms.py`, `views.py`, `urls.py`,
`services.py` (logique métier), `permissions.py`, `admin.py`, `tests/`.

## 6. Choix techniques

- **Django 5.2 LTS**, sans framework front-end. Bootstrap 5.3, Bootstrap Icons et la police Inter sont servis **en local** (aucun CDN : plus fiable et plus rapide en Côte d'Ivoire).
- **Utilisateur personnalisé** (`accounts.User`) : e-mail et téléphone uniques, rôle `PARENT` / `TUTOR` / `ADMIN`. Les numéros sont normalisés au format `+225XXXXXXXXXX`.
- **Sécurité** : mots de passe hachés (PBKDF2), CSRF, cookies `HttpOnly`, blocage après 5 échecs de connexion (django-axes), justificatifs stockés hors du dossier public, réglages HTTPS en production.
- **Interrupteurs** : `FEATURE_REVIEWS_ENABLED` et `FEATURE_PAYMENTS_ENABLED` sont désactivés par défaut.

## 7. Identité visuelle

| Rôle | Couleur |
|---|---|
| Bleu foncé (confiance) | `#0B2545` |
| Bleu principal | `#1D5FD1` |
| Bleu clair (fonds) | `#E8F0FC` |
| Accent (boutons d'action) | `#F28C28` |
| Badge « Vérifié » | `#1E9E6A` |

L'illustration de la page d'accueil est un SVG provisoire. Elle est à remplacer par une photographie dont vous détenez les droits.

## 8. Mise en production (plus tard)

```bash
set DJANGO_SETTINGS_MODULE=config.settings.prod   # Windows
export DJANGO_SETTINGS_MODULE=config.settings.prod # Linux
python manage.py check --deploy
python manage.py collectstatic
```

Prérequis : `DEBUG=False`, `ALLOWED_HOSTS` renseigné, PostgreSQL, HTTPS.
