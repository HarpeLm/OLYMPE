"""
Diagnostic qualité des échantillons wake word "Olympe"
Vérifie : format, durée, niveau sonore, détection de silence
Usage : python voice/check_wake_samples.py
"""
import wave
import numpy as np
from pathlib import Path

SAMPLE_RATE_EXPECTED = 16000
CHANNELS_EXPECTED = 1
SAMPLE_WIDTH_EXPECTED = 2  # 16-bit
DURATION_EXPECTED = 1.5

POSITIVE_DIR = Path("voice/wake_samples")

def analyze_wav(filepath):
    """Analyse un fichier WAV et retourne les métriques."""
    with wave.open(str(filepath), 'rb') as wf:
        n_channels = wf.getnchannels()
        sample_width = wf.getsampwidth()
        sample_rate = wf.getframerate()
        n_frames = wf.getnframes()
        duration = n_frames / sample_rate
        
        # Lire l'audio
        audio_data = wf.readframes(n_frames)
        audio = np.frombuffer(audio_data, dtype=np.int16).astype(np.float32)
    
    # Métriques audio
    rms = np.sqrt(np.mean(audio ** 2))  # Volume moyen
    peak = np.max(np.abs(audio))  # Volume max
    
    # Détection de silence (RMS très bas)
    is_silent = rms < 100  # Seuil empirique pour 16-bit
    
    # Détection de clipping (saturation)
    clip_ratio = np.mean(np.abs(audio) > 30000) * 100
    
    return {
        "file": filepath.name,
        "sample_rate": sample_rate,
        "channels": n_channels,
        "sample_width": sample_width,
        "duration": duration,
        "rms": rms,
        "peak": peak,
        "is_silent": is_silent,
        "clip_ratio": clip_ratio,
        "format_ok": (
            sample_rate == SAMPLE_RATE_EXPECTED
            and n_channels == CHANNELS_EXPECTED
            and sample_width == SAMPLE_WIDTH_EXPECTED
        )
    }

def main():
    print("=" * 70)
    print("Diagnostic qualité — échantillons wake word 'Olympe'")
    print("=" * 70)
    
    files = sorted(POSITIVE_DIR.glob("olympe_*.wav"))
    if not files:
        print(f"\nERREUR : aucun fichier trouvé dans {POSITIVE_DIR}")
        return
    
    print(f"\n{len(files)} fichiers à analyser\n")
    
    results = []
    for f in files:
        r = analyze_wav(f)
        results.append(r)
    
    # Affichage tableau
    print(f"{'Fichier':<20} {'Format':<6} {'Durée':<7} {'RMS':<8} {'Peak':<7} {'Clip%':<6} {'Statut'}")
    print("-" * 70)
    
    silent_count = 0
    format_issues = 0
    duration_issues = 0
    
    for r in results:
        format_status = "OK" if r["format_ok"] else "ERREUR"
        if not r["format_ok"]:
            format_issues += 1
        
        duration_status = abs(r["duration"] - DURATION_EXPECTED) < 0.1
        if not duration_status:
            duration_issues += 1
        
        if r["is_silent"]:
            status = "SILENCIEUX"
            silent_count += 1
        elif r["rms"] < 300:
            status = "TROP FAIBLE"
        elif r["clip_ratio"] > 5:
            status = "CLIPPING"
        else:
            status = "OK"
        
        print(f"{r['file']:<20} {format_status:<6} {r['duration']:<7.2f} "
              f"{r['rms']:<8.0f} {r['peak']:<7.0f} {r['clip_ratio']:<6.1f} {status}")
    
    # Résumé
    print("\n" + "=" * 70)
    print("Résumé")
    print("=" * 70)
    print(f"Total fichiers         : {len(results)}")
    print(f"Problèmes de format    : {format_issues}")
    print(f"Durées incorrectes     : {duration_issues}")
    print(f"Fichiers silencieux    : {silent_count}")
    
    rms_values = [r["rms"] for r in results if not r["is_silent"]]
    if rms_values:
        print(f"RMS moyen (non-silencieux) : {np.mean(rms_values):.0f}")
        print(f"RMS min (non-silencieux)   : {np.min(rms_values):.0f}")
        print(f"RMS max (non-silencieux)   : {np.max(rms_values):.0f}")
    
    # Verdict
    good_samples = sum(1 for r in results 
                       if r["format_ok"] and not r["is_silent"] and r["rms"] >= 300)
    
    print("\n" + "=" * 70)
    if good_samples >= 10:
        print(f"VERDICT : {good_samples}/{len(results)} échantillons utilisables")
        print("L'entraînement peut être lancé.")
    elif good_samples >= 5:
        print(f"VERDICT : {good_samples}/{len(results)} échantillons utilisables")
        print("C'est limite. Enregistre plus d'échantillons ou recommence les faibles.")
    else:
        print(f"VERDICT : seulement {good_samples}/{len(results)} échantillons utilisables")
        print("TROP PEU. Il faut réenregistrer les échantillons de meilleure qualité.")
    print("=" * 70)

if __name__ == "__main__":
    main()
