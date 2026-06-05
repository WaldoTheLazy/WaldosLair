"""WaldosLair — CSS stilovi. Sav CSS na jednom mjestu."""

DARK_STAR_CSS = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700;900&family=Rajdhani:wght@300;400;600&display=swap');

    html, body, [class*="css"] { background-color: #0a0a0f; color: #e8e8f0; }

    .stApp {
        background: radial-gradient(ellipse at 20% 50%, #0d0d1a 0%, #0a0a0f 60%, #000005 100%);
        min-height: 100vh;
    }

    .stApp::before {
        content: '';
        position: fixed;
        top: 0; left: 0; right: 0; bottom: 0;
        background-image:
            radial-gradient(1px 1px at 10% 15%, rgba(255,255,255,0.6) 0%, transparent 100%),
            radial-gradient(1px 1px at 30% 40%, rgba(255,255,255,0.4) 0%, transparent 100%),
            radial-gradient(1px 1px at 50% 20%, rgba(255,255,255,0.7) 0%, transparent 100%),
            radial-gradient(1px 1px at 70% 60%, rgba(255,255,255,0.5) 0%, transparent 100%),
            radial-gradient(1px 1px at 90% 10%, rgba(255,255,255,0.6) 0%, transparent 100%),
            radial-gradient(1px 1px at 15% 80%, rgba(255,255,255,0.3) 0%, transparent 100%),
            radial-gradient(1px 1px at 85% 85%, rgba(255,255,255,0.5) 0%, transparent 100%),
            radial-gradient(1px 1px at 45% 70%, rgba(255,255,255,0.4) 0%, transparent 100%),
            radial-gradient(1px 1px at 60% 35%, rgba(255,255,255,0.6) 0%, transparent 100%),
            radial-gradient(1px 1px at 25% 55%, rgba(255,255,255,0.3) 0%, transparent 100%);
        pointer-events: none;
        z-index: 0;
    }

    .hero-container {
        display: flex; flex-direction: column; align-items: center;
        justify-content: center; min-height: 85vh; text-align: center; padding: 2rem;
    }
    .hero-title {
        font-family: 'Orbitron', monospace;
        font-size: clamp(2.5rem, 8vw, 5rem);
        font-weight: 900; color: #ffd700;
        text-shadow: 0 0 10px rgba(255,215,0,0.8), 0 0 30px rgba(255,215,0,0.4), 0 0 60px rgba(255,215,0,0.2);
        letter-spacing: 0.15em; margin-bottom: 0.5rem; line-height: 1.1;
    }
    .hero-subtitle {
        font-family: 'Rajdhani', sans-serif;
        font-size: clamp(0.9rem, 2.5vw, 1.3rem);
        color: #a0a0c0; font-style: italic; letter-spacing: 0.05em;
        margin-bottom: 3rem; max-width: 600px; line-height: 1.6;
    }
    .hero-separator {
        width: 200px; height: 2px;
        background: linear-gradient(90deg, transparent, #ffd700, transparent);
        margin: 1.5rem auto;
    }

    .welcome-header {
        font-family: 'Orbitron', monospace; font-size: 1.8rem; font-weight: 700;
        color: #ffd700; text-shadow: 0 0 15px rgba(255,215,0,0.4); margin-bottom: 0.25rem;
    }
    .welcome-sub {
        font-family: 'Rajdhani', sans-serif; font-size: 1rem;
        color: #7878a0; margin-bottom: 1.5rem;
    }
    .quote-box {
        background: linear-gradient(135deg, rgba(255,215,0,0.05), rgba(255,215,0,0.02));
        border-left: 3px solid #ffd700; border-radius: 4px;
        padding: 1rem 1.5rem; margin-bottom: 2rem;
        font-family: 'Rajdhani', sans-serif; font-style: italic; color: #c8c8e0; font-size: 1rem;
    }
    .quote-author { font-size: 0.85rem; color: #ffd700; font-style: normal; margin-top: 0.4rem; }

    .card {
        background: linear-gradient(135deg, #12121e, #0d0d1a);
        border: 1px solid rgba(255,215,0,0.15); border-radius: 10px;
        padding: 1.5rem; height: 100%; transition: border-color 0.3s, box-shadow 0.3s;
    }
    .card:hover { border-color: rgba(255,215,0,0.4); box-shadow: 0 0 20px rgba(255,215,0,0.08); }
    .card-icon { font-size: 2rem; margin-bottom: 0.75rem; }
    .card-title {
        font-family: 'Orbitron', monospace; font-size: 0.85rem; font-weight: 700;
        color: #ffd700; letter-spacing: 0.08em; text-transform: uppercase; margin-bottom: 0.5rem;
    }
    .card-status { font-family: 'Rajdhani', sans-serif; font-size: 1.2rem; color: #e8e8f0; font-weight: 600; }
    .card-badge {
        display: inline-block; background: rgba(255,215,0,0.15); color: #ffd700;
        font-family: 'Rajdhani', sans-serif; font-size: 0.8rem; font-weight: 600;
        padding: 0.25rem 0.6rem; border-radius: 20px; margin-top: 0.5rem;
    }

    .subapp-container {
        display: flex; flex-direction: column; align-items: center;
        justify-content: center; min-height: 65vh; text-align: center;
        padding: 3rem; border-radius: 16px; margin: 1rem 0;
    }
    .subapp-title {
        font-family: 'Orbitron', monospace; font-size: 2rem;
        font-weight: 900; letter-spacing: 0.1em; margin-bottom: 0.75rem;
    }
    .subapp-subtitle { font-family: 'Rajdhani', sans-serif; font-size: 1.1rem; margin-bottom: 2rem; opacity: 0.8; }
    .under-dev-badge {
        font-family: 'Orbitron', monospace; font-size: 0.85rem; font-weight: 700;
        letter-spacing: 0.15em; padding: 0.6rem 1.5rem; border-radius: 4px; border: 2px solid;
    }

    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0d0d1a 0%, #0a0a0f 100%);
        border-right: 1px solid rgba(255,215,0,0.1);
    }
    #MainMenu, footer, header { visibility: hidden; }
    .stDeployButton { display: none; }
</style>
"""

WAYNE_CSS = """
<style>
.wayne-header {
    font-family: 'Orbitron', monospace; font-size: 2.2rem; font-weight: 700;
    color: #4a90d9; text-shadow: 0 0 18px rgba(74,144,217,0.45);
    letter-spacing: 0.15em; margin-bottom: 0.25rem;
}
.wayne-sub {
    font-family: 'Rajdhani', sans-serif; color: #8aabcc; font-size: 1rem;
    letter-spacing: 0.1em; margin-bottom: 1.5rem; text-transform: uppercase;
}
.wayne-divider {
    height: 1px;
    background: linear-gradient(90deg, transparent, rgba(74,144,217,0.4), transparent);
    margin: 1rem 0 1.5rem 0;
}
.kpi-card {
    background: linear-gradient(135deg, rgba(20,30,55,0.85), rgba(10,15,30,0.85));
    border: 1px solid rgba(74,144,217,0.35); border-radius: 10px;
    padding: 1.1rem 1.3rem; box-shadow: inset 0 0 30px rgba(74,144,217,0.08);
}
.kpi-label {
    font-family: 'Rajdhani', sans-serif; font-size: 0.75rem;
    letter-spacing: 0.18em; color: #6e8eaf; text-transform: uppercase; margin-bottom: 0.4rem;
}
.kpi-value { font-family: 'Orbitron', monospace; font-size: 1.6rem; font-weight: 700; color: #e6f0ff; }
.kpi-value.pos { color: #6cd49a; }
.kpi-value.neg { color: #ff7878; }
</style>
"""
