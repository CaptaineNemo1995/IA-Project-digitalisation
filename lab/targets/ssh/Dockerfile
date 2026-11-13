FROM debian:trixie-slim

ARG WAZUH_VERSION=4.14.9-1

# SSH + rsyslog (écrit /var/log/auth.log au format syslog, lisible par Wazuh)
RUN apt-get update \
 && apt-get install -y --no-install-recommends openssh-server rsyslog curl gnupg ca-certificates \
 && mkdir -p /run/sshd \
 && sed -i 's/^#\?PasswordAuthentication.*/PasswordAuthentication yes/' /etc/ssh/sshd_config \
 && sed -i '/imklog/s/^/#/' /etc/rsyslog.conf

# Agent Wazuh (même version que le manager), enregistré auprès du manager du labo
RUN curl -s https://packages.wazuh.com/key/GPG-KEY-WAZUH \
      | gpg --no-default-keyring --keyring gnupg-ring:/usr/share/keyrings/wazuh.gpg --import \
 && chmod 644 /usr/share/keyrings/wazuh.gpg \
 && echo "deb [signed-by=/usr/share/keyrings/wazuh.gpg] https://packages.wazuh.com/4.x/apt/ stable main" \
      > /etc/apt/sources.list.d/wazuh.list \
 && apt-get update \
 && WAZUH_MANAGER="172.30.0.50" WAZUH_AGENT_NAME="srv-ssh" \
      apt-get install -y wazuh-agent=${WAZUH_VERSION} \
 && rm -rf /var/lib/apt/lists/*

COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

EXPOSE 22
ENTRYPOINT ["/entrypoint.sh"]
