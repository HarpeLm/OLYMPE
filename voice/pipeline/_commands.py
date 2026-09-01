"""Mixin commandes du pipeline vocal (routage + handlers)."""
from voice.pipeline._config import *
from router.orchestrator import grounded_web_answer


class CommandsMixin:
    def handle_command(self, text):
        """Route : déterministe (dispatcheur) ou LLM + outils."""
        from integrations._core.confirmation import (
            is_confirmation_pending, handle_response)
        if is_confirmation_pending():
            answer = handle_response(text)
            if answer is not None:
                self.memory.log_turn(self.session_id, text, answer)
                return answer
        result = self.dispatcher.route(text)
        intent = result.get("intent")
        action = result.get("action")
        confidence = result.get("confidence")
        print(
            f"[PIPELINE] Intent={intent} | action={action} | confiance={confidence}"
        )

        if action == "deterministic" and intent == "get_events_today":
            import re as _re
            if "aujourd" not in text.lower():
                m = _re.search(
                    r"(après-demain|demain|lundi|mardi|mercredi|jeudi|vendredi|"
                    r"samedi|dimanche|\d{1,2}/\d{1,2}(?:/\d{4})?)", text, _re.I)
                if m:
                    result["intent"] = "get_events_date"
                    result["slots"] = {"date": m.group(1).lower()}
                    result["handler"] = self.dispatcher.schemas.get(
                        "get_events_date", {}).get("handler")
                    intent = "get_events_date"
                    print(f"[REPAIR] rerouté get_events_date : {result['slots']}")

        if action == "fallback":
            in_cal = intent in FAMILIES.get("calendar", set())
            hinted = calendar_intent_hint(text)
            if in_cal or hinted:
                target = intent if in_cal else hinted
                repaired = repair_calendar_slots(text, result.get("slots"))
                if repaired.get("title") or target != "create_event":
                    result["intent"] = target
                    result["slots"] = repaired
                    result["action"] = "deterministic"
                    result["confidence"] = 0.75
                    result["handler"] = self.dispatcher.schemas.get(target, {}).get("handler")
                    action = "deterministic"
                    intent = target
                    print(f"[REPAIR] intent {target} + slots : {repaired}")

        if action == "deterministic" and intent == "web_search":
            print("[TOOL] web_search (reponse ancree)")
            response = grounded_web_answer(text)
            self.memory.log_turn(self.session_id, text, response)
            return response

        if action == "deterministic" and intent in (
                "delete_file", "empty_trash", "delete_folder", "overwrite_file"):
            from integrations._core.confirmation import request_confirmation
            slots = result.get("slots") or {}
            if intent == "delete_file":
                desc = f"supprimer {slots.get('filename') or 'ce fichier'}"
            elif intent == "delete_folder":
                desc = f"supprimer le dossier {slots.get('filename') or 'ce dossier'}"
            elif intent == "overwrite_file":
                desc = (f"remplacer {slots.get('destination') or 'ce fichier'} "
                        f"par {slots.get('source') or 'un autre'}")
            else:
                desc = "vider la corbeille"
            def _run_confirmed(res):
                """Executor du chemin confirmé : injecte confirmed=True."""
                res = dict(res)
                slots = dict(res.get("slots") or {})
                slots["confirmed"] = True
                res["slots"] = slots
                return self.try_execute_handler(res)

            question = request_confirmation(desc, dict(result), _run_confirmed)
            self.memory.log_turn(self.session_id, text, question)
            return question

        if action == "deterministic":
            response = self.try_execute_handler(result)
            if response is not None:
                self.memory.log_turn(self.session_id, text, response)
                return response
            from router.prefilter import prefilter as _pf
            forced, _ = _pf(text)
            if forced and forced == intent:
                msg = ("Désolé, l'action a échoué ou l'application concernée "
                       "n'est pas disponible.")
                self.memory.log_turn(self.session_id, text, msg)
                return msg
            from router.prefilter import prefilter as _pf
            forced, _ = _pf(text)
            if forced and forced == intent:
                msg = ("Désolé, l'action a échoué ou n'est pas encore "
                       "disponible.")
                self.memory.log_turn(self.session_id, text, msg)
                return msg
            print("[PIPELINE] Handler non implémenté → LLM + outils MCP")
            answer = self.llm_with_tools(text)
            self.memory.log_turn(self.session_id, text, answer)
            return answer

        print("[PIPELINE] Fallback LLM avec outils MCP...")
        answer = self.llm_with_tools(text)
        self.memory.log_turn(self.session_id, text, answer)
        return answer

    def try_execute_handler(self, result):
        """Exécute le handler déterministe s'il existe (intégrations P7)."""
        handler = result.get("handler")
        if not handler or "::" not in handler:
            return None

        path_str, func_name = handler.split("::", 1)
        mod_name = path_str.replace("/", ".").removesuffix(".py")

        try:
            import importlib
            module = importlib.import_module(mod_name)
            func = getattr(module, func_name)
            return str(func(**result.get("slots", {})))
        except Exception as e:
            print(f"[PIPELINE] Handler non exécutable ({handler}) : {e}")
            return None
