"""
Site web Malove AI
==================

Un site où les gens se connectent avec leur compte Google, discutent avec l'IA,
et peuvent parler ensemble dans un salon public.

🔒 SÉCURITÉ : la clé API Groq n'est JAMAIS envoyée au navigateur.
   Le navigateur parle uniquement à CE serveur (/api/chat), et c'est le serveur
   qui contacte Groq. Si tu ouvres l'inspecteur du navigateur (F12), tu ne verras
   que des appels vers ton propre site — jamais la clé.

Lancement :
    pip install -r requirements.txt
    python app.py
"""

import os
import sqlite3
import time
from datetime import datetime, timedelta
from functools import wraps

from flask import (
    Flask, render_template, request, redirect,
    url_for, session, jsonify, g
)
from authlib.integrations.flask_client import OAuth
from groq import Groq
from dotenv import load_dotenv

# On charge les secrets depuis le fichier .env (jamais dans le code, jamais côté navigateur)
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "change-moi-en-production")

# ---------------------------------------------------------------------------
# CONFIGURATION
# ---------------------------------------------------------------------------
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")

BASE_DE_DONNEES = "malove.db"

# Limites (anti-abus)
LIMITE_IA_PAR_HEURE = 20        # messages à l'IA par personne et par heure
LIMITE_CHAT_PAR_MINUTE = 10     # messages dans le salon public par minute
LONGUEUR_MAX_MESSAGE = 2000     # caractères

client_ia = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None

PERSONNALITE = (
    "Tu es Malove AI, un assistant fun et détendu créé par Ximo. "
    "Tu réponds de façon claire et concise, avec un ton naturel et amical. "
    "Tu adaptes ta langue à celle de la personne qui te parle."
)

# ---------------------------------------------------------------------------
# CONNEXION GOOGLE (OAuth)
# ---------------------------------------------------------------------------
oauth = OAuth(app)
google = oauth.register(
    name="google",
    client_id=GOOGLE_CLIENT_ID,
    client_secret=GOOGLE_CLIENT_SECRET,
    server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
    client_kwargs={"scope": "openid email profile"},
)

# ---------------------------------------------------------------------------
# TRADUCTIONS
# ---------------------------------------------------------------------------
TRADUCTIONS = {
    "fr": {
        "tagline": "Ton assistant IA, en un seul endroit",
        "login_intro": "Connecte-toi avec Google pour discuter avec Malove AI et rejoindre le salon.",
        "login_button": "Continuer avec Google",
        "tab_ia": "Discuter avec l'IA",
        "tab_public": "Salon public",
        "placeholder_ia": "Pose ta question à Malove AI…",
        "placeholder_public": "Écris un message à tout le monde…",
        "send": "Envoyer",
        "settings": "Réglages",
        "accent": "Couleur",
        "language": "Langue",
        "logout": "Se déconnecter",
        "credits_left": "messages IA restants cette heure",
        "empty_ia": "Commence la conversation. Malove AI répond en quelques secondes.",
        "empty_public": "Personne n'a encore écrit. Lance la discussion.",
        "limit_reached": "Limite atteinte. Réessaie dans une heure.",
        "limit_chat": "Tu écris trop vite. Attends quelques secondes.",
        "too_long": "Message trop long.",
        "error": "Une erreur est survenue. Réessaie.",
        "quota": "Le quota IA du jour est épuisé. Réessaie demain.",
    },
    "en": {
        "tagline": "Your AI assistant, all in one place",
        "login_intro": "Sign in with Google to chat with Malove AI and join the room.",
        "login_button": "Continue with Google",
        "tab_ia": "Chat with AI",
        "tab_public": "Public room",
        "placeholder_ia": "Ask Malove AI anything…",
        "placeholder_public": "Write a message to everyone…",
        "send": "Send",
        "settings": "Settings",
        "accent": "Colour",
        "language": "Language",
        "logout": "Sign out",
        "credits_left": "AI messages left this hour",
        "empty_ia": "Start the conversation. Malove AI replies in seconds.",
        "empty_public": "Nobody has written yet. Start the discussion.",
        "limit_reached": "Limit reached. Try again in an hour.",
        "limit_chat": "You're writing too fast. Wait a few seconds.",
        "too_long": "Message too long.",
        "error": "Something went wrong. Try again.",
        "quota": "Today's AI quota is used up. Try again tomorrow.",
    },
}


# ---------------------------------------------------------------------------
# BASE DE DONNÉES
# ---------------------------------------------------------------------------
def get_db():
    """Ouvre (ou réutilise) la connexion SQLite pour la requête en cours."""
    if "db" not in g:
        g.db = sqlite3.connect(BASE_DE_DONNEES)
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def fermer_db(exception):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    """Crée les tables au premier lancement."""
    db = sqlite3.connect(BASE_DE_DONNEES)
    db.executescript("""
        CREATE TABLE IF NOT EXISTS utilisateurs (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            google_id     TEXT UNIQUE NOT NULL,
            email         TEXT,
            nom           TEXT,
            photo         TEXT,
            couleur       TEXT DEFAULT '#8b5cf6',
            langue        TEXT DEFAULT 'fr',
            cree_le       TEXT DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS messages (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            utilisateur_id INTEGER NOT NULL,
            salon         TEXT NOT NULL,          -- 'ia' ou 'public'
            role          TEXT NOT NULL,          -- 'user' ou 'assistant'
            contenu       TEXT NOT NULL,
            cree_le       TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (utilisateur_id) REFERENCES utilisateurs(id)
        );

        CREATE INDEX IF NOT EXISTS idx_messages_salon ON messages(salon, cree_le);
        CREATE INDEX IF NOT EXISTS idx_messages_user  ON messages(utilisateur_id, cree_le);
    """)
    db.commit()
    db.close()


# ---------------------------------------------------------------------------
# OUTILS
# ---------------------------------------------------------------------------
def connexion_requise(f):
    """Empêche l'accès à une page si la personne n'est pas connectée."""
    @wraps(f)
    def decoree(*args, **kwargs):
        if "utilisateur_id" not in session:
            return redirect(url_for("accueil"))
        return f(*args, **kwargs)
    return decoree


def utilisateur_actuel():
    """Renvoie la ligne de la base pour la personne connectée (ou None)."""
    if "utilisateur_id" not in session:
        return None
    db = get_db()
    return db.execute(
        "SELECT * FROM utilisateurs WHERE id = ?", (session["utilisateur_id"],)
    ).fetchone()


def textes(langue):
    """Renvoie le dictionnaire de traductions pour la langue demandée."""
    return TRADUCTIONS.get(langue, TRADUCTIONS["fr"])


def compter_messages_recents(utilisateur_id, salon, minutes):
    """Compte les messages envoyés par cette personne dans les N dernières minutes."""
    db = get_db()
    depuis = (datetime.utcnow() - timedelta(minutes=minutes)).strftime("%Y-%m-%d %H:%M:%S")
    ligne = db.execute(
        """SELECT COUNT(*) AS total FROM messages
           WHERE utilisateur_id = ? AND salon = ? AND role = 'user' AND cree_le >= ?""",
        (utilisateur_id, salon, depuis),
    ).fetchone()
    return ligne["total"]


# ---------------------------------------------------------------------------
# PAGES
# ---------------------------------------------------------------------------
@app.route("/")
def accueil():
    """Page de connexion (ou redirection vers le chat si déjà connecté)."""
    if "utilisateur_id" in session:
        return redirect(url_for("chat"))
    langue = request.args.get("lang", "fr")
    return render_template("login.html", t=textes(langue), langue=langue)


@app.route("/connexion")
def connexion():
    """Redirige vers Google pour se connecter."""
    return google.authorize_redirect(url_for("retour_google", _external=True))


@app.route("/retour-google")
def retour_google():
    """Google renvoie la personne ici après connexion."""
    try:
        jeton = google.authorize_access_token()
        infos = jeton.get("userinfo")
    except Exception as e:
        print(f"[ERREUR OAUTH] {e}")
        return redirect(url_for("accueil"))

    if not infos:
        return redirect(url_for("accueil"))

    db = get_db()
    existant = db.execute(
        "SELECT * FROM utilisateurs WHERE google_id = ?", (infos["sub"],)
    ).fetchone()

    if existant is None:
        curseur = db.execute(
            "INSERT INTO utilisateurs (google_id, email, nom, photo) VALUES (?, ?, ?, ?)",
            (infos["sub"], infos.get("email"), infos.get("name"), infos.get("picture")),
        )
        db.commit()
        session["utilisateur_id"] = curseur.lastrowid
    else:
        session["utilisateur_id"] = existant["id"]

    return redirect(url_for("chat"))


@app.route("/deconnexion")
def deconnexion():
    session.clear()
    return redirect(url_for("accueil"))


@app.route("/chat")
@connexion_requise
def chat():
    """Page principale : chat IA + salon public."""
    utilisateur = utilisateur_actuel()
    if utilisateur is None:
        session.clear()
        return redirect(url_for("accueil"))

    utilises = compter_messages_recents(utilisateur["id"], "ia", 60)
    return render_template(
        "chat.html",
        utilisateur=utilisateur,
        t=textes(utilisateur["langue"]),
        restants=max(0, LIMITE_IA_PAR_HEURE - utilises),
        limite_totale=LIMITE_IA_PAR_HEURE,
    )


# ---------------------------------------------------------------------------
# API (appelée par le navigateur en JavaScript)
# ---------------------------------------------------------------------------
@app.route("/api/reglages", methods=["POST"])
@connexion_requise
def api_reglages():
    """Enregistre la couleur et la langue choisies."""
    donnees = request.get_json(silent=True) or {}
    couleur = donnees.get("couleur")
    langue = donnees.get("langue")

    db = get_db()
    if couleur and couleur.startswith("#") and len(couleur) == 7:
        db.execute("UPDATE utilisateurs SET couleur = ? WHERE id = ?",
                   (couleur, session["utilisateur_id"]))
    if langue in TRADUCTIONS:
        db.execute("UPDATE utilisateurs SET langue = ? WHERE id = ?",
                   (langue, session["utilisateur_id"]))
    db.commit()
    return jsonify({"ok": True})


@app.route("/api/historique/<salon>")
@connexion_requise
def api_historique(salon):
    """Renvoie les messages d'un salon ('ia' pour le chat privé, 'public' pour le salon)."""
    if salon not in ("ia", "public"):
        return jsonify({"erreur": "salon inconnu"}), 400

    db = get_db()
    if salon == "public":
        lignes = db.execute(
            """SELECT m.contenu, m.cree_le, m.role, u.nom, u.photo, u.couleur, u.id AS uid
               FROM messages m JOIN utilisateurs u ON u.id = m.utilisateur_id
               WHERE m.salon = 'public'
               ORDER BY m.id DESC LIMIT 100"""
        ).fetchall()
    else:
        lignes = db.execute(
            """SELECT m.contenu, m.cree_le, m.role, u.nom, u.photo, u.couleur, u.id AS uid
               FROM messages m JOIN utilisateurs u ON u.id = m.utilisateur_id
               WHERE m.salon = 'ia' AND m.utilisateur_id = ?
               ORDER BY m.id DESC LIMIT 100""",
            (session["utilisateur_id"],),
        ).fetchall()

    messages = [dict(ligne) for ligne in reversed(lignes)]
    for message in messages:
        message["moi"] = (message["uid"] == session["utilisateur_id"])
    return jsonify({"messages": messages})


@app.route("/api/public", methods=["POST"])
@connexion_requise
def api_public():
    """Envoie un message dans le salon public."""
    utilisateur = utilisateur_actuel()
    t = textes(utilisateur["langue"])

    contenu = (request.get_json(silent=True) or {}).get("message", "").strip()
    if not contenu:
        return jsonify({"erreur": t["error"]}), 400
    if len(contenu) > LONGUEUR_MAX_MESSAGE:
        return jsonify({"erreur": t["too_long"]}), 400

    if compter_messages_recents(utilisateur["id"], "public", 1) >= LIMITE_CHAT_PAR_MINUTE:
        return jsonify({"erreur": t["limit_chat"]}), 429

    db = get_db()
    db.execute(
        "INSERT INTO messages (utilisateur_id, salon, role, contenu) VALUES (?, 'public', 'user', ?)",
        (utilisateur["id"], contenu),
    )
    db.commit()
    return jsonify({"ok": True})


@app.route("/api/chat", methods=["POST"])
@connexion_requise
def api_chat():
    """
    Envoie un message à l'IA et renvoie sa réponse.

    🔒 C'est ICI que la clé API est utilisée — côté serveur uniquement.
       Le navigateur ne voit jamais ni la clé, ni l'adresse de Groq.
    """
    utilisateur = utilisateur_actuel()
    t = textes(utilisateur["langue"])

    if client_ia is None:
        return jsonify({"erreur": "GROQ_API_KEY manquante dans le fichier .env"}), 500

    contenu = (request.get_json(silent=True) or {}).get("message", "").strip()
    if not contenu:
        return jsonify({"erreur": t["error"]}), 400
    if len(contenu) > LONGUEUR_MAX_MESSAGE:
        return jsonify({"erreur": t["too_long"]}), 400

    utilises = compter_messages_recents(utilisateur["id"], "ia", 60)
    if utilises >= LIMITE_IA_PAR_HEURE:
        return jsonify({"erreur": t["limit_reached"], "restants": 0}), 429

    db = get_db()

    # On récupère les 10 derniers messages pour que l'IA garde le fil de la conversation
    anciens = db.execute(
        """SELECT role, contenu FROM messages
           WHERE salon = 'ia' AND utilisateur_id = ?
           ORDER BY id DESC LIMIT 10""",
        (utilisateur["id"],),
    ).fetchall()

    historique = [{"role": l["role"], "content": l["contenu"]} for l in reversed(anciens)]
    historique.append({"role": "user", "content": contenu})

    try:
        reponse = client_ia.chat.completions.create(
            model="llama-3.3-70b-versatile",
            max_tokens=800,
            messages=[{"role": "system", "content": PERSONNALITE}] + historique,
        )
        texte_reponse = reponse.choices[0].message.content
    except Exception as e:
        print(f"[ERREUR GROQ] {type(e).__name__}: {e}")
        message_erreur = t["quota"] if ("429" in str(e) or "rate_limit" in str(e)) else t["error"]
        return jsonify({"erreur": message_erreur}), 503

    # On enregistre la question et la réponse
    db.execute(
        "INSERT INTO messages (utilisateur_id, salon, role, contenu) VALUES (?, 'ia', 'user', ?)",
        (utilisateur["id"], contenu),
    )
    db.execute(
        "INSERT INTO messages (utilisateur_id, salon, role, contenu) VALUES (?, 'ia', 'assistant', ?)",
        (utilisateur["id"], texte_reponse),
    )
    db.commit()

    return jsonify({
        "reponse": texte_reponse,
        "restants": max(0, LIMITE_IA_PAR_HEURE - utilises - 1),
    })


# On crée la base de données ici (pas seulement dans le bloc __main__ plus bas),
# car gunicorn (utilisé en production sur Render) importe ce fichier sans jamais
# exécuter "if __name__ == '__main__'" — sans cette ligne, la base ne serait
# jamais créée et le site plante.
init_db()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
