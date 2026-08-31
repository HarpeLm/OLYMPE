"""
Pré-filtre règles/regex (~0 ms) — roadmap §4 [1]
Court-circuite le dispatcheur pour les motifs évidents.
"""
import re

RULES = [
    # Heure/date → fallback (aucun intent dédié ; le LLM + outil MCP répond)
    (r"\b(heure|quel jour|quelle date|on est le|quelle heure)\b", "fallback", "time_date"),
    # Météo → get_weather forcé (l'intent existe, le modèle se trompe)
    (r"\b(météo|temps fait-il|pleut|neige|température)\b", "get_weather", "weather"),
    # Minuteur/timer → fallback (aucun intent dédié)
    (r"\b(minuteur|timer|compte à rebours|alarme dans)\b", "fallback", "timer"),
    # Fichiers : motifs évidents forcés en déterministe
    (r"\b(ouvre|ouvrir)\b.{0,40}\b(dossier|téléchargements|telechargements|bureau|documents|downloads|desktop|images|musique|vidéos)\b", "open_folder", "files_open"),
    (r"\b(cherche|trouve|recherche)\b.{0,40}\b(fichier|fichiers|pdf|word|excel|image|images|document)\b", "find_file", "files_find"),
    (r"\bfichiers?\b.{0,40}\b(modifiés|modifiées|recemment|récemment|recents|récents)\b", "list_recent_files", "files_recent"),
    (r"\b(vide|vider)\b.{0,20}\bcorbeille\b", "empty_trash", "files_trash"),
    (r"\b(supprime|supprimer|efface|effacer)\b.{0,40}\bdossiers?\b", "delete_folder", "files_deletefolder"),
    (r"\b(supprime|supprimer|efface|effacer)\b", "delete_file", "files_delete"),
    (r"\b(où est|ou est|où se trouve|montre|affiche|repère)\b", "locate_file", "files_locate"),
    (r"\bdans le finder\b", "locate_file", "files_locate"),
    (r"\b(ouvre|ouvrir)\b.{0,40}\.[a-z0-9]{2,5}\b", "open_file", "files_openfile"),
    (r"\b(ouvre|ouvrir|lance|lancer)\b", "open_app", "app_open"),
    (r"\b(ferme|fermer)\b.{0,40}\.[a-z0-9]{2,5}\b", "close_file", "files_closefile"),
    (r"\b(ferme|fermer|quitte|quitter)\b", "close_app", "app_close"),
    (r"\b(renomme|renommer)\b.{0,60}\ben\b", "rename_file", "files_rename"),
    (r"\b(copie|copier)\b.{0,60}\bvers\b", "copy_file", "files_copy"),
    (r"\b(duplique|dupliquer)\b", "duplicate_file", "files_dup"),
    (r"\b(zippe|zipper|compresse|compresser)\b", "compress_file", "files_zip"),
    (r"\b(décompresse|décompresser|extrais|extraire)\b", "extract_archive", "files_unzip"),
    (r"\b(tague|taguer)\b", "add_tag", "files_tag"),
    (r"\ben\s+favoris\b", "set_favorite", "files_fav"),
    (r"\b(écrase|écraser|remplace|remplacer)\b.{0,60}\b(par|avec|sur)\b", "overwrite_file", "files_overwrite"),
    (r"\bexiste\b", "check_file_exists", "files_exists"),
    (r"\b(infos?|informations?|taille)\b.{0,40}\b(de|sur|du|des|de la)\b", "get_file_info", "files_info"),
]

