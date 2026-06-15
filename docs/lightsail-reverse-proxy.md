# Lightsail Reverse Proxy (Caddy)

> Lightsail Instance 단독 구조에서 HTTPS 종단을 처리하기 위한 **중앙화된 Caddy 사이드카** 설계.

## 동기

Lightsail Instance 는 ACM 인증서를 직접 부착할 수 없다 (ACM Public 인증서는 export 불가). HTTPS 가 필요한 프로젝트는 다음 중 하나가 필요:

1. Lightsail Load Balancer ($18/월) + ACM
2. Cloudflare 프록시 (외부 의존)
3. 인스턴스 안에서 Let's Encrypt 인증서 직접 운영

본 hub 는 옵션 3 을 **`reverse_proxy` 옵셔널 변수** 로 중앙화한다. 프로젝트 yml 에 변수 한 블록만 선언하면 Caddy 사이드카 + Let's Encrypt 인증서 + HTTPS 종단까지 자동 구성된다. 변수가 없으면 기존 host_port 직접 노출 동작 그대로.

## 설계

```
[Lightsail Instance]
  ├─ caddy (호스트당 1개, 80/443 점유)
  │   ├─ /etc/caddy/Caddyfile          (메인 — sites.d/*.caddy import)
  │   └─ /etc/caddy/sites.d/
  │       ├─ miner.caddy                (프로젝트별 site snippet)
  │       └─ (다른 프로젝트.caddy)
  │
  ├─ proxy_net (docker bridge network)
  │
  └─ miner 컨테이너 (expose 8080, proxy_net 참여)
```

핵심 원칙:

- **Caddy 는 인스턴스 단위 자원**. 첫 프로젝트가 부트스트랩, 이후 프로젝트는 site snippet 만 추가.
- **공유 docker network** (`proxy_net`) 가 Caddy ↔ 프로젝트 컨테이너 통신을 담당. 프로젝트 컨테이너는 host port 노출 X.
- **인증서 발급·갱신은 Caddy 자체** (ACME HTTP-01). certbot 설치 불필요. 60일마다 자동 갱신.
- **idempotent 부트스트랩** — 매 배포마다 Caddy 컨테이너 존재 확인, 없으면 생성. 있으면 skip.
- **Caddy 영속 볼륨** (`caddy_data`, `caddy_config`) — 인증서·ACME 계정 키 보존.

## projects/{project}.yml 스키마

```yaml
lightsail:
  instance_name: miner
  container_name: miner
  host_port: 8080            # reverse_proxy 모드에서는 docker network 안 통신용
  container_port: 8080
  health_check:
    path: /health
    interval: 10
    timeout: 5
    retries: 3
  env:
    SPRING_PROFILES_ACTIVE: production

  # optional — 있으면 Caddy 사이드카 자동 부트스트랩 + Let's Encrypt 인증서 자동 발급/갱신
  reverse_proxy:
    enabled: true
    domain: miner.ravit.run
    tls:
      provider: letsencrypt
      email: devravit@gmail.com
```

| 필드 | 필수 | 의미 |
|------|------|------|
| `reverse_proxy.enabled` | true 면 활성 | false / 미선언 시 기존 host_port 직접 노출 동작 |
| `reverse_proxy.domain` | enabled=true 면 필수 | Caddy 가 listen 할 호스트명 (DNS 사전 설정 필수) |
| `reverse_proxy.tls.provider` | enabled=true 면 필수 | 현재 `letsencrypt` 만 |
| `reverse_proxy.tls.email` | enabled=true 면 필수 | ACME 계정 + 만료 알림 수신 메일 |

## 배포 흐름 (lightsail.yml 워크플로우)

`reverse_proxy.enabled: true` 일 때:

1. **Caddy 부트스트랩 step**
   - `/etc/caddy/sites.d/` 디렉토리 생성
   - `/etc/caddy/Caddyfile` 메인 설정 생성 (없을 때만 — email + import)
   - `proxy_net` docker network 생성 (idempotent)
   - Caddy 컨테이너 생성 (이미 있으면 skip)
   - `/etc/caddy/sites.d/{project}.caddy` snippet 작성 (덮어쓰기)
   - Lightsail firewall 443 OPEN (idempotent)
2. **컨테이너 배포 step**
   - 기존 컨테이너 stop/rm
   - 새 컨테이너 `--network proxy_net --expose ${CONTAINER_PORT}` 로 실행 (host port 노출 없음)
   - Caddy reload (snippet 변경 반영)
3. **Health check step**
   - reverse_proxy 모드: 컨테이너 내부에서 `wget http://localhost:${CONTAINER_PORT}${HEALTH_PATH}` 폴링
   - 기본 모드: 인스턴스 localhost:${HOST_PORT} 폴링

`reverse_proxy.enabled: false` (또는 미선언):
- Caddy 부트스트랩 step skip
- 기존 동작 그대로 (`-p HOST_PORT:CONTAINER_PORT`)

## 사전 조건 (프로젝트 진입 전)

| 항목 | 확인 방법 |
|------|----------|
| DNS A 레코드 → Lightsail 인스턴스 IP | `dig +short {domain} A` |
| 인스턴스 80 OPEN (Let's Encrypt HTTP-01 challenge) | Lightsail 콘솔 / `aws lightsail get-instance --query 'instance.networking.ports'` |
| 인스턴스에 docker + AWS CLI 설치 | 기존 lightsail 사전 셋업 동일 |
| 인스턴스가 ECR pull 권한 보유 | `/home/ubuntu/.aws/credentials` 의 IAM key |

DNS 가 인스턴스 IP 를 가리키지 않으면 Let's Encrypt HTTP-01 challenge 실패 → 인증서 발급 안 됨. 첫 배포 전에 DNS 부터.

## 운영

### 인증서 갱신
- Caddy 가 만료 30일 전부터 자동 갱신
- 갱신 실패시 `reverse_proxy.tls.email` 로 알림 (Let's Encrypt 발송)
- 수동 확인: `docker exec caddy caddy list-certificates`

### Caddyfile snippet 수정
- 프로젝트 yml 의 `domain` 변경 후 재배포 → snippet 갱신 + Caddy reload
- 메인 Caddyfile (`/etc/caddy/Caddyfile`) 은 첫 부트스트랩 시점 한 번만 생성됨 — email 변경 등은 수동 + Caddy 재시작 필요 (개선 여지)

### 다중 프로젝트 attach
- 같은 인스턴스에 다른 프로젝트도 attach 하려면 같은 lightsail.yml 흐름 그대로
- 두 번째 프로젝트의 `reverse_proxy.domain` 만 다르게 → Caddy 가 호스트 기반 라우팅
- 단, 두 프로젝트가 같은 컨테이너 이름 사용 금지

### Caddy 자원 사용 (참고)
- 메모리: ~25 MB (alpine 이미지 기준)
- CPU: idle 거의 0
- TLS handshake 분당 0~수 회 수준

### 트러블슈팅
- 인증서 발급 실패: `docker logs caddy` 에서 ACME 에러 확인 → DNS / 80 firewall / rate limit 점검
- 503 응답: Caddy 는 살아있고 backend 컨테이너 다운 → `docker ps`, `docker logs ${CONTAINER_NAME}`
- 504 응답: backend 시작 느림 → health_check `interval`/`retries` 조정

## 기존 프로젝트와의 호환

- `apprunner` 타입: 영향 없음 (App Runner 가 자체 HTTPS 종단)
- `curseforge` 타입: 영향 없음 (배포 산출물만)
- `lightsail` 타입 + `reverse_proxy` 미선언: 영향 없음 (기존 host_port 동작 유지)

## 관련

- [Caddy 공식 문서](https://caddyserver.com/docs/)
- [Let's Encrypt rate limits](https://letsencrypt.org/docs/rate-limits/)
- [ADR 0004 (miner) — Lightsail 채택](https://github.com/devRavit/miner/blob/main/docs/decisions/0004-use-lightsail-instance-not-app-runner.md)
- [ADR 0008 (miner) — host_port / container_port 분리](https://github.com/devRavit/miner/blob/main/docs/decisions/0008-host-port-container-port-separation.md)
