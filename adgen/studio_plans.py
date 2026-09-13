"""Versioned limits; existing paid plans keep their original quotas."""
STUDIO_PLANS = {
    "adgen-studio-essentiel": dict(name="AdGen Studio Essentiel", price=3000, eur="5.00", level="starter", text=20, video=5, voice=3000, music=5),
    "adgen-studio-createur": dict(name="AdGen Studio Créateur", price=10000, eur="16.00", level="pro", text=100, video=25, voice=15000, music=25),
    "adgen-studio-business": dict(name="AdGen Studio Business", price=25000, eur="40.00", level="enterprise", text=300, video=80, voice=45000, music=80),
}
LEGACY_LIMITS = {
    "adgen-starter": dict(text=30, video=10, voice=3000, music=10),
    "adgen-pro": dict(text=150, video=50, voice=15000, music=50),
    "adgen-business": dict(text=500, video=150, voice=45000, music=150),
}
RESOURCE_LABELS = {"text": "lots de textes", "video": "montages vidéo", "voice": "caractères de voix-off", "music": "ambiances sonores"}
