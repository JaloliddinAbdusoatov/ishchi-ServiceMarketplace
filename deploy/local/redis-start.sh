#!/bin/sh
# Generates a restricted ACL inside a NEW dedicated container; no Redis client calls.
set -eu
case "$ISHCHI_REDIS_ROLE" in
  ishchi_local_app) pattern='ishchi:local:work:*'; extra='' ;;
  ishchi_local_test) pattern='ishchi-sprint2-*'; extra='+scan' ;;
  *) echo 'Unexpected local Redis role' >&2; exit 1 ;;
esac
password="$(tr -d '\r\n' < /run/secrets/redis_password)"
test "${#password}" -ge 24
digest="$(printf '%s' "$password" | sha256sum | cut -d ' ' -f 1)"
unset password
printf 'user default off\nuser %s on #%s ~%s resetchannels -@all +ping +hello +select +client|setname +client|setinfo +get +set +del +mget +mset +exists +expire +pexpire +ttl +pttl +incr +incrby +eval +evalsha +script|load +multi +exec +discard %s\n' \
  "$ISHCHI_REDIS_ROLE" "$digest" "$pattern" "$extra" > /tmp/ishchi-users.acl
cat > /tmp/ishchi-redis.conf <<'CONF'
bind 0.0.0.0
port 6379
protected-mode yes
aclfile /tmp/ishchi-users.acl
dir /data
appendonly yes
appendfsync everysec
save 60 1
maxmemory 256mb
maxmemory-policy noeviction
CONF
chmod 644 /tmp/ishchi-users.acl /tmp/ishchi-redis.conf
exec /usr/local/bin/docker-entrypoint.sh redis-server /tmp/ishchi-redis.conf
