#!/bin/sh
# pod.sh create <name> | wait <name> <ssh_alias> | list | terminate <id>
# Needs RUNPOD_PERSONAL_API_KEY and RUNPOD_TEMPLATE_ID (the blender-5.0.1 template) in the environment; neither is printed. Writes an ssh config OUTSIDE the project (~/.ssh/<alias>.conf).
API=https://rest.runpod.io/v1; A="Authorization: Bearer $RUNPOD_PERSONAL_API_KEY"
case $1 in
 create) jq -n --arg tpl "$RUNPOD_TEMPLATE_ID" --arg n "$2" --arg pk "$(cat ~/.ssh/id_ed25519.pub)" '{name:$n,templateId:$tpl,cloudType:"SECURE",computeType:"GPU",gpuCount:1,gpuTypeIds:["NVIDIA GeForce RTX 4090","NVIDIA GeForce RTX 5090","NVIDIA L40S","NVIDIA RTX A5000"],gpuTypePriority:"custom",env:{PUBLIC_KEY:$pk}}' \
   | curl -s -X POST -H "$A" -H "Content-Type: application/json" -d @- $API/pods | jq -c '{id,name,costPerHr,gpu:.gpu.gpuTypeId,err:(.error // .message // null)}';;
 wait) for i in $(seq 1 60); do R=$(curl -s -H "$A" $API/pods | jq -c --arg n "$2" '.[]|select(.name==$n)'); IP=$(echo "$R" | jq -r '.publicIp // ""'); PORT=$(echo "$R" | jq -r '.portMappings["22"] // ""'); [ -n "$IP" ] && [ -n "$PORT" ] && break; sleep 8; done
   umask 077; printf 'Host %s\n  HostName %s\n  Port %s\n  User root\n  IdentityFile ~/.ssh/id_ed25519\n  StrictHostKeyChecking accept-new\n  UserKnownHostsFile ~/.ssh/known_hosts_pixanim\n  ServerAliveInterval 30\n  ServerAliveCountMax 10\n' "$3" "$IP" "$PORT" > ~/.ssh/$3.conf
   for i in $(seq 1 30); do ssh -F ~/.ssh/$3.conf -o ConnectTimeout=8 -o BatchMode=yes $3 'nvidia-smi --query-gpu=name --format=csv,noheader' </dev/null 2>/dev/null && break; sleep 8; done;;
 list) curl -s -H "$A" $API/pods | jq -c '[.[]|{name,desiredStatus,costPerHr}]';;
 terminate) curl -s -X DELETE -H "$A" -w "HTTP %{http_code}\n" $API/pods/$2;;
esac
