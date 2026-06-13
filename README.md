# deployment-hub

개인 프로젝트들의 CD(Continuous Deployment) 중앙 관리 허브

## Overview

각 프로젝트의 CI는 해당 프로젝트에서 수행하고, CD는 이 저장소에서 중앙 관리합니다.

```
[프로젝트 repo]          [deployment-hub]
    │                         │
    ├─ CI (build, test)       │
    ├─ Docker build & push    │
    └─ repository_dispatch ──>├─ Load project config
                              ├─ Resolve secrets
                              ├─ Deploy to App Runner
                              └─ Create GitHub Release
```

## Project Configuration

`projects/{project}.yml` 형식으로 각 프로젝트 설정 관리:

```yaml
name: stash
source_repo: devRavit/stash
type: apprunner

apprunner:
  service_name: stash
  port: 9090
  cpu: "0.25 vCPU"
  memory: "0.5 GB"
  health_check:
    path: /health
    interval: 10
    timeout: 5
    healthy_threshold: 1
    unhealthy_threshold: 5
  env:
    JAVA_TOOL_OPTIONS: "-Xmx256m -XX:+UseG1GC"
```

## Secrets Management

AWS Secrets Manager에서 `production/{project}` 컨벤션으로 자동 탐색:

- Secret ID: `production/stash`
- Key format: `spring.mongodb.uri` (Spring property 형식)
- 자동 변환: `spring.mongodb.uri` → `SPRING_MONGODB_URI`

새 secret 추가 시 코드 변경 없이 Secrets Manager에만 추가하면 자동 주입됩니다.

## Supported Deployment Types

- **apprunner**: AWS App Runner (ECR 이미지 기반) — ⚠️ 2026-04-30부로 AWS가 신규 가입 중단 (deprecated). 기존 서비스는 유지·보안 패치만.
- **lightsail**: AWS Lightsail Instance (ECR 이미지 기반, SSH + docker pull/restart 방식)
  - 워커형 워크로드(자율 워커·고정 IP 필요·HTTP 진입 적음)에 적합
  - 필요한 GitHub Actions 시크릿: `LIGHTSAIL_SSH_KEY` (인스턴스 키페어 private key 전문)
  - 인스턴스 측 사전 셋업: docker, AWS CLI, ECR pull 권한을 가진 IAM access key (`~/.aws/credentials`)
  - 헬스체크: 인스턴스 localhost에서 컨테이너 포트로 curl 폴링
- **curseforge**: WoW Addon CurseForge 자동 배포 (BigWigs Packager 기반)
  - `repository_dispatch`(태그 push 시 자동) 또는 `workflow_dispatch`(수동 dry-run) 트리거
  - dry-run 모드: 패키지 zip을 GitHub Actions artifact로 출력 (CurseForge 등록 신청용)
  - 시크릿: `CF_API_KEY` (CurseForge Upload API), `PAT` (cross-repo 인증, 기존 `deployment-hub` PAT 재사용)

## Recent Changes

<!-- CHANGELOG_START -->
<!-- CHANGELOG_END -->

## License

Private repository
