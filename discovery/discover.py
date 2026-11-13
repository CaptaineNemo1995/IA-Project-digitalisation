#!/usr/bin/env python3
"""
CyberSentinel AI — Étape 1 : découverte et inventaire des actifs.

Lance nmap sur le réseau du labo, analyse le résultat XML et produit :
  output/inventaire.json  -> données structurées (pour le SIEM à l'étape 2)
  output/inventaire.csv   -> une ligne par service (pour Excel / tableur)
  output/inventaire.md    -> tableau lisible (pour la documentation)

Usage (depuis la sandbox) :
  docker compose exec scanner python3 discover.py
  docker compose exec scanner python3 discover.py --subnet 172.30.0.0/24
"""

import argparse
import csv
import json
import subprocess
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

OUTPUT_DIR = Path(__file__).parent / "output"

# Rôles connus du labo (enrichissement de l'inventaire)
KNOWN_ROLES = {
    "172.30.0.1": "Passerelle réseau Docker",
    "172.30.0.100": "Poste d'analyse SOC (scanner)",
}

# Règles simples d'observation de sécurité, par service détecté
RISK_RULES = {
    "ssh": "SSH exposé : surveiller les tentatives de connexion (brute force)",
    "http": "HTTP non chiffré : trafic lisible en clair",
    "redis": "Redis exposé : vérifier l'authentification (souvent ouvert par défaut)",
    "telnet": "Telnet : protocole non chiffré, à désactiver",
    "ftp": "FTP : identifiants transmis en clair",
}


def run_nmap(subnet: str) -> str:
    """Scan des 1000 ports TCP les plus courants + détection de version des services."""
    cmd = ["nmap", "-p-", "-sV", "--version-light", "-T4", "-oX", "-", subnet]
    print(f"[*] Commande : {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    return result.stdout


def parse_nmap_xml(xml_data: str) -> list[dict]:
    """Transforme la sortie XML de nmap en liste d'actifs."""
    root = ET.fromstring(xml_data)
    assets = []

    for host in root.findall("host"):
        if host.find("status").get("state") != "up":
            continue

        ip, mac, vendor = None, None, None
        for addr in host.findall("address"):
            if addr.get("addrtype") == "ipv4":
                ip = addr.get("addr")
            elif addr.get("addrtype") == "mac":
                mac = addr.get("addr")
                vendor = addr.get("vendor")

        hostname_el = host.find("hostnames/hostname")
        hostname = hostname_el.get("name") if hostname_el is not None else None

        services = []
        for port in host.findall("ports/port"):
            if port.find("state").get("state") != "open":
                continue
            svc = port.find("service")
            name = svc.get("name") if svc is not None else "inconnu"
            services.append({
                "port": int(port.get("portid")),
                "protocole": port.get("protocol"),
                "service": name,
                "produit": (svc.get("product") if svc is not None else None),
                "version": (svc.get("version") if svc is not None else None),
                "observation": RISK_RULES.get(name),
            })

        assets.append({
            "ip": ip,
            "hostname": hostname,
            "mac": mac,
            "fabricant": vendor,
            "role": KNOWN_ROLES.get(ip, "Cible du labo"),
            "services": services,
        })

    return sorted(assets, key=lambda a: tuple(int(x) for x in a["ip"].split(".")))


def write_outputs(assets: list[dict], subnet: str, scan_time: str) -> None:
    OUTPUT_DIR.mkdir(exist_ok=True)

    # JSON
    data = {"scan_date": scan_time, "reseau": subnet, "nb_actifs": len(assets), "actifs": assets}
    (OUTPUT_DIR / "inventaire.json").write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

    # CSV : une ligne par service (ou une ligne vide si aucun service)
    with open(OUTPUT_DIR / "inventaire.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(["ip", "hostname", "mac", "role", "port", "protocole", "service", "produit", "version", "observation"])
        for a in assets:
            rows = a["services"] or [None]
            for s in rows:
                w.writerow([a["ip"], a["hostname"], a["mac"], a["role"],
                            *( [s["port"], s["protocole"], s["service"], s["produit"], s["version"], s["observation"]]
                               if s else ["", "", "", "", "", ""] )])

    # Markdown
    lines = [
        "# Inventaire des actifs — CyberSentinel AI",
        "",
        f"- **Date du scan :** {scan_time}",
        f"- **Réseau :** `{subnet}`",
        f"- **Actifs découverts :** {len(assets)}",
        "",
        "## Vue d'ensemble",
        "",
        "| IP | Nom d'hôte | Rôle | Services ouverts |",
        "|---|---|---|---|",
    ]
    for a in assets:
        svcs = ", ".join(f"{s['port']}/{s['service']}" for s in a["services"]) or "aucun"
        lines.append(f"| {a['ip']} | {a['hostname'] or '-'} | {a['role']} | {svcs} |")

    lines += ["", "## Détail des services et observations", "",
              "| IP | Port | Service | Produit / version | Observation |",
              "|---|---|---|---|---|"]
    for a in assets:
        for s in a["services"]:
            prod = " ".join(x for x in (s["produit"], s["version"]) if x) or "-"
            lines.append(f"| {a['ip']} | {s['port']}/{s['protocole']} | {s['service']} | {prod} | {s['observation'] or '-'} |")

    (OUTPUT_DIR / "inventaire.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Découverte et inventaire des actifs du labo")
    parser.add_argument("--subnet", default="172.30.0.0/24", help="Réseau à scanner (par défaut : réseau du labo)")
    args = parser.parse_args()

    scan_time = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    assets = parse_nmap_xml(run_nmap(args.subnet))
    write_outputs(assets, args.subnet, scan_time)

    print(f"[+] {len(assets)} actifs découverts")
    for a in assets:
        svcs = ", ".join(f"{s['port']}/{s['service']}" for s in a["services"]) or "aucun service ouvert"
        print(f"    {a['ip']:<15} {a['role']:<32} {svcs}")
    print(f"[+] Résultats : {OUTPUT_DIR}/inventaire.(json|csv|md)")


if __name__ == "__main__":
    main()