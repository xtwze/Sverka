#!/bin/sh
set -eu
# Вызов внутри отдельного Linux-контейнера после initialize.sh.
python3 -c 'import json; r=json.load(open("/var/lib/1c/review-logs/readonly.json", encoding="utf-8-sig")); assert r["status"] == "PASS", r'
mkdir -p /var/www/onec
# webinstt пытается разобрать прежний дескриптор при повторной публикации.
# Здесь это только генерируемый файл; база и логи находятся в отдельном volume.
rm -f /var/www/onec/default.vrd
/opt/1cv8t/x86_64/8.3.27.1508/webinstt -publish -apache24 \
  -wsdir Sverka -dir /var/www/onec \
  -connstr 'File="/var/lib/1c/review";Usr="APIReader";' \
  -confPath /etc/apache2/apache2.conf
cat > /var/www/onec/default.vrd <<'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<point xmlns="http://v8.1c.ru/8.2/virtual-resource-system"
       base="/Sverka" ib="File=&quot;/var/lib/1c/review&quot;;Usr=&quot;APIReader&quot;;" enable="false">
  <ws pointEnableCommon="false"/>
  <httpServices publishByDefault="false" publishExtensionsByDefault="false">
    <service name="ReconciliationAPI" rootUrl="api" enable="true" reuseSessions="dontuse"/>
  </httpServices>
  <pool size="1"/>
  <standardOdata enable="false"/>
  <analytics enable="false"/>
</point>
EOF
# Учебная версия допускает один сеанс; запросы обрабатываются последовательно.
a2dismod mpm_event >/dev/null
a2enmod mpm_prefork >/dev/null
cat > /etc/apache2/conf-available/onec-demo.conf <<'EOF'
ServerName localhost
<IfModule mpm_prefork_module>
  StartServers 1
  MinSpareServers 1
  MaxSpareServers 1
  ServerLimit 1
  MaxRequestWorkers 1
  MaxConnectionsPerChild 0
</IfModule>
EOF
a2enconf onec-demo >/dev/null
chown -R www-data:www-data /var/lib/1c/review
apache2ctl -t
