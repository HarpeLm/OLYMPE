"""
Mémoire persistante MJ — SQLite (roadmap §8, Palier 6)

Deux tables :
  facts : faits explicites (préférences, infos perso), gardés indéfiniment
  turns : historique conversationnel, purgé après 7 jours

Zéro dépendance externe (sqlite3 = stdlib). La DB vit sur disque :
elle survit aux redémarrages du pipeline et résout le stateless du
serveur MCP (spawné par appel).
"""
import sqlite3
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "data" / "memory" / "olympe.db"


class Memory:
    def __init__(self, db_path=DB_PATH):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(self.db_path))
        self._init_schema()

    def _init_schema(self):
        self.conn.executescript("""
            CREATE TABLE IF NOT EXISTS facts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ts INTEGER NOT NULL,
                category TEXT NOT NULL DEFAULT 'general',
                content TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS turns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                ts INTEGER NOT NULL,
                user_text TEXT NOT NULL,
                assistant_text TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_facts_ts ON facts(ts);
            CREATE INDEX IF NOT EXISTS idx_turns_ts ON turns(ts);
        """)
        self.conn.commit()

    def remember(self, content, category="general"):
        cur = self.conn.execute(
            "INSERT INTO facts (ts, category, content) VALUES (?, ?, ?)",
            (int(time.time()), category, content),
        )
        self.conn.commit()
        return cur.lastrowid

    def recall(self, query=None, category=None, limit=5):
        sql = "SELECT id, ts, category, content FROM facts WHERE 1=1"
        params = []
        if category:
            sql += " AND category = ?"
            params.append(category)
        if query:
            sql += " AND content LIKE ?"
            params.append(f"%{query}%")
        sql += " ORDER BY ts DESC LIMIT ?"
        params.append(limit)
        rows = self.conn.execute(sql, params).fetchall()
        return [{"id": r[0], "ts": r[1], "category": r[2], "content": r[3]}
                for r in rows]

    def forget(self, fact_id):
        self.conn.execute("DELETE FROM facts WHERE id = ?", (fact_id,))
        self.conn.commit()

    def log_turn(self, session_id, user_text, assistant_text):
        self.conn.execute(
            "INSERT INTO turns (session_id, ts, user_text, assistant_text) "
            "VALUES (?, ?, ?, ?)",
            (session_id, int(time.time()), user_text, assistant_text),
        )
        self.conn.commit()

    def recent_turns(self, limit=3, max_age_days=7):
        cutoff = int(time.time()) - max_age_days * 86400
        rows = self.conn.execute(
            "SELECT ts, user_text, assistant_text FROM turns "
            "WHERE ts >= ? ORDER BY ts DESC LIMIT ?",
            (cutoff, limit),
        ).fetchall()
        return [{"ts": r[0], "user": r[1], "assistant": r[2]}
                for r in reversed(rows)]

    def purge_old_turns(self, max_age_days=7):
        cutoff = int(time.time()) - max_age_days * 86400
        self.conn.execute("DELETE FROM turns WHERE ts < ?", (cutoff,))
        self.conn.commit()

    def context_prompt(self, limit_facts=5, limit_turns=3):
        """Bloc mémoire à injecter dans le system prompt du 8B."""
        facts = self.recall(limit=limit_facts)
        turns = self.recent_turns(limit=limit_turns)
        if not facts and not turns:
            return ""
        lines = ["MÉMOIRE MJ :"]
        if facts:
            lines.append("Faits connus sur l'UTILISATEUR (ces faits parlent de lui, pas de toi) :")
            lines += [f"- [{f['category']}] l'utilisateur a dit : « {f['content']} »" for f in facts]
        if turns:
            lines.append("Derniers échanges :")
            lines += [f"- L'utilisateur a dit : {t['user']} / MJ a répondu : {t['assistant']}" for t in turns]
        return "\n".join(lines)

    def close(self):
        self.conn.close()
