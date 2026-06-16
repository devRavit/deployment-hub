# Changelog

## v0.2.9
`2026.06.16`

fix: Caddy --dns 재생성 조건 수정 + debug 워크플로 제거

docker inspect HostConfig.Dns 가 빈 경우 `<no value>` 반환이라 `= []` 비교가 안 먹어 기존 DNS 없는 caddy 가 재생성 안 됨(6h 유지). 8.8.8.8 grep 포함 여부로 감지하도록 변경. 진단(debug-instance.yml)으로 caddy resolv.conf=127.0.0.53 + nslookup refused + NO 80/443 LISTENER 확인 완료, 진단 제거.

## v0.2.8
`2026.06.16`

chore: 진단 워크플로 재투입 (Caddy DNS 재생성 검증)

--dns 추가 후에도 80/443 refused 지속 — caddy DNS config/resolv.conf/nslookup 확인용 일회성 재투입.

## v0.2.7
`2026.06.16`

fix: Caddy 컨테이너 DNS 미설정 — ACME 인증서 발급 실패로 443 미listen 해결

진단 결과 (debug-instance.yml): Caddy 컨테이너는 정상 기동했으나 호스트 systemd-resolved stub(127.0.0.53)을 컨테이너에서 접근 못 해 ACME(Let's Encrypt/ZeroSSL) DNS 해석 실패 → 인증서 미발급 → TLS 핸들러 미준비 → 80/443 connection refused.

- caddy `docker run` 에 `--dns 8.8.8.8 --dns 1.1.1.1` 추가 — 공용 resolver 로 ACME 도메인 해석.
- 기존 컨테이너가 --dns 없이 떠 있으면 (HostConfig.Dns 가 빈 배열) 강제 재생성.
- 진단용 `debug-instance.yml` 제거 (원인 파악 완료).

## v0.2.6
`2026.06.16`

chore: 일회성 인스턴스 진단 워크플로우 (debug-instance.yml)

reverse_proxy Caddy 부트스트랩 후에도 80/443 connection refused 가 지속돼, 인스턴스의 docker ps / caddy logs / Caddyfile / sites.d / listening ports 를 한 번에 출력하는 `workflow_dispatch` 진단 워크플로우 추가. 원인 파악 후 제거 예정.

## v0.2.5
`2026.06.16`

fix: Caddy 부트스트랩 SSH env 미전달 — `bash -c` → stdin `bash -s` + export 인라인

v0.2.4 의 heredoc 수정 후에도 `ssh host VAR=val bash -c "$SCRIPT"` 형식에서 `RP_DOMAIN: unbound variable` 로 실패. `ssh host VAR=val bash -c "..."` 는 OpenSSH 가 VAR 를 원격 명령의 환경변수로 안 붙임 (bash -s stdin 패턴과 달리). `set -u` 가 unbound 로 즉시 중단.

- 변수를 로컬 GitHub Actions env 확장으로 `export VAR='...'` 인라인해 스크립트 앞에 prepend.
- `printf '%s\n' "$REMOTE_SCRIPT" | ssh ubuntu@IP bash -s` (stdin 전달) — Pull image step 과 동일 패턴.

## v0.2.4
`2026.06.16`

fix: Caddy 부트스트랩 중첩 heredoc 버그 — Caddy 컨테이너 미기동으로 80/443 죽던 문제

`lightsail.yml` 의 Caddy 부트스트랩 step 이 `ssh ... bash -s <<'REMOTE'` 안에 `<<MAIN` / `<<SITE` 중첩 heredoc 을 들여쓰기와 함께 둬, 종료 토큰(`MAIN`/`SITE`)이 줄 시작이 아니라 인식 안 됨 → heredoc 미종료 → 스크립트 깨짐 → Caddy 컨테이너 미기동. workflow 의 health check 는 컨테이너 내부(8080)로 폴링해 통과했지만 외부 80/443 은 listen 0.

- 중첩 heredoc 제거 → `REMOTE_SCRIPT` 변수 + `printf` 로 Caddyfile / site snippet 생성.
- `<<'REMOTE'` quoted heredoc 의 변수 미보간 문제도 해소 — `ssh ... bash -c "$REMOTE_SCRIPT"` 로 env 전달.

## v0.2.3
`2026.06.16`

ci: 워크플로우 트리거 분리로 status check 중복 실행 해소

- `ci.yml` (`changelog-bumped`): `pull_request:` 제거, `push:` only. PR 브랜치 push 시점에만 1회 산출.
- `pr-body.yml` (`required-sections`): `push:` 제거 + open PR 조회 우회 로직 통째로 제거, `pull_request:` only. PR open/edit/synchronize 시점에만 1회 산출.
- 이전: 동일 체크가 push + pull_request 양쪽 트리거로 2회씩 실행되어 PR 당 4개 status check 표시 + run 비용 중복.
- main ruleset 의 두 required_status_checks (`changelog-bumped`, `required-sections`) 는 그대로 — 단일 ruleset 이 두 context 강제. trigger 가 다른 시점이라도 PR head commit 에 두 SUCCESS 가 모이면 merge 통과.
- miner 의 `project_miner_ruleset_traps` 패턴과 동일 구조.

## v0.2.2
`2026.06.16`

Lightsail 배포에 Caddy reverse proxy 사이드카 지원 추가 (HTTPS 종단 중앙화).

- `lightsail.yml`: `reverse_proxy` 옵셔널 변수 추가. 활성 시 인스턴스당 공유 Caddy 컨테이너 자동 부트스트랩 + `sites.d/{project}.caddy` snippet 생성 + Lightsail firewall 443 OPEN + Caddy reload.
- `lightsail.yml`: 배포·헬스체크 step 이 `reverse_proxy.enabled` 에 따라 분기. reverse_proxy 모드는 proxy_net docker network + host 포트 미노출 + 컨테이너 내부 health check.
- `projects/miner.yml`: `reverse_proxy` 블록 활성화 (`miner.ravit.run` + Let's Encrypt). host_port 80 → 8080 으로 변경 (Caddy 가 외부 종단).
- `README.md` + `docs/lightsail-reverse-proxy.md`: 설계·운영 문서 신설.
- 기존 프로젝트 영향 없음 — `reverse_proxy` 미선언 시 기존 host_port 직접 노출 동작 유지.

## v0.2.1
`2026.06.15 (KST)`

chore: GitHub Actions 액션 최신 버전 업그레이드 (Node.js 20 deprecated 해소)

- `actions/checkout` v4 → v6 (전 워크플로).
- `actions/github-script` v7 → v9 (apprunner/lightsail).
- `actions/upload-artifact` v4 → v7 (curseforge).
- `aws-actions/configure-aws-credentials` v4 → v6 (apprunner/lightsail/rollback).
- 3rd-party(`BigWigsMods/packager@v2`)는 유지.

## v0.2.0
`2026.06.15 (KST)`

Lightsail rollback workflow + ECR lifecycle 정책 (miner #60)

- `.github/workflows/rollback.yml`: `workflow_dispatch` 로 직전(또는 지정) 버전 1-step 복귀
  - `target_version` 비우면 ECR 직전(latest-1) 자동 결정. 직전이 없으면 조용히 skip
  - ECR `:target` pull → ssh stop/rm/run → health check → 실패 시 `:latest` 자동 원복
  - rollback 은 `docker image prune` 하지 않음 — 원복용 `:latest` 이미지 보존
- `.github/workflows/lightsail.yml`: 배포 시 ECR lifecycle 적용 step 추가
  - `config.ecr.lifecycle.keep_count` 가 있으면 적용 (없는 프로젝트는 skip)
  - tagged 최근 N개(latest + 직전들) 보관 + untagged 1일 만료
- `projects/miner.yml`: `ecr.lifecycle.keep_count: 2` (latest + 직전만 보관)
- `.github/workflows/pr-body.yml`: PR 본문 10 섹션 게이트 (miner 패턴 — push/pull_request 트리거, open PR 없으면 skip)
- `.github/workflows/ci.yml`: CHANGELOG 현행화 게이트 (최상단 `## vX.Y.Z` 가 main 대비 bump 됐는지 — miner 의 checkVersionBumped + checkChangelogEntry 동등)
- README: mermaid 아키텍처 다이어그램 (ASCII → mermaid), `ecr.lifecycle` 스키마, Rollback 사용법

## v0.1.0
`2026.05.02 (KST)`

CurseForge 배포 타입 추가 (WoW 애드온 지원)

- `.github/workflows/curseforge.yml`: BigWigs Packager 기반 CurseForge 자동 업로드
  - `repository_dispatch` (소스 리포 태그 push 트리거) + `workflow_dispatch` (수동 dry-run) 양쪽 지원
  - dry-run 모드: zip 산출물을 GitHub Actions artifact로 출력
- `projects/<addon>.yml`: 첫 WoW 애드온 프로젝트 추가 (project_id placeholder)
- README: Supported Deployment Types에 curseforge 추가
- 신규 시크릿: `CF_API_KEY` (CurseForge Upload API). cross-repo 인증은 기존 `PAT` 재사용 (스코프에 신규 애드온 repo 추가 필요)
- `projects/<addon>.yml`: CurseForge 승인 후 실제 project_id 적용

---

## v0.0.3
`2025.11.30 12:00`

프로젝트별 region 및 IAM role 설정 지원

- `projects.yml`에 `region`, `aws.ecr_role`, `aws.instance_role` 필드 추가
- GitHub Secrets에서 `AWS_ACCOUNT_ID`만 사용, role ARN은 동적 조합
- 배포 단순화: `start-deployment`만 호출 (마이그레이션 로직 제거)
- 불필요한 secrets 정리: `AWS_REGION`, `APP_RUNNER_*_ROLE_ARN` 삭제

---

## v0.0.2
`2025.11.29 22:22`

Secrets Manager 동적 주입 리팩토링

- `production/{project}` 컨벤션으로 자동 secret 탐색
- `spring.mongodb.uri` → `SPRING_MONGODB_URI` 자동 변환
- 프로젝트 설정 파일에서 secrets 항목 제거 (코드 변경 없이 secret 추가 가능)

---

## v0.0.1
`2025.11.29 20:58`

deployment-hub 초기 구성

- App Runner 배포 workflow 추가
- 최초 프로젝트 설정 추가
- GitHub Deployment, Release 자동 생성

---
