<!DOCTYPE html>
<html lang="{{ langue }}">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Malove AI</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@500;700&family=Inter:wght@400;500;600&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="{{ url_for('static', filename='css/style.css') }}">
</head>
<body class="page-login">

    <main class="login-carte">
        <!-- Le robot Malove : ses yeux s'allument au survol -->
        <svg class="login-robot" viewBox="0 0 380 380" role="img" aria-label="Malove AI">
            <defs>
                <linearGradient id="fond" x1="0%" y1="0%" x2="100%" y2="100%">
                    <stop offset="0%" stop-color="#8b5cf6"/>
                    <stop offset="100%" stop-color="#ec4899"/>
                </linearGradient>
            </defs>
            <circle cx="190" cy="190" r="170" fill="url(#fond)"/>
            <rect x="118" y="118" width="144" height="128" rx="36" fill="#ffffff"/>
            <rect x="140" y="90" width="10" height="34" rx="5" fill="#ffffff"/>
            <rect x="230" y="90" width="10" height="34" rx="5" fill="#ffffff"/>
            <circle cx="145" cy="88" r="9" fill="#ec4899"/>
            <circle cx="235" cy="88" r="9" fill="#8b5cf6"/>
            <circle class="oeil" cx="160" cy="178" r="15" fill="#8b5cf6"/>
            <circle class="oeil" cx="220" cy="178" r="15" fill="#ec4899"/>
            <path d="M155 218 C 168 235, 212 235, 225 218 C 225 240, 205 252, 190 252 C 175 252, 155 240, 155 218 Z" fill="#ec4899"/>
            <rect x="100" y="185" width="16" height="36" rx="8" fill="#ffffff" opacity="0.85"/>
            <rect x="264" y="185" width="16" height="36" rx="8" fill="#ffffff" opacity="0.85"/>
        </svg>

        <h1 class="login-titre">Malove<span class="point">.</span>ai</h1>
        <p class="login-tagline">{{ t.tagline }}</p>
        <p class="login-intro">{{ t.login_intro }}</p>

        {% if banni %}
        <p class="login-banni">🚫 {{ t.banni }}</p>
        {% endif %}

        <a class="bouton-google" href="{{ url_for('connexion') }}">
            <svg viewBox="0 0 24 24" width="20" height="20" aria-hidden="true">
                <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92a5.06 5.06 0 0 1-2.2 3.32v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.1z"/>
                <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.65l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84A11 11 0 0 0 12 23z"/>
                <path fill="#FBBC05" d="M5.84 14.11a6.6 6.6 0 0 1 0-4.22V7.05H2.18a11 11 0 0 0 0 9.9l3.66-2.84z"/>
                <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.05l3.66 2.84C6.71 7.31 9.14 5.38 12 5.38z"/>
            </svg>
            {{ t.login_button }}
        </a>

        <div class="login-langues">
            <a href="{{ url_for('accueil', lang='fr') }}" class="{{ 'actif' if langue == 'fr' }}">Français</a>
            <span aria-hidden="true">·</span>
            <a href="{{ url_for('accueil', lang='en') }}" class="{{ 'actif' if langue == 'en' }}">English</a>
        </div>
    </main>

</body>
</html>
