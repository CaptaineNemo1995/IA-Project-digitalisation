#!/usr/bin/env python3
"""
CyberSentinel AI — Étape 4 : serveur MCP « wazuh » (LECTURE SEULE)

Expose à l'agent IA (Goose) quelques outils pour CONSULTER les alertes Wazuh
et l'inventaire des actifs. Aucun outil ne modifie quoi que ce soit, aucun
n'exécute de commande : c'est la règle « pas d'exécution arbitraire » du projet.

Protocole : MCP (Model Context Protocol) sur stdio — messages JSON-RPC 2.0,
un message JSON par ligne. Uniquement la bibliothèque standard Python.

Configuration : lue dans le fichier .env à la racine du dépôt
  SIEM_ADMIN_USER / SIEM_ADMIN_PASSWORD  -> identifiants de l'indexeur Wazuh
  WAZUH_INDEXER_URL (optionnel)          -> défaut https://localhost:9200
"""

import base64
import json
import os
import ssl
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CA_FILE = ROOT / "lab/siem/wazuh-docker/single-node/config/wazuh_indexer_ssl_certs/root-ca.pem"
INVENTORY_FILE = ROOT / "discovery/output/inventaire.json"
ALERTS_INDEX = "wazuh-alerts-4.x-*"
MAX_RESULTS = 10


# ---------------------------------------------------------------- configuration

def load_env(path: Path) -> dict:
    env = {}
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                env[k.strip()] = v.strip().strip('"').strip("'")
    return env


ENV = {**load_env(ROOT / ".env"), **os.environ}
INDEXER_URL = ENV.get("WAZUH_INDEXER_URL", "https://localhost:9200").rstrip("/")
INDEXER_USER = ENV.get("SIEM_ADMIN_USER", "admin")
INDEXER_PASSWORD = ENV.get("SIEM_ADMIN_PASSWORD", "")


def ssl_context() -> ssl.SSLContext:
    # On vérifie le certificat avec NOTRE autorité (root-ca.pem générée à l'étape 2).
    # Le nom d'hôte n'est pas vérifié car le certificat est émis pour « wazuh.indexer »
    # et on s'y connecte via localhost.
    ctx = ssl.create_default_context(cafile=str(CA_FILE)) if CA_FILE.exists() else ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_flags &= ~ssl.VERIFY_X509_STRICT  # CA Wazuh sans extension keyUsage (Python >= 3.13)
    if not CA_FILE.exists():
        ctx.verify_mode = ssl.CERT_NONE
    return ctx


SSL_CTX = ssl_context()


def indexer_search(body: dict) -> dict:
    """Requête de RECHERCHE uniquement (_search) sur l'index des alertes."""
    url = f"{INDEXER_URL}/{ALERTS_INDEX}/_search"
    token = base64.b64encode(f"{INDEXER_USER}:{INDEXER_PASSWORD}".encode()).decode()
    req = urllib.request.Request(
        url, data=json.dumps(body).encode(), method="POST",
        headers={"Content-Type": "application/json", "Authorization": f"Basic {token}"},
    )
    with urllib.request.urlopen(req, context=SSL_CTX, timeout=20) as resp:
        return json.loads(resp.read())


# ---------------------------------------------------------------- outils

def _time_filter(heures: int) -> dict:
    heures = max(1, min(int(heures), 24 * 30))
    return {"range": {"timestamp": {"gte": f"now-{heures}h"}}}


def _compact(hit: dict) -> dict:
    s = hit.get("_source", {})
    rule, data = s.get("rule", {}), s.get("data", {})
    return {
        "date": s.get("timestamp"),
        "agent": s.get("agent", {}).get("name"),
        "regle_id": rule.get("id"),
        "niveau": rule.get("level"),
        "description": rule.get("description"),
        "groupes": None,
        "mitre": rule.get("mitre", {}).get("technique"),
        "ip_source": data.get("srcip"),
        "utilisateur": data.get("srcuser") or data.get("dstuser"),
        "log": (s.get("full_log") or "")[:150],
    }


def tool_resume_alertes(heures: int = 24, niveau_min: int = 3) -> dict:
    body = {
        "size": 0,
        "query": {"bool": {"filter": [_time_filter(heures), {"range": {"rule.level": {"gte": int(niveau_min)}}}]}},
        "aggs": {
            "par_regle": {
                "terms": {"field": "rule.description", "size": 15},
                "aggs": {"niveau_max": {"max": {"field": "rule.level"}}},
            },
            "par_ip_source": {"terms": {"field": "data.srcip", "size": 10}},
            "par_agent": {"terms": {"field": "agent.name", "size": 10}},
        },
    }
    r = indexer_search(body)
    a = r.get("aggregations", {})
    return {
        "periode_heures": heures,
        "niveau_min": niveau_min,
        "total_alertes": r.get("hits", {}).get("total", {}).get("value"),
        "par_regle": [{"description": b["key"], "nombre": b["doc_count"],
                       "niveau_max": b["niveau_max"]["value"]} for b in a.get("par_regle", {}).get("buckets", [])],
        "par_ip_source": [{"ip": b["key"], "nombre": b["doc_count"]} for b in a.get("par_ip_source", {}).get("buckets", [])],
        "par_agent": [{"agent": b["key"], "nombre": b["doc_count"]} for b in a.get("par_agent", {}).get("buckets", [])],
    }


def tool_rechercher_alertes(heures: int = 24, niveau_min: int = 0, agent: str = "",
                            ip_source: str = "", groupe: str = "", limite: int = 20) -> dict:
    filters = [_time_filter(heures), {"range": {"rule.level": {"gte": int(niveau_min)}}}]
    if agent:
        filters.append({"term": {"agent.name": agent}})
    if ip_source:
        filters.append({"term": {"data.srcip": ip_source}})
    if groupe:
        filters.append({"term": {"rule.groups": groupe}})
    body = {
        "size": max(1, min(int(limite), MAX_RESULTS)),
        "sort": [{"timestamp": "desc"}],
        "query": {"bool": {"filter": filters}},
    }
    r = indexer_search(body)
    hits = r.get("hits", {})
    return {"total": hits.get("total", {}).get("value"), "alertes": [_compact(h) for h in hits.get("hits", [])]}


def tool_activite_ip(ip: str, heures: int = 24) -> dict:
    body = {
        "size": 0,
        "query": {"bool": {"filter": [_time_filter(heures), {"term": {"data.srcip": ip}}]}},
        "aggs": {
            "premiere": {"min": {"field": "timestamp"}},
            "derniere": {"max": {"field": "timestamp"}},
            "regles": {"terms": {"field": "rule.description", "size": 10}},
            "utilisateurs": {"terms": {"field": "data.srcuser", "size": 20}},
            "cibles": {"terms": {"field": "agent.name", "size": 10}},
            "mitre": {"terms": {"field": "rule.mitre.technique", "size": 10}},
        },
    }
    r = indexer_search(body)
    a = r.get("aggregations", {})
    keys = lambda name: [b["key"] for b in a.get(name, {}).get("buckets", [])]
    return {
        "ip": ip,
        "nombre_evenements": r.get("hits", {}).get("total", {}).get("value"),
        "premiere_activite": a.get("premiere", {}).get("value_as_string"),
        "derniere_activite": a.get("derniere", {}).get("value_as_string"),
        "regles_declenchees": keys("regles"),
        "utilisateurs_tentes": keys("utilisateurs"),
        "machines_ciblees": keys("cibles"),
        "techniques_mitre": keys("mitre"),
    }


def tool_inventaire_actifs() -> dict:
    if not INVENTORY_FILE.exists():
        return {"erreur": "Inventaire absent. Lancer d'abord : docker compose exec scanner python3 discover.py"}
    return json.loads(INVENTORY_FILE.read_text(encoding="utf-8"))


TOOLS = {
    "resume_alertes": {
        "fn": tool_resume_alertes,
        "description": "Résumé des alertes Wazuh sur une période : nombre total, regroupement par règle, par IP source et par machine.",
        "schema": {"type": "object", "properties": {
            "heures": {"type": "integer", "description": "Période en heures (défaut 24)"},
            "niveau_min": {"type": "integer", "description": "Niveau de gravité minimum 0-15 (défaut 3)"}}},
    },
    "rechercher_alertes": {
        "fn": tool_rechercher_alertes,
        "description": "Liste les alertes Wazuh les plus récentes, avec filtres optionnels (machine, IP source, groupe de règles comme 'authentication_failed' ou 'sshd').",
        "schema": {"type": "object", "properties": {
            "heures": {"type": "integer"}, "niveau_min": {"type": "integer"},
            "agent": {"type": "string", "description": "Nom de la machine, ex : srv-ssh"},
            "ip_source": {"type": "string", "description": "IP de l'attaquant présumé"},
            "groupe": {"type": "string", "description": "Groupe de règles Wazuh"},
            "limite": {"type": "integer", "description": "Nombre max de résultats (max 100)"}}},
    },
    "activite_ip": {
        "fn": tool_activite_ip,
        "description": "Profil d'une IP source : volume d'événements, première et dernière activité, règles déclenchées, utilisateurs tentés, machines ciblées, techniques MITRE ATT&CK.",
        "schema": {"type": "object", "required": ["ip"], "properties": {
            "ip": {"type": "string"}, "heures": {"type": "integer"}}},
    },
    "inventaire_actifs": {
        "fn": tool_inventaire_actifs,
        "description": "Inventaire des actifs du labo (étape 1) : IP, nom, rôle, services ouverts et observations de sécurité.",
        "schema": {"type": "object", "properties": {}},
    },
}


# ---------------------------------------------------------------- protocole MCP

def reply(msg_id, result=None, error=None):
    msg = {"jsonrpc": "2.0", "id": msg_id}
    msg["error" if error else "result"] = error or result
    sys.stdout.write(json.dumps(msg, ensure_ascii=False) + "\n")
    sys.stdout.flush()


def handle(msg: dict):
    method, msg_id, params = msg.get("method"), msg.get("id"), msg.get("params") or {}

    if msg_id is None:            # notification (ex : notifications/initialized) : pas de réponse
        return

    if method == "initialize":
        reply(msg_id, {
            "protocolVersion": params.get("protocolVersion", "2025-06-18"),
            "capabilities": {"tools": {}},
            "serverInfo": {"name": "cybersentinel-wazuh", "version": "1.0.0"},
            "instructions": "Outils en lecture seule sur les alertes Wazuh et l'inventaire du labo CyberSentinel.",
        })
    elif method == "ping":
        reply(msg_id, {})
    elif method == "tools/list":
        reply(msg_id, {"tools": [
            {"name": n, "description": t["description"], "inputSchema": t["schema"],
             "annotations": {"readOnlyHint": True}}
            for n, t in TOOLS.items()]})
    elif method == "tools/call":
        name, args = params.get("name"), params.get("arguments") or {}
        tool = TOOLS.get(name)
        if not tool:
            reply(msg_id, error={"code": -32602, "message": f"Outil inconnu : {name}"})
            return
        try:
            result = tool["fn"](**args)
            reply(msg_id, {"content": [{"type": "text", "text": json.dumps(result, ensure_ascii=False, indent=2)}]})
        except urllib.error.HTTPError as e:
            reply(msg_id, {"isError": True, "content": [{"type": "text", "text": f"Erreur indexeur HTTP {e.code} : {e.read()[:150]!r}"}]})
        except Exception as e:
            reply(msg_id, {"isError": True, "content": [{"type": "text", "text": f"Erreur : {type(e).__name__} : {e}"}]})
    else:
        reply(msg_id, error={"code": -32601, "message": f"Méthode non supportée : {method}"})


def main():
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            handle(json.loads(line))
        except json.JSONDecodeError:
            reply(None, error={"code": -32700, "message": "JSON invalide"})


if __name__ == "__main__":
    main()
