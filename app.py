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

function creerMessage({ texte, auteur, photo, moi, estIA, estErreur, estVip, email, uid }) {
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
        const ligneAuteur = document.createElement('div');
        ligneAuteur.className = 'message-auteur' + (estVip ? ' vip' : '');
        ligneAuteur.textContent = (estVip ? '⭐ ' : '') + auteur;
        corps.appendChild(ligneAuteur);
    }

    const contenu = document.createElement('div');
    contenu.className = 'message-texte';
    contenu.textContent = texte;
    corps.appendChild(contenu);

    bloc.appendChild(corps);

    if (window.MALOVE.estAdmin && !moi && !estIA && email) {
        const actions = document.createElement('div');
        actions.className = 'message-admin-actions';

        const boutonVip = document.createElement('button');
        boutonVip.className = 'mini-bouton-admin';
        boutonVip.textContent = '⭐';
        boutonVip.title = 'VIP';
        boutonVip.addEventListener('click', () => appelAdmin('/api/admin/vip', { email }, 'adminOkVip'));

        const boutonBan = document.createElement('button');
        boutonBan.className = 'mini-bouton-admin';
        boutonBan.textContent = '🚫';
        boutonBan.title = 'Ban';
        boutonBan.addEventListener('click', () => appelAdmin('/api/admin/ban', { email }, 'adminOkBan'));

        actions.appendChild(boutonVip);
        actions.appendChild(boutonBan);
        bloc.appendChild(actions);
    }

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
                estVip: message.est_vip,
                email:  message.email,
                uid:    message.uid,
            });
        }
    } catch (e) {
        console.error('Chargement impossible', e);
    }
}

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

function gererRafraichissement() {
    if (rafraichissement) clearInterval(rafraichissement);
    if (salonActuel === 'public') {
        rafraichissement = setInterval(() => chargerHistorique(true), 4000);
    }
}

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
    location.reload();
});

async function appelAdmin(url, corps, cleTexteSucces) {
    try {
        const reponse = await fetch(url, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(corps),
        });
        const donnees = await reponse.json();
        const messageEl = document.getElementById('admin-message');

        if (donnees.erreur) {
            if (messageEl) { messageEl.textContent = donnees.erreur; messageEl.className = 'admin-message erreur'; }
        } else {
            if (messageEl) { messageEl.textContent = T[cleTexteSucces] || 'OK'; messageEl.className = 'admin-message ok'; }
            delete zoneMessages.dataset.signature;
            chargerHistorique();
        }
    } catch (e) {
        console.error('Action admin échouée', e);
    }
}

const boutonAdminVip = document.getElementById('admin-bouton-vip');
const boutonAdminBan = document.getElementById('admin-bouton-ban');
const champAdminEmail = document.getElementById('admin-email');

if (boutonAdminVip) {
    boutonAdminVip.addEventListener('click', () => {
        const email = champAdminEmail.value.trim();
        if (email) appelAdmin('/api/admin/vip', { email }, 'adminOkVip');
    });
}

if (boutonAdminBan) {
    boutonAdminBan.addEventListener('click', () => {
        const email = champAdminEmail.value.trim();
        if (email) appelAdmin('/api/admin/ban', { email }, 'adminOkBan');
    });
}

appliquerCouleur(choixCouleur.value);
chargerHistorique();
champMessage.focus();
