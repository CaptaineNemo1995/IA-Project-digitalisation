#!/bin/sh
set -e

# Clés d'hôte SSH (si absentes)
ssh-keygen -A

# Utilisateur de test créé à partir des variables du .env
id "$SSH_USER" >/dev/null 2>&1 || useradd -m -s /bin/bash "$SSH_USER"
echo "$SSH_USER:$SSH_PASSWORD" | chpasswd

# Journalisation système : sshd -> rsyslog -> /var/log/auth.log
touch /var/log/auth.log
rsyslogd

# L'agent Wazuh surveille /var/log/auth.log (ajouté une seule fois)
if ! grep -q "/var/log/auth.log" /var/ossec/etc/ossec.conf; then
  cat >> /var/ossec/etc/ossec.conf <<'EOF'
<ossec_config>
  <localfile>
    <log_format>syslog</log_format>
    <location>/var/log/auth.log</location>
  </localfile>
</ossec_config>
EOF
fi
/var/ossec/bin/wazuh-control start

# sshd au premier plan (journaux envoyés à rsyslog)
exec /usr/sbin/sshd -D
