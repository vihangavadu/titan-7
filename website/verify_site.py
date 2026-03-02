#!/usr/bin/env python3
import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('187.77.186.252', username='root', password='Chilaw@123@llm', timeout=15)

cmds = [
    'curl -sk -o /dev/null -w "index: %{http_code}" https://titanxanti.site/',
    'curl -sk -o /dev/null -w "shareholder: %{http_code}" https://titanxanti.site/shareholder-agreement.html',
    'curl -sk -o /dev/null -w "payment: %{http_code}" https://titanxanti.site/payment.html',
    'ls /var/www/titanxanti.site/',
    'systemctl is-active nginx',
]

for cmd in cmds:
    _, out, _ = ssh.exec_command(cmd)
    print(out.read().decode().strip())

ssh.close()
