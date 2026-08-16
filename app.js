/* =========================================================
   Malove AI — JavaScript
   Ce fichier est visible par tout le monde (F12), c'est normal :
   il ne contient AUCUN secret. La clé API reste sur le serveur.
   ========================================================= */

const T = window.MALOVE.textes;

const zoneMessages   = document.getElementById('messages');
const formulaire     = document.getElementById('formulaire');
const champMessage   = document.getElementById('champ-message');
const boutonEnvoi    = document.getElementById('bouton-envoi');
const compteur       = document.getElementById('compteur');
const affichageRestants = document.getElementById('restants');

let salonActuel = 'ia';
let rafraichissement = null;

/* ---------------------------------------------------------
   AFFICHAGE DES MESSAGES
   --------------------------------------------------------- */
function creerMessage({ texte, auteur, photo, moi, estIA, estErreur }) {
    const bloc = document.createElement('div');
    bloc.className = 'message' + (moi ? ' moi' : '') + (estErreur ? ' erreur' : '');

    if (estIA) {
        const avatar = document.createElement('div');
        avatar.className = 'message-avatar ia';
        avatar.textContent = '🤖';
        bloc.appendChild(avatar);
    } else if (photo) {
        const avatar = document.createElement('img');
        avatar.className = 'message-avatar';
        avatar.src = photo;
        avatar.alt = auteur || '';
        avatar.referrerPolicy = 'no-referrer';
        bloc.appendChild(avatar);
    }

    const corps = document.createElement('div');
    corps.className = 'message-corps';

    if (auteur && !moi) {
        const nom = document.createElement('div');
        nom.className = 'message-auteur';
        nom.textContent = auteur;
        corps.appendChild(nom);
    }

    const contenu = document.createElement('div');
    contenu.className = 'message-texte';
    // textContent (et non innerHTML) : impossible d'injecter du code via un message
    contenu.textContent = texte;
    corps.appendChild(contenu);

    bloc.appendChild(corps);
    return bloc;
}

function ajouterMessage(options) {
    const vide = zoneMessages.querySelector('.vide');
    if (vide) vide.remove();

    zoneMessages.appendChild(creerMessage(options));
    zoneMessages.scrollTop = zoneMessages.scrollHeight;
}

function afficherVide(texte) {
    zoneMessages.innerHTML = '';
    const bloc = document.createElement('p');
    bloc.className = 'vide';
    bloc.textContent = texte;
    zoneMessages.appendChild(bloc);
}

function afficherIndicateur() {
    const bloc = document.createElement('div');
    bloc.className = 'message';
    bloc.id = 'indicateur';
    bloc.innerHTML =
        '<div class="message-avatar ia">🤖</div>' +
        '<div class="message-corps"><div class="ecrit"><span></span><span></span><span></span></div></div>';
    zoneMessages.appendChild(bloc);
    zoneMessages.scrollTop = zoneMessages.scrollHeight;
}

function retirerIndicateur() {
    const bloc = document.getElementById('indicateur');
    if (bloc) bloc.remove();
}

/* ---------------------------------------------------------
   CHARGEMENT DE L'HISTORIQUE
   --------------------------------------------------------- */
async function chargerHistorique(silencieux = false) {
    try {
        const reponse = await fetch(`/api/historique/${salonActuel}`);
        const donnees = await reponse.json();

        if (!donnees.messages || donnees.messages.length === 0) {
            if (!silencieux) {
                afficherVide(salonActuel === 'ia' ? T.videIa : T.videPublic);
            }
            return;
        }

        // En mode silencieux (rafraîchissement auto), on ne recharge que si ça a changé
        const signature = donnees.messages.length + '|' +
            (donnees.messages[donnees.messages.length - 1].contenu || '');
        if (silencieux && zoneMessages.dataset.signature === signature) return;
        zoneMessages.dataset.signature = signature;

        zoneMessages.innerHTML = '';
        for (const message of donnees.messages) {
            ajouterMessage({
                texte:  message.contenu,
                auteur: message.role === 'assistant' ? 'Malove AI' : message.nom,
                photo:  message.photo,
                moi:    message.moi && message.role !== 'assistant',
                estIA:  message.role === 'assistant',
            });
        }
    } catch (e) {
        console.error('Chargement impossible', e);
    }
}

/* ---------------------------------------------------------
   ENVOI D'UN MESSAGE
   --------------------------------------------------------- */
formulaire.addEventListener('submit', async (evenement) => {
    evenement.preventDefault();

    const texte = champMessage.value.trim();
    if (!texte) return;

    champMessage.value = '';
    boutonEnvoi.disabled = true;

    if (salonActuel === 'ia') {
        await envoyerAlIA(texte);
    } else {
        await envoyerAuSalon(texte);
    }

    boutonEnvoi.disabled = false;
    champMessage.focus();
});

async function envoyerAlIA(texte) {
    ajouterMessage({ texte, moi: true });
    afficherIndicateur();

    try {
        const reponse = await fetch('/api/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message: texte }),
        });
        const donnees = await reponse.json();
        retirerIndicateur();

        if (donnees.erreur) {
            ajouterMessage({ texte: donnees.erreur, estIA: true, estErreur: true });
        } else {
            ajouterMessage({ texte: donnees.reponse, auteur: 'Malove AI', estIA: true });
        }

        if (typeof donnees.restants === 'number') {
            affichageRestants.textContent = donnees.restants;
        }
    } catch (e) {
        retirerIndicateur();
        ajouterMessage({ texte: T.erreur, estIA: true, estErreur: true });
    }
}

async function envoyerAuSalon(texte) {
    try {
        const reponse = await fetch('/api/public', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message: texte }),
        });
        const donnees = await reponse.json();

        if (donnees.erreur) {
            ajouterMessage({ texte: donnees.erreur, estIA: true, estErreur: true });
        } else {
            await chargerHistorique();
        }
    } catch (e) {
        ajouterMessage({ texte: T.erreur, estIA: true, estErreur: true });
    }
}

/* ---------------------------------------------------------
   ONGLETS
   --------------------------------------------------------- */
document.querySelectorAll('.onglet').forEach((onglet) => {
    onglet.addEventListener('click', () => {
        document.querySelectorAll('.onglet').forEach((o) => {
            o.classList.remove('actif');
            o.setAttribute('aria-selected', 'false');
        });
        onglet.classList.add('actif');
        onglet.setAttribute('aria-selected', 'true');

        salonActuel = onglet.dataset.salon;
        champMessage.placeholder = salonActuel === 'ia' ? T.placeholderIa : T.placeholderPublic;
        compteur.classList.toggle('masque', salonActuel !== 'ia');

        delete zoneMessages.dataset.signature;
        zoneMessages.innerHTML = '';
        chargerHistorique();
        gererRafraichissement();
    });
});

/* Le salon public se met à jour tout seul toutes les 4 secondes */
function gererRafraichissement() {
    if (rafraichissement) clearInterval(rafraichissement);
    if (salonActuel === 'public') {
        rafraichissement = setInterval(() => chargerHistorique(true), 4000);
    }
}

/* ---------------------------------------------------------
   RÉGLAGES (couleur + langue)
   --------------------------------------------------------- */
const panneau  = document.getElementById('reglages');
const voile    = document.getElementById('voile');
const palette  = document.getElementById('palette');
const choixCouleur = document.getElementById('choix-couleur');
const choixLangue  = document.getElementById('choix-langue');

function ouvrirReglages() { panneau.hidden = false; voile.hidden = false; }
function fermerReglages() { panneau.hidden = true;  voile.hidden = true; }

document.getElementById('ouvrir-reglages').addEventListener('click', ouvrirReglages);
voile.addEventListener('click', fermerReglages);
document.addEventListener('keydown', (e) => { if (e.key === 'Escape') fermerReglages(); });

async function enregistrerReglages(donnees) {
    try {
        await fetch('/api/reglages', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(donnees),
        });
    } catch (e) {
        console.error('Réglages non enregistrés', e);
    }
}

function appliquerCouleur(couleur) {
    document.documentElement.style.setProperty('--accent', couleur);
    choixCouleur.value = couleur;
    document.querySelectorAll('.pastille').forEach((p) => {
        p.classList.toggle('actif', p.dataset.couleur.toLowerCase() === couleur.toLowerCase());
    });
}

palette.addEventListener('click', (evenement) => {
    const pastille = evenement.target.closest('.pastille');
    if (!pastille) return;
    appliquerCouleur(pastille.dataset.couleur);
    enregistrerReglages({ couleur: pastille.dataset.couleur });
});

choixCouleur.addEventListener('change', () => {
    appliquerCouleur(choixCouleur.value);
    enregistrerReglages({ couleur: choixCouleur.value });
});

choixLangue.addEventListener('change', async () => {
    await enregistrerReglages({ langue: choixLangue.value });
    location.reload(); // on recharge pour appliquer les textes traduits
});

/* ---------------------------------------------------------
   DÉMARRAGE
   --------------------------------------------------------- */
appliquerCouleur(choixCouleur.value);
chargerHistorique();
champMessage.focus();
