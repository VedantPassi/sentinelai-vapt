#!/usr/bin/env bash
# SentinelAI — interactive deployment script
# Usage: bash scripts/deploy.sh
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; CYAN='\033[0;36m'; NC='\033[0m'

info()    { echo -e "${CYAN}[INFO]${NC} $*"; }
success() { echo -e "${GREEN}[OK]${NC} $*"; }
warn()    { echo -e "${YELLOW}[WARN]${NC} $*"; }
die()     { echo -e "${RED}[ERROR]${NC} $*" >&2; exit 1; }
ask()     { local _v; read -rp "$(echo -e "${YELLOW}?${NC} $1: ")" _v; echo "$_v"; }
confirm() { local _v; read -rp "$(echo -e "${YELLOW}?${NC} $1 [y/N]: ")" _v; [[ "$_v" =~ ^[Yy]$ ]]; }

# ---- banner ---------------------------------------------------------------
echo -e "${CYAN}"
echo "  ███████╗███████╗███╗   ██╗████████╗██╗███╗   ██╗███████╗██╗      █████╗ ██╗"
echo "  ██╔════╝██╔════╝████╗  ██║╚══██╔══╝██║████╗  ██║██╔════╝██║     ██╔══██╗██║"
echo "  ███████╗█████╗  ██╔██╗ ██║   ██║   ██║██╔██╗ ██║█████╗  ██║     ███████║██║"
echo "  ╚════██║██╔══╝  ██║╚██╗██║   ██║   ██║██║╚██╗██║██╔══╝  ██║     ██╔══██║██║"
echo "  ███████║███████╗██║ ╚████║   ██║   ██║██║ ╚████║███████╗███████╗██║  ██║██║"
echo "  ╚══════╝╚══════╝╚═╝  ╚═══╝   ╚═╝   ╚═╝╚═╝  ╚═══╝╚══════╝╚══════╝╚═╝  ╚═╝╚═╝"
echo -e "${NC}"
echo "  AI-native VAPT Platform — On-Premise Deployment"
echo ""

# ---- check prerequisites --------------------------------------------------
info "Checking prerequisites..."

check_cmd() {
  if command -v "$1" &>/dev/null; then
    success "$1 found ($(command -v "$1"))"
  else
    if [[ "${2:-required}" == "optional" ]]; then
      warn "$1 not found — optional, skipping"
      return 1
    else
      die "$1 is required but not installed. See docs/deployment/on-premise.md"
    fi
  fi
}

check_cmd docker
check_cmd git

# ---- choose deployment path -----------------------------------------------
echo ""
echo "Deployment path:"
echo "  1) Docker Compose (single VM, recommended for < 10 concurrent scans)"
echo "  2) Kubernetes / Helm"
echo ""
DEPLOY_PATH=$(ask "Choose [1/2]")
[[ "$DEPLOY_PATH" =~ ^[12]$ ]] || die "Invalid choice"

if [[ "$DEPLOY_PATH" == "2" ]]; then
  check_cmd kubectl
  check_cmd helm
fi

# ---- environment setup ----------------------------------------------------
echo ""
info "Setting up environment..."

if [[ -f ".env.prod" ]]; then
  warn ".env.prod already exists"
  if ! confirm "Overwrite existing .env.prod?"; then
    info "Using existing .env.prod"
    # shellcheck source=/dev/null
    set -a; source .env.prod; set +a
    SKIP_ENV=1
  fi
fi

if [[ "${SKIP_ENV:-0}" != "1" ]]; then
  [[ -f ".env.prod.example" ]] || die ".env.prod.example not found — run from repo root"
  cp .env.prod.example .env.prod

  echo ""
  info "Generating secrets..."

  # Generate secrets automatically
  JWT_SECRET=$(python3 -c "import secrets; print(secrets.token_hex(32))")
  PG_PASS=$(python3 -c "import secrets; print(secrets.token_urlsafe(24))")
  REDIS_PASS=$(python3 -c "import secrets; print(secrets.token_urlsafe(24))")
  NEO4J_PASS=$(python3 -c "import secrets; print(secrets.token_urlsafe(24))")

  success "Generated: JWT_SECRET_KEY, POSTGRES_PASSWORD, REDIS_PASSWORD, NEO4J_PASSWORD"

  # Collect required values from user
  echo ""
  info "Enter configuration values (leave blank to fill manually in .env.prod later):"
  DOMAIN=$(ask "Domain (e.g. vapt.example.com)")
  ANTHROPIC_KEY=$(ask "Anthropic API key (sk-ant-...)")

  # Patch .env.prod
  sed -i.bak \
    -e "s|POSTGRES_PASSWORD=CHANGE_ME_strong_password_here|POSTGRES_PASSWORD=${PG_PASS}|" \
    -e "s|REDIS_PASSWORD=CHANGE_ME_redis_password_here|REDIS_PASSWORD=${REDIS_PASS}|" \
    -e "s|NEO4J_PASSWORD=CHANGE_ME_neo4j_password_here|NEO4J_PASSWORD=${NEO4J_PASS}|" \
    -e "s|JWT_SECRET_KEY=CHANGE_ME_generate_64_char_hex|JWT_SECRET_KEY=${JWT_SECRET}|" \
    .env.prod

  if [[ -n "$DOMAIN" ]]; then
    sed -i.bak \
      -e "s|DOMAIN=yourdomain.com|DOMAIN=${DOMAIN}|" \
      -e "s|NEXT_PUBLIC_API_URL=https://yourdomain.com|NEXT_PUBLIC_API_URL=https://${DOMAIN}|" \
      -e "s|TLS_CERT_DIR=/etc/letsencrypt/live/yourdomain.com|TLS_CERT_DIR=/etc/letsencrypt/live/${DOMAIN}|" \
      -e "s|OIDC_REDIRECT_URI=https://yourdomain.com|OIDC_REDIRECT_URI=https://${DOMAIN}|" \
      .env.prod
  fi

  if [[ -n "$ANTHROPIC_KEY" ]]; then
    sed -i.bak "s|ANTHROPIC_API_KEY=sk-ant-CHANGE_ME|ANTHROPIC_API_KEY=${ANTHROPIC_KEY}|" .env.prod
    sed -i.bak "s|LLM_PROVIDER=ollama|LLM_PROVIDER=anthropic|" .env.prod
  fi

  rm -f .env.prod.bak
  chmod 600 .env.prod
  success ".env.prod created (chmod 600)"

  # shellcheck source=/dev/null
  set -a; source .env.prod; set +a
fi

# ---- build images ---------------------------------------------------------
echo ""
info "Building Docker images..."

NEXT_PUBLIC_API_URL="${NEXT_PUBLIC_API_URL:-https://${DOMAIN:-localhost}}"

docker build -t sentinelai/backend:latest ./backend
success "sentinelai/backend:latest built"

docker build -t sentinelai/frontend:latest \
  --build-arg NEXT_PUBLIC_API_URL="$NEXT_PUBLIC_API_URL" \
  ./frontend
success "sentinelai/frontend:latest built"

# ---- deploy ---------------------------------------------------------------
if [[ "$DEPLOY_PATH" == "1" ]]; then
  echo ""
  info "Starting Docker Compose stack..."

  COMPOSE_FILE="infra/docker/docker-compose.prod.yml"

  # Start infra first, wait for postgres health
  docker compose -f "$COMPOSE_FILE" --env-file .env.prod up -d postgres redis neo4j
  info "Waiting for postgres to be healthy..."
  until docker compose -f "$COMPOSE_FILE" --env-file .env.prod exec postgres \
    pg_isready -U "${POSTGRES_USER:-sentinel}" -d "${POSTGRES_DB:-sentinelai}" &>/dev/null; do
    sleep 2
  done
  success "Postgres healthy"

  # Run migrations
  info "Running database migrations..."
  docker run --rm \
    --env-file .env.prod \
    --network "$(docker network ls --filter name=sentinelai --format '{{.Name}}' | head -1)" \
    sentinelai/backend:latest \
    alembic upgrade head
  success "Migrations complete"

  # Start remaining services
  docker compose -f "$COMPOSE_FILE" --env-file .env.prod up -d
  success "All services started"

  echo ""
  echo -e "${GREEN}============================================================${NC}"
  echo -e "${GREEN}  SentinelAI is running!${NC}"
  echo -e "${GREEN}============================================================${NC}"
  echo ""
  echo "  URL:    https://${DOMAIN:-localhost}"
  echo "  Health: https://${DOMAIN:-localhost}/health"
  echo ""
  echo "  Register your admin account:"
  echo "  curl -X POST https://${DOMAIN:-localhost}/auth/register \\"
  echo '    -H "Content-Type: application/json" \'
  echo '    -d '"'"'{"email":"admin@example.com","password":"YourPass","org_name":"My Org"}'"'"
  echo ""

else
  # ---- Kubernetes -----------------------------------------------------------
  NAMESPACE="sentinelai"
  HELM_CHART="infra/helm/sentinelai"

  echo ""
  info "Deploying to Kubernetes (namespace: ${NAMESPACE})..."

  kubectl create namespace "$NAMESPACE" --dry-run=client -o yaml | kubectl apply -f -

  # Build values override from .env.prod
  VALUES_OVERRIDE=$(mktemp /tmp/sentinelai-values-XXXXXX.yaml)
  trap "rm -f $VALUES_OVERRIDE" EXIT

  cat > "$VALUES_OVERRIDE" <<EOF
ingress:
  host: "${DOMAIN:-sentinelai.example.com}"
secrets:
  postgresPassword: "${POSTGRES_PASSWORD}"
  redisPassword: "${REDIS_PASSWORD}"
  neo4jPassword: "${NEO4J_PASSWORD}"
  jwtSecretKey: "${JWT_SECRET_KEY}"
  anthropicApiKey: "${ANTHROPIC_API_KEY:-}"
  bloodhoundSecret: "${BLOODHOUND_SECRET:-}"
  awsAccessKeyId: "${AWS_ACCESS_KEY_ID:-}"
  awsSecretAccessKey: "${AWS_SECRET_ACCESS_KEY:-}"
  oidcClientSecret: "${OIDC_CLIENT_SECRET:-}"
config:
  oidcEnabled: "${OIDC_ENABLED:-false}"
  oidcClientId: "${OIDC_CLIENT_ID:-}"
EOF

  if helm status sentinelai -n "$NAMESPACE" &>/dev/null; then
    info "Upgrading existing release..."
    helm upgrade sentinelai "$HELM_CHART" \
      -n "$NAMESPACE" \
      -f "$VALUES_OVERRIDE" \
      --wait --timeout 10m
  else
    info "Installing new release..."
    helm install sentinelai "$HELM_CHART" \
      -n "$NAMESPACE" \
      -f "$VALUES_OVERRIDE" \
      --wait --timeout 10m
  fi

  success "Helm release deployed"

  echo ""
  echo -e "${GREEN}============================================================${NC}"
  echo -e "${GREEN}  SentinelAI is running on Kubernetes!${NC}"
  echo -e "${GREEN}============================================================${NC}"
  echo ""
  echo "  Pods:"
  kubectl get pods -n "$NAMESPACE"
  echo ""
  echo "  URL: https://${DOMAIN:-sentinelai.example.com}"
  echo ""
fi

info "Done. See docs/deployment/on-premise.md for upgrade and backup instructions."
