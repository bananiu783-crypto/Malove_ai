# Malove AI — le site

Un site où les gens se connectent avec Google, discutent avec l'IA Malove,
et parlent ensemble dans un salon public.

---

## Ce qu'il y a dedans

| Fichier | À quoi ça sert |
|---|---|
| `app.py` | Tout le serveur : connexion Google, chat IA, salon public |
| `templates/login.html` | La page de connexion |
| `templates/chat.html` | La page principale |
| `static/css/style.css` | Le design |
| `static/js/app.js` | Ce qui bouge dans le navigateur |
| `.env` | **Tes secrets** (à créer, jamais à partager) |

---

## Installation, étape par étape

### 1. Installer les librairies

```bash
pip install -r requirements.txt
```

### 2. Créer une clé API Groq (l'IA, gratuite)

1. Va sur **https://console.groq.com/keys**
2. Connecte-toi (Google ou email), clique sur **Create API Key**
3. Copie la clé (elle commence par `gsk_`)

### 3. Créer les identifiants Google (pour le bouton "Continuer avec Google")

1. Va sur **https://console.cloud.google.com/apis/credentials**
2. Crée un projet si tu n'en as pas
3. Clique **Create Credentials → OAuth client ID**
4. Type d'application : **Web application**
5. Dans **Authorized redirect URIs**, ajoute exactement :
   - en local : `http://localhost:5000/retour-google`
   - en ligne : `https://ton-domaine.com/retour-google`
6. Copie le **Client ID** et le **Client Secret**

### 4. Créer le fichier `.env`

Copie `.env.example` en `.env`, puis remplis les 4 valeurs :

```
FLASK_SECRET_KEY=...
GROQ_API_KEY=gsk_...
GOOGLE_CLIENT_ID=...apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=...
```

Pour générer la clé secrète Flask :

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

### 5. Lancer le site

```bash
python app.py
```

Ouvre **http://localhost:5000** dans ton navigateur.

---

## Pourquoi la clé API est invisible dans l'inspecteur (F12)

C'est le point important du projet. Voici comment ça marche :

```
Navigateur  ──►  TON SERVEUR  ──►  Groq (l'IA)
   (F12)          (la clé est ici)
```

- Le navigateur envoie juste ton message à **ton propre site** (`/api/chat`)
- C'est **ton serveur** qui contacte Groq, avec la clé stockée dans `.env`
- La clé ne quitte jamais le serveur : elle n'est **ni dans le HTML, ni dans le JS, ni dans les requêtes réseau**

Si quelqu'un ouvre F12 → onglet Réseau, il verra seulement des appels vers ton site. C'est tout.

**À ne jamais faire** : mettre la clé dans `app.js` ou dans un `<script>` de la page. Là, elle serait visible par tout le monde.

---

## Les limites en place

| Limite | Valeur | Où la changer |
|---|---|---|
| Messages à l'IA | 20 / heure / personne | `LIMITE_IA_PAR_HEURE` dans `app.py` |
| Messages salon public | 10 / minute / personne | `LIMITE_CHAT_PAR_MINUTE` dans `app.py` |
| Longueur d'un message | 2000 caractères | `LONGUEUR_MAX_MESSAGE` dans `app.py` |

---

## Personnalisation

- **Couleur** : chaque personne choisit la sienne dans les réglages (icône engrenage) — elle est sauvegardée sur son compte
- **Langue** : français ou anglais, dans les réglages. Pour ajouter une langue, complète le dictionnaire `TRADUCTIONS` dans `app.py`
- **Personnalité de l'IA** : modifie la variable `PERSONNALITE` dans `app.py`

---

## Mettre le site en ligne

En local, `python app.py` suffit. Pour une vraie mise en ligne :

```bash
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

Trois choses à ne pas oublier :

1. **HTTPS obligatoire** — Google refuse OAuth en HTTP sur un vrai domaine
2. Ajouter l'URL de production dans les **Authorized redirect URIs** de Google
3. Ne jamais envoyer le fichier `.env` sur GitHub (le `.gitignore` s'en charge déjà)

---

## À savoir

- La base de données est un simple fichier `malove.db`, créé tout seul au premier lancement. **Sauvegarde-le** si les conversations comptent.
- SQLite convient très bien jusqu'à quelques dizaines de personnes en même temps. Au-delà, il faudra passer à PostgreSQL.
- Le salon public se rafraîchit toutes les 4 secondes. Simple et efficace pour un petit site ; pour du temps réel instantané il faudrait des WebSockets.
